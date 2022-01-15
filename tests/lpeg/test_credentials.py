"""Test cases for LPEG credentials module."""
import io
from typing import Any

import pytest
from pytest_mock import MockerFixture

from afesta_tools.exceptions import NoCredentialsError
from afesta_tools.lpeg import FourDCredentials


TEST_UID = "foo"
TEST_ST = "123456"
TEST_MID = "jtCsTw2kdWzs4yYJhJifAVVrBbCrTJR62SH53uU5PlErtuqyAndDIWzoVFXVTyl9"
TEST_PID = "0001234567abcdef123456"
TEST_CREDENTIALS = FourDCredentials(TEST_UID, TEST_ST, TEST_MID, TEST_PID)


@pytest.fixture
def mock_registry(mocker: MockerFixture) -> None:
    """Fixture which mocks Windows registry using fake_winreg."""
    from fake_winreg import fake_reg_tools
    from fake_winreg import fake_winreg

    fake_registry = fake_reg_tools.get_minimal_windows_testregistry()
    fake_winreg.load_fake_registry(fake_registry)

    try:
        mocker.patch("winreg.OpenKey", fake_winreg.OpenKey)
        mocker.patch("winreg.EnumValue", fake_winreg.EnumValue)
    except ImportError:
        pass


def test_fourd_user_reg_values(mock_registry: Any) -> None:
    """Test that registry values are loaded properly."""
    from fake_winreg import fake_winreg
    from fake_winreg import registry_constants

    reg_sz = registry_constants.REG_SZ

    with pytest.raises(NoCredentialsError):
        FourDCredentials._get_user_reg_values()

    with fake_winreg.CreateKey(
        registry_constants.HKEY_CURRENT_USER, FourDCredentials.WINREG_KEY
    ) as key:
        fake_winreg.SetValueEx(key, "login_account_123", 0, reg_sz, TEST_UID)
        fake_winreg.SetValueEx(key, "mid_123", 0, reg_sz, TEST_MID)
        fake_winreg.SetValueEx(key, "st_123", 0, reg_sz, TEST_ST)
    assert FourDCredentials._get_user_reg_values() == {
        "login_account": TEST_UID,
        "mid": TEST_MID,
        "st": TEST_ST,
    }


def test_4d_user_pid(mocker: MockerFixture) -> None:
    """Test that PidConfiguration.json is loaded properly."""
    mocker.patch("builtins.open", side_effect=FileNotFoundError)
    with pytest.raises(NoCredentialsError):
        FourDCredentials._get_user_pid()

    mocker.patch(
        "builtins.open",
        return_value=io.BytesIO(f'{{"pid": "{TEST_PID}"}}'.encode()),
    )
    assert FourDCredentials._get_user_pid() == TEST_PID


def test_4d_get_default(mocker: MockerFixture) -> None:
    """Test that default credentials are loaded properly."""
    mocker.patch.object(
        FourDCredentials,
        "_get_user_reg_values",
        return_value={
            "login_account": TEST_UID,
            "st": TEST_ST,
            "mid": TEST_MID,
        },
    )
    mocker.patch.object(FourDCredentials, "_get_user_pid", return_value=TEST_PID)
    assert FourDCredentials.get_default() == TEST_CREDENTIALS
