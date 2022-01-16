"""Global test fixtures."""
import os
from pathlib import Path
from typing import Generator

import pytest
from pytest_mock import MockerFixture


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
