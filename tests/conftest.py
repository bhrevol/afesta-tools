"""Global test fixtures."""

import inspect
import os
from pathlib import Path
from collections.abc import Generator
from unittest.mock import Mock

import aiohttp
import pytest
from pytest_mock import MockerFixture


# monkeypatch aioresponses to support breaking change in aiohttp 3.14
_response_init = aiohttp.ClientResponse.__init__
if "stream_writer" in inspect.signature(_response_init).parameters:

    def _patched_response_init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs.setdefault("stream_writer", Mock(output_size=0))
        _response_init(self, *args, **kwargs)

    aiohttp.ClientResponse.__init__ = _patched_response_init  # type: ignore[method-assign]


@pytest.fixture
def config_dir(tmp_path: Path, mocker: MockerFixture) -> Path:
    """Fixture for generating afesta-tools config directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    mocker.patch("platformdirs.user_config_dir", return_value=str(config_dir))
    return config_dir


@pytest.fixture
def wdir(tmp_path: Path) -> Generator[Path, None, None]:
    """Fixture for generating a new working directory."""
    working_dir = tmp_path / "wdir"
    working_dir.mkdir()
    cwd = os.getcwd()
    os.chdir(working_dir)
    yield working_dir
    os.chdir(cwd)
