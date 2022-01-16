"""Test cases for the __main__ module."""
from pathlib import Path
from typing import List
from typing import Optional

import pytest
from click.testing import CliRunner
from pytest_mock import MockerFixture

from afesta_tools import __main__
from afesta_tools.lpeg.client import FourDClient

from .lpeg.test_credentials import TEST_CREDENTIALS


@pytest.fixture
def runner() -> CliRunner:
    """Fixture for invoking command-line interfaces."""
    return CliRunner()


def test_main_succeeds(runner: CliRunner) -> None:
    """It exits with a status code of zero."""
    result = runner.invoke(__main__.cli)
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "args, input",
    [
        (None, "username\npassword\n"),
        (["-u", "username"], "password\n"),
        (["-p", "password"], "username\n"),
        (["-u" "username", "-p", "password"], None),
    ],
)
def test_login(
    runner: CliRunner,
    mocker: MockerFixture,
    config_dir: Path,
    args: Optional[List[str]],
    input: Optional[str],
) -> None:
    """Should login with username/password."""
    register_player = mocker.patch.object(
        FourDClient, "register_player", return_value=TEST_CREDENTIALS
    )
    result = runner.invoke(__main__.login, args=args, input=input)
    register_player.assert_called_with("username", "password")
    assert f"Logged into Afesta as {TEST_CREDENTIALS.uid}" in result.output


def test_already_logged_in(
    runner: CliRunner, config_dir: Path, mocker: MockerFixture
) -> None:
    """Should not login unless --force is provided."""
    from afesta_tools.config import dump_credentials

    register_player = mocker.patch.object(
        FourDClient, "register_player", return_value=TEST_CREDENTIALS
    )
    dump_credentials(TEST_CREDENTIALS)
    result = runner.invoke(__main__.login)
    assert f"Already logged in as {TEST_CREDENTIALS.uid}" in result.output
    register_player.assert_not_called()

    result = runner.invoke(__main__.login, ["-u", "username", "-p", "password", "-f"])
    assert "Logged into Afesta" in result.output
    register_player.assert_called_with("username", "password")
