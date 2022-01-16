"""Global test fixtures."""
from pathlib import Path

import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def config_dir(tmp_path: Path, mocker: MockerFixture) -> Path:
    """Fixture for generating afesta-tools config directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    mocker.patch("platformdirs.user_config_dir", return_value=str(config_dir))
    return config_dir
