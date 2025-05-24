import os
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO, cast

from lxml import etree

from ..exceptions import AfestaError


class ChapterControlParseError(AfestaError):
    pass


@dataclass
class Scene:
    time: int
    duration: int
    name: str | None
    file: str | None
    goto: str | None

    @classmethod
    def from_xml(cls, e: etree._Element) -> "Scene":
        if e.tag != "scene":
            raise ChapterControlParseError("Expected ChapterControl scene element")
        try:
            time = e.get("time")
            duration = e.get("duration")
            if time is None or duration is None:
                raise ValueError("Scene element missing required time+duration")
            return cls(
                time=int(cast(str, e.get("time"))),
                duration=int(cast(str, e.get("duration"))),
                name=e.get("name"),
                file=e.get("file"),
                goto=e.get("goto"),
            )
        except ValueError as exc:
            raise ChapterControlParseError("Failed to parse scene element") from exc


@dataclass
class ChapterControl:
    scenes: list[Scene]

    @classmethod
    def from_xml(cls, e: etree._Element) -> "ChapterControl":
        if e.tag != "params":
            raise ChapterControlParseError("Expected ChapterControl params element")
        scenes = [Scene.from_xml(scene) for scene in e.iterfind(".//scene")]
        return cls(scenes=scenes)

    def dump_ffmetadata(self, f: TextIO) -> None:
        lines = [";FFMETADATA1"]
        for i, scene in enumerate(self.scenes):
            if i + 1 >= len(self.scenes):
                end = scene.time + scene.duration
            else:
                end = self.scenes[i + 1].time - 1
            lines.extend(
                [
                    "[CHAPTER]",
                    "TIMEBASE=1/1000",
                    f"START={scene.time}",
                    f"END={end}",
                    f"TITLE=Chapter {i + 1}",
                ]
            )
        f.write(os.linesep.join(lines))

    async def file_offsets(self, dir: str | Path | None = None) -> dict[str, int]:
        from .archive import VCZArchive

        """Returns relative offsets for external VCZ files."""
        workdir = Path(dir) if dir is not None else Path.cwd()
        offsets = {}
        for i, scene in enumerate(self.scenes):
            if scene.name:
                continue
            if scene.file and scene.file not in offsets:
                if not scene.goto:
                    raise ValueError("external scene with no goto reference")
                async with VCZArchive(workdir / f"{scene.file}.vcz") as vcz:
                    chapters = await vcz.chapter_control()
                    if not chapters:
                        raise ValueError("external chapters found")
                    try:
                        theirs = chapters.scenes[i]
                    except IndexError as e:
                        raise ValueError("external scene not found") from e
                offsets[scene.file] = scene.time - theirs.time
        return offsets
