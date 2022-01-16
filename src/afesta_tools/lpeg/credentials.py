"""LPEG API credentials."""
import hashlib
import os
import platform
import uuid
from dataclasses import dataclass
from typing import ClassVar
from typing import Dict
from typing import Union
from typing import cast

from ..exceptions import NoCredentialsError


if platform.system().lower() == "windows":
    import winreg
else:
    import fake_winreg as winreg  # type: ignore


@dataclass
class BaseCredentials:
    """Base LPEG API credentials.

    Attributes:
        uid: LPEG API user ID (login username).
        st: LPEG API st token (6-digit numeric string).
        mid: LPEG API mid (64-character alphanumeric string).
        pid: LPEG API player ID (alphanumeric player ID).
    """

    uid: str
    st: str
    mid: str
    pid: str

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseCredentials):
            return False
        return (
            self.uid == other.uid
            and self.st == other.st
            and self.mid == other.mid
            and self.pid == other.pid
        )

    @classmethod
    def get_default(cls) -> "BaseCredentials":  # pragma: no cover
        """Lookup and return default credentials for the current user.

        Raises:
            NoCredentialsError: No default credentials for the current user
                could be found.
        """
        raise NoCredentialsError

    @classmethod
    def get_device_id(cls) -> "str":
        """Return a device ID suitable for generating a player ID (`pid`).

        LPEG player ID's consist of a a server token prepended to a unique
        device ID. Device ID generation is dependent on platform and client,
        but is comparable to ``UnityEngine.SystemInfo.deviceUniqueIdentifier``.

        Returns:
            Unique (hardware based) device ID roughly equivalent to an LPEG
            desktop player device ID.
        """
        hardware_id = uuid.getnode().to_bytes(length=6, byteorder="big")
        return hashlib.blake2b(hardware_id, digest_size=6).digest().hex()


@dataclass
class FourDCredentials(BaseCredentials):
    """4D Media Player API credentials.

    Note:
        Local credential lookup requires a registered 4D Media Player
        installation, meaning that the user must install the player, log in
        with a valid LPEG/Afesta account, and register that player instance
        to the user's account.

        When looking up local player credentials, afesta_tools will not read
        the local user's LPEG/Afesta password, it only reads the API access
        credentials which are already stored on the local machine by 4D Media
        Player.
    """

    WINREG_KEY: ClassVar[str] = r"SOFTWARE\lpeg\4D MEDIA PLAYER"
    PID_CONFIG_PATH: ClassVar[str] = os.path.join(
        "~",
        "AppData",
        "LocalLow",
        "lpeg",
        "4D MEDIA PLAYER",
        "PidConfiguration.json",
    )

    @classmethod
    def get_default(cls) -> "FourDCredentials":
        """Lookup and return default credentials for the current user.

        Returns:
            Default 4D Media Player credentials.

        Raises:
            NoCredentialsError: No default credentials for the current user
                could be found.
        """
        reg_values = cls._get_user_reg_values()
        return cls(
            uid=reg_values["login_account"],
            st=reg_values["st"],
            mid=reg_values["mid"],
            pid=cls._get_user_pid(),
        )

    @classmethod
    def _get_user_reg_values(cls) -> Dict[str, str]:
        result: Dict[str, str] = {}
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.WINREG_KEY) as key:
                names = {"login_account", "mid", "st"}
                i = 0
                while True:
                    try:
                        value_name, value, typ = winreg.EnumValue(key, i)
                        for name in names:
                            if value_name.startswith(f"{name}_"):
                                result[name] = cls._coerce_reg_str(value, typ)
                    except OSError:
                        break
                    i += 1
        except (OSError, ValueError) as exc:
            raise NoCredentialsError(
                "No registered 4D Media Player installation could be found."
            ) from exc
        return result

    @staticmethod
    def _coerce_reg_str(value: Union[str, bytes], typ: int) -> str:
        if typ == winreg.REG_SZ:
            return cast(str, value).rstrip("\0")
        elif typ == winreg.REG_BINARY:  # pragma: no cover
            try:
                return cast(bytes, value).decode("utf-8")
            except UnicodeDecodeError:
                pass
        raise ValueError(  # pragma: no cover
            f"Unexpected winreg value: {value!r}, {typ}"
        )

    @classmethod
    def _get_user_pid(cls) -> str:
        import json

        path = os.path.expanduser(cls.PID_CONFIG_PATH)
        try:
            with open(path, encoding="utf-8") as fp:
                pid_config: Dict[str, str] = json.load(fp)
            return pid_config["pid"]
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            raise NoCredentialsError(
                "No registered 4D Media Player installation could be found."
            ) from exc
