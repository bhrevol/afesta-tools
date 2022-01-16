"""Command-line interface."""
import asyncio
from typing import Optional
from typing import Sequence
from typing import cast

import click
from tqdm.asyncio import tqdm

from .config import dump_credentials
from .config import load_credentials
from .exceptions import AfestaError
from .exceptions import NoCredentialsError
from .lpeg.client import BaseLpegClient
from .lpeg.client import FourDClient
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
def login(
    username: Optional[str], password: Optional[str], force: bool
) -> int:  # noqa: DAR101
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
@click.argument("video_id", nargs=-1)
def dl(video_id: Sequence[str]) -> int:  # noqa: DAR101
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
        asyncio.run(_dl(video_id, creds))
    except AfestaError as exc:  # pragma: no cover
        click.echo(f"Download failed: {exc}", err=True)
        return 1
    return 0


async def _dl(video_ids: Sequence[str], creds: BaseCredentials) -> None:
    async with FourDClient(creds) as client:
        await asyncio.gather(*(_dl_one(client, video_id) for video_id in video_ids))


async def _dl_one(client: BaseLpegClient, video_id: str) -> None:
    with tqdm(unit="B", unit_scale=True) as pbar:
        await client.download_video(
            video_id,
            progress=ProgressCallback(pbar),
        )


if __name__ == "__main__":
    cli(prog_name="afesta")  # pragma: no cover
