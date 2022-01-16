"""Afesta Tools config module."""
import json
import os
from dataclasses import asdict

import platformdirs

from .exceptions import NoCredentialsError
from .lpeg.credentials import BaseCredentials


APP_NAME = "afesta-tools"
CREDENTIALS_FILE = "credentials.json"


def dump_credentials(creds: BaseCredentials) -> None:
    """Dump credentials to the default credentials file."""
    config_dir = platformdirs.user_config_dir(APP_NAME)
    os.makedirs(config_dir, exist_ok=True)
    creds_file = os.path.join(config_dir, CREDENTIALS_FILE)
    with open(creds_file, mode="w", encoding="utf-8") as f:
        json.dump(asdict(creds), f)


def load_credentials() -> BaseCredentials:
    """Load credentials from the default credentials file.

    Returns:
        Default credentials.

    Raises:
        NoCredentialsError: Credentials could not be loaded.
    """
    config_dir = platformdirs.user_config_dir(APP_NAME)
    os.makedirs(config_dir, exist_ok=True)
    creds_file = os.path.join(config_dir, CREDENTIALS_FILE)
    try:
        with open(creds_file, encoding="utf-8") as f:
            return BaseCredentials(**json.load(f))
    except (OSError, json.JSONDecodeError) as exc:
        raise NoCredentialsError("Failed to load default credentials.") from exc
