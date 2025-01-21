"""Command-line interface."""
import asyncio
import os
from contextlib import aclosing
from pathlib import Path
from typing import Literal
from collections.abc import Sequence
from typing import Any
from typing import cast

import click
from tqdm.asyncio import tqdm

from .config import dump_credentials
from .config import load_credentials
from .exceptions import AfestaError
from .exceptions import NoCredentialsError
from .lpeg.client import BaseLpegClient
from .lpeg.client import FourDClient
from .lpeg.client import VideoQuality
from .lpeg.credentials import BaseCredentials
from .lpeg.credentials import FourDCredentials
from .progress import ProgressCallback


@click.group()
@click.version_option()
def cli() -> None:
    """Afesta Tools."""


def _load_credentials() -> BaseCredentials:
    """Try to load default credentials.

    Will attempt to load creds from afesta-tools config or an existing
    4D Media Player installation, in that order.

    Returns:
        Default credentials.
    """
    try:
        return load_credentials()
    except NoCredentialsError:
        pass
    return FourDCredentials.get_default()


@cli.command()
@click.option("-u", "--username", default=None, help="Afesta username.")
@click.option("-p", "--password", default=None, help="Afesta password.")
@click.option(
    "-f", "--force", is_flag=True, default=False, help="Overwrite existing credentials."
)
def login(username: str | None, password: str | None, force: bool) -> int:  # noqa: DAR101
    """Login to Afesta and register afesta-tools as a new player.

    If username and/or password are not specified, they will be prompted via the
    command-line.

    Login is not required if 4D Media Player is installed and the current
    user has logged into 4D Media Player and registered it with an Afesta
    account.

    Note that afesta-tools only stores username and API tokens (password will
    not be saved to disk).
    """
    if not force:
        try:
            creds = load_credentials()
            click.echo(f"Already logged in as {creds.uid}")
            return 0
        except NoCredentialsError:
            pass
    if not username:
        username = click.prompt("Afesta username")
    if not password:
        password = click.prompt("Afesta password", hide_input=True)
    try:
        username = cast(str, username)
        password = cast(str, password)
        creds = asyncio.run(_login(username, password))
        dump_credentials(creds)
        click.echo(f"Logged into Afesta as {creds.uid}")
    except AfestaError as exc:  # pragma: no cover
        click.echo(f"Login failed: {exc}", err=True)
        return 1
    return 0


async def _login(username: str, password: str) -> BaseCredentials:
    async with FourDClient() as client:
        return await client.register_player(username, password)


@cli.command()
@click.option("-q", "--quality", type=click.Choice(["h264", "h265"]), default=None)
@click.option(
    "-c",
    "--code",
    is_flag=True,
    help="Download explicit purchase code(s) instead of video FID (i.e. cc123..._0000)",
)
@click.option(
    "-l",
    "--lang",
    type=click.Choice(["jp", "en"], case_sensitive=False),
    default="jp",
)
@click.argument("code_or_fid", nargs=-1)
def dl(
    code_or_fid: Sequence[str],
    quality: str | None,
    code: bool,
    lang: Literal["jp", "en"],
) -> int:  # noqa: DAR101
    """Download an afesta video.

    Requires an account with permissions to download the video (either via
    standalone purchase or monthly subscription DL benefits).

    If 4D Media Player is installed and the current user is logged in via the
    player, the existing 4D Media Player credentials will be used. Otherwise,
    the 'afesta login' command must be run before downloading.
    """
    try:
        creds = _load_credentials()
    except NoCredentialsError:
        click.echo("No credentials found. Did you forget to run 'afesta login'?")
    try:
        kwargs = {}
        if quality:
            kwargs["quality"] = {
                "h264": VideoQuality.H264,
                "h265": VideoQuality.H265,
            }[quality.lower()]
        asyncio.run(_dl(code_or_fid, creds, code=code, lang=lang.upper(), **kwargs))
    except AfestaError as exc:  # pragma: no cover
        click.echo(f"Download failed: {exc}", err=True)
        return 1
    return 0


async def _dl(video_ids: Sequence[str], creds: BaseCredentials, **kwargs: Any) -> None:
    async with FourDClient(creds) as client:
        await asyncio.gather(
            *(_dl_one(client, video_id, **kwargs) for video_id in video_ids)
        )


async def _dl_one(
    client: BaseLpegClient, video_id: str, code: bool = False, **kwargs: Any
) -> None:
    with tqdm(unit="B", unit_scale=True) as pbar:
        if code:
            kwargs["code"] = video_id
        else:
            kwargs["fid"] = video_id
        await client.download_video(
            progress=ProgressCallback(pbar),
            **kwargs,
        )


