"""General utilities module."""
import asyncio
import contextvars
import functools
import re
import shutil
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeVar

from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from .vcs.chapter import ChapterControl

from .exceptions import AfestaError


_P = ParamSpec("_P")
_R = TypeVar("_R")


async def to_thread(func: Callable[_P, _R], *args: _P.args, **kwargs: _P.kwargs) -> _R:
    """Backport of asyncio.to_thread."""
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)


async def ffmpeg_concat(
    src: Path,
    chapters: "ChapterControl",
    dry_run: bool = False,
    force: bool = False,
    output_dir: Path | None = None,
) -> Path:
    if not shutil.which("ffmpeg"):
        raise ValueError("ffmpeg is required for video concat")

    parts: list[Path] = []
    processed: set[str] = set()
    m = re.match(r"(?P<filename>.*)-R1(?P<vr_format>_.*)?$", src.stem)
    if not m:
        raise ValueError("Part 1 (-R1) VCZ is required")
    filename = m.group("filename")
    vr_format = m.group("vr_format") if m.group("vr_format") else ""
    src_dir = src.parent
    for scene in chapters.scenes:
        if scene.name:
            file = f"{src.stem}.mp4"
        elif scene.file:
            file = f"{scene.file}.mp4"
        else:
            continue
        if file in processed:
            continue
        processed.add(file)
        part = src_dir / file
        if not part.exists():
            raise FileNotFoundError(f"{part} does not exist")
        parts.append(part.resolve())
    output_dir = output_dir or src_dir
    output = output_dir / f"{filename}{vr_format}.mp4"
    if not force and output.exists():
        raise FileExistsError(f"{output} already exists")
    if not dry_run:
        with tempfile.TemporaryDirectory(dir=src_dir) as temp:
            tmpdir = Path(temp)
            for i, part in enumerate(parts):
                process = await asyncio.create_subprocess_exec(
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(part),
                    "-c",
                    "copy",
                    str(tmpdir / f"{i}.ts"),
                )
                await process.wait()
                if not process.returncode == 0:
                    raise AfestaError("ffmpeg failed to convert part .ts")

            meta_file = tmpdir / "chapters.ffmeta"
            with open(meta_file, "w") as f:
                chapters.dump_ffmetadata(f)
            tmp_output = tmpdir / f"{filename}.mp4"
            concat_parts = "|".join(str(tmpdir / f"{i}.ts") for i in range(len(parts)))
            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-y",
                "-i",
                f"concat:{concat_parts}",
                "-i",
                str(meta_file),
                "-map_metadata",
                "1",
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(tmp_output),
            )
            await process.wait()
            if not process.returncode == 0:
                raise AfestaError("ffmpeg concat failed")
            output.parent.mkdir(parents=True, exist_ok=True)
            tmp_output.replace(output)
    return output


async def script_concat(
    src: Path,
    chapters: "ChapterControl",
    script_formats: Sequence[Literal["csv", "vcsx", "funscript"]],
    dry_run: bool = False,
    force: bool = False,
    output_dir: Path | None = None,
) -> None:
    from a10sa_script.script import (
        VCSXCycloneScript,
        VCSXOnaRhythmScript,
        VCSXPistonScript,
    )

    from .vcs import GoodsType, VCZArchive
    from .vcs.goods import convert_script

    src_dir = src.parent
    output_dir = output_dir or src_dir
    parts: dict[Path, int] = {}
    m = re.match(r"(?P<filename>.*)-R1(?P<vr_format>_.*)?$", src.stem)
    if not m:
        raise ValueError("Part 1 (-R1) VCZ is required")
    filename = m.group("filename")
    vr_format = m.group("vr_format") if m.group("vr_format") else ""
    vcz_offsets = {src: 0}
    vcz_offsets.update(
        (src_dir / f"{k}.vcz", v)
        for k, v in (await chapters.file_offsets(dir=src_dir)).items()
    )
    for path in parts:
        if not path.exists():
            raise FileNotFoundError(f"{path} does not exist")

    for typ, script_cls, suffix in (
        (GoodsType.CYCLONE, VCSXCycloneScript, "_cyclone"),
        (GoodsType.PISTON, VCSXPistonScript, "_piston"),
        (GoodsType.ONARHYTHM, VCSXOnaRhythmScript, "_onarhythm"),
    ):
        script = script_cls()
        for path, offset in vcz_offsets.items():
            async with VCZArchive(path) as vcz:
                try:
                    part_script = await vcz.read_script(typ)
                    for cmd in part_script.commands:
                        cmd.offset += offset
                        script.commands.add(cmd)
                except (KeyError, ValueError):
                    pass
        if script.commands and not dry_run:
            for fmt in script_formats:
                if not dry_run:
                    try:
                        converted = convert_script(script, fmt)
                        suffix = "" if fmt == "funscript" else suffix
                        output = output_dir / f"{filename}{vr_format}{suffix}.{fmt}"
                        if force or not output.exists():
                            output.parent.mkdir(parents=True, exist_ok=True)
                            with open(output, "wb") as f:
                                converted.dump(f)
                    except ValueError:
                        pass
