"""Tests for the config module."""
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from afesta_tools.config import CREDENTIALS_FILE
from afesta_tools.config import dump_credentials
from afesta_tools.config import load_credentials
from afesta_tools.exceptions import NoCredentialsError

from .lpeg.test_credentials import TEST_CREDENTIALS


TEST_JSON = json.dumps(asdict(TEST_CREDENTIALS))


def test_dump_credentials(config_dir: Path) -> None:
    """Credentials should be dumped to json."""
    dump_credentials(TEST_CREDENTIALS)
    assert (config_dir / CREDENTIALS_FILE).read_text("utf-8") == TEST_JSON


def test_load_credentials(config_dir: Path) -> None:
    """Credentials should be loaded from json."""
    with pytest.raises(NoCredentialsError):
        load_credentials()
    (config_dir / CREDENTIALS_FILE).write_text(TEST_JSON, encoding="utf-8")
    assert load_credentials() == TEST_CREDENTIALS