@cli.command()
@click.argument("video_id", nargs=-1)
def dl_vcz(video_id: Sequence[str]) -> int:  # noqa: DAR101
    """Download vcz files for an afesta video.

    Requires an account with permissions to download the video (either via
    standalone purchase or monthly subscription DL benefits).

    If 4D Media Player is installed and the current user is logged in via the
    player, the existing 4D Media Player credentials will be used. Otherwise,
    the 'afesta login' command must be run before downloading.
    """
    try:
        creds = _load_credentials()
    except NoCredentialsError:
        click.echo("No credentials found. Did you forget to run 'afesta login'?")
    try:
        asyncio.run(_dl_vczs(video_id, creds))
    except AfestaError as exc:  # pragma: no cover
        click.echo(f"Download failed: {exc}", err=True)
        return 1
    return 0


async def _dl_vczs(video_ids: Sequence[str], creds: BaseCredentials) -> None:
    async with FourDClient(creds) as client:
        await asyncio.gather(*(_dl_vcz(client, video_id) for video_id in video_ids))


async def _dl_vcz(client: BaseLpegClient, video_id: str) -> None:
    with tqdm(unit="B", unit_scale=True) as pbar:
        video_id, ext = os.path.splitext(os.path.basename(video_id))
        await client.download_vcz(
            video_id,
            progress=ProgressCallback(pbar),
        )


@cli.command()
@click.argument(
    "filename",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False, readable=True),
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["csv", "funscript", "vcsx"], case_sensitive=False),
    default=["csv"],
    multiple=True,
    help=(
        "Script format (defaults to CSV). --format can be specified multiple"
        "times to extract more than one format."
    ),
)
def extract_script(
    filename: Sequence[Path], fmt: Sequence[Literal["csv", "vcsx", "funscript"]]
) -> int:  # noqa: DAR101
    """Extract interlocking goods script files from a VCZ file."""
    try:
        asyncio.run(_extract_script(filename, fmt))
    except AfestaError as exc:  # prgma: no cover
        click.echo(f"Script extraction failed: {exc}", err=True)
        return 1
    return 0


async def _extract_script(
    filenames: Sequence[Path], fmts: Sequence[Literal["csv", "vcsx", "funscript"]]
) -> None:
    await asyncio.gather(*(_extract_one(name, fmts) for name in filenames))


async def _extract_one(
    filename: Path, fmts: Sequence[Literal["csv", "vcsx", "funscript"]]
) -> None:
    from .vcs import GoodsType
    from .vcs import VCZArchive

    async with VCZArchive(filename) as vcz:
        for typ in (
            GoodsType.CYCLONE,
            GoodsType.PISTON,
            GoodsType.ONARHYTHM,
        ):
            for fmt in fmts:
                try:
                    path = await vcz.extract_script(typ, fmt)
                    click.echo(f"Extracted {path}")
                except (KeyError, ValueError):
                    pass


@cli.command()
@click.option(
    "-l",
    "--lang",
    type=click.Choice(["jp", "en"], case_sensitive=False),
    default="JP",
)
@click.option("-d", "--detail", is_flag=True, help="List detailed video information.")
@click.option("--tv", is_flag=True, help="List AfestaTV/2D videos (defaults to VR).")
def list(tv: bool, detail: bool, lang: Literal["JP", "EN"]) -> int:
    """List available afesta video downloads.

    Requires an account with permissions to download the video (either via
    standalone purchase or monthly subscription DL benefits).

    If 4D Media Player is installed and the current user is logged in via the
    player, the existing 4D Media Player credentials will be used. Otherwise,
    the 'afesta login' command must be run before downloading.
    """
    try:
        creds = _load_credentials()
    except NoCredentialsError:
        click.echo("No credentials found. Did you forget to run 'afesta login'?")
    try:
        asyncio.run(_list(creds, tv, detail, cast(Literal["JP", "EN"], lang.upper())))
    except AfestaError as exc:  # pragma: no cover
        click.echo(f"Listing failed: {exc}", err=True)
        return 1
    return 0


async def _list(
    creds: BaseCredentials, tv: bool, detail: bool, lang: Literal["JP", "EN"]
) -> None:
    async with FourDClient(creds) as client:
        async with aclosing(client.get_videos(vr=not tv, lang=lang)) as results:  # type: ignore[type-var]
            async for video in results:
                if detail:
                    lines = [
                        f"{video.get_fid()}:",
                        f"  {video.title_all}",
                    ]
                    if video.num_parts is not None:
                        lines.append(f"  Parts: {video.num_parts}")
                    lines.extend(
                        [
                            f"  Actresses: {', '.join(a for a in video.acters)}",
                            f"  Genres: {', '.join(c for c in video.categories)}",
                            f"  Release date: {video.release_date:%x %X} JST",
                            f"  Duration: {video.duration}",
                        ]
                    )
                    click.echo(os.linesep.join(lines))
                else:
                    click.echo(f"{video.get_fid()}: {video.title}")


if __name__ == "__main__":
    cli(prog_name="afesta")  # pragma: no cover
