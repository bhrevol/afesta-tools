"""Test cases for LPEG client module."""
import os
from pathlib import Path
from typing import AsyncGenerator
from typing import Optional

import pytest
import pytest_asyncio
from aioresponses import aioresponses
from aioresponses.compat import merge_params
from aioresponses.compat import normalize_url
from pytest_mock import MockerFixture

from afesta_tools.exceptions import AuthenticationError
from afesta_tools.lpeg import FourDClient
from afesta_tools.lpeg import VideoQuality
from afesta_tools.lpeg.client import AP_LOGIN_URL
from afesta_tools.lpeg.client import AP_REG_URL
from afesta_tools.lpeg.client import AP_STATUS_CHK_URL
from afesta_tools.lpeg.client import DL_URL
from afesta_tools.lpeg.client import VCS_DL_URL
from afesta_tools.lpeg.client import BaseLpegClient
from afesta_tools.lpeg.credentials import BaseCredentials
from afesta_tools.progress import ProgressCallback

from .test_credentials import TEST_CREDENTIALS


TEST_VIDEO_CODE = "st1234"


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[BaseLpegClient, None]:
    """Fixture to generate a 4D client with test credentials."""
    async with FourDClient(TEST_CREDENTIALS) as client:
        yield client


@pytest_asyncio.fixture
async def client_noauth() -> AsyncGenerator[BaseLpegClient, None]:
    """Fixture to generate a 4D client with no auth credentials."""
    async with FourDClient() as client:
        yield client


async def test_require_auth(client_noauth: BaseLpegClient) -> None:
    """Unauthed client should fail on require_auth calls."""
    with pytest.raises(AuthenticationError):
        await client_noauth.status_chk()


async def test_status_chk(mocker: MockerFixture, client: BaseLpegClient) -> None:
    """ap_status_chk request should be made."""
    post = mocker.spy(client._session, "post")
    with aioresponses() as m:  # type: ignore
        m.post(
            AP_STATUS_CHK_URL,
            status=200,
            payload={"data": {}, "reg": 0, "result": 1},
        )
        await client.status_chk()
    post.assert_called_once_with(
        AP_STATUS_CHK_URL,
        data={
            "st": TEST_CREDENTIALS.st,
            "mid": TEST_CREDENTIALS.mid,
            "pid": TEST_CREDENTIALS.pid,
            "type": "dpvr",
        },
    )


@pytest.mark.parametrize("quality", [None, VideoQuality.H265])
@pytest.mark.parametrize("with_progress", [True, False])
async def test_download_video(
    tmpdir: Path,
    mocker: MockerFixture,
    client: BaseLpegClient,
    quality: VideoQuality,
    with_progress: bool,
) -> None:
    """Download request should be made."""
    if with_progress:
        progress: Optional[ProgressCallback] = ProgressCallback(mocker.MagicMock())
        set_desc = mocker.spy(progress, "set_desc")
        set_total = mocker.spy(progress, "set_total")
        update = mocker.spy(progress, "update")
    else:
        progress = None
    get = mocker.spy(client._session, "get")
    params = {
        "op": 1,
        "type": quality.value if quality else VideoQuality.PC_SBS.value,
        "code": TEST_VIDEO_CODE,
        "pid": TEST_CREDENTIALS.pid,
    }
    with aioresponses() as m:  # type: ignore
        redirect = "http://vr00.lpeg.jp/mp4sbs_dl.php?fid=abc123&status=123"
        url = normalize_url(merge_params(DL_URL, params=params))
        m.get(url, status=303, headers={"Location": redirect})
        m.get(
            redirect,
            status=200,
            headers={
                "Content-Disposition": 'attachment; filename="foo.mp4"',
                "Content-Length": "10",
            },
            body=b"1234567890",
        )
        cwd = os.getcwd()
        os.chdir(tmpdir)
        await client.download_video(TEST_VIDEO_CODE, quality=quality, progress=progress)
        os.chdir(cwd)
    assert client._dl_timeout.total is None
    get.assert_called_once_with(DL_URL, params=params, timeout=client._dl_timeout)
    assert (Path(tmpdir) / "foo.mp4").read_bytes() == b"1234567890"
    if with_progress:
        set_desc.assert_called_once_with("Downloading foo.mp4")
        set_total.assert_called_once_with(10)
        update.assert_called_with(10)


async def test_download_vcz(
    tmpdir: Path, mocker: MockerFixture, client: BaseLpegClient
) -> None:
    """Download VCZ request should be made."""
    progress = ProgressCallback(mocker.MagicMock())
    get = mocker.spy(client._session, "get")
    set_desc = mocker.spy(progress, "set_desc")
    set_total = mocker.spy(progress, "set_total")
    update = mocker.spy(progress, "update")
    params = {"pid": TEST_CREDENTIALS.pid, "fid": "foo_sbs"}
    with aioresponses() as m:  # type: ignore
        url = normalize_url(merge_params(VCS_DL_URL, params=params))
        m.post(
            AP_STATUS_CHK_URL,
            status=200,
            payload={"data": {}, "reg": 0, "result": 1},
        )
        m.get(
            url,
            status=200,
            headers={
                "Content-Disposition": 'attachment; filename="foo.vcz"',
                "Content-Length": "10",
            },
            body=b"1234567890",
        )
        await client.download_vcz("foo_sbs", download_dir=tmpdir, progress=progress)
    get.assert_called_once_with(
        VCS_DL_URL,
        params=params,
        headers={"Accept-Encoding": "gzip, identity"},
        timeout=client._dl_timeout,
    )
    output_path = Path(tmpdir) / "foo.vcz"
    assert output_path.read_bytes() == b"1234567890"
    set_desc.assert_called_once_with(f"Downloading {output_path}")
    set_total.assert_called_once_with(10)
    update.assert_called_with(10)


async def test_register_player(
    mocker: MockerFixture, client_noauth: BaseLpegClient
) -> None:
    """Should register with default creds."""
    device_id = BaseCredentials.get_device_id()
    with aioresponses() as m:  # type: ignore
        url = merge_params(AP_REG_URL, params={"pid": device_id})
        m.get(url, payload={"result": -1})
        with pytest.raises(AuthenticationError):
            await client_noauth.register_player(TEST_CREDENTIALS.uid, "password")
    with aioresponses() as m:  # type: ignore
        url = merge_params(AP_REG_URL, params={"pid": device_id})
        m.get(url, payload={"result": 0, "mp_no": TEST_CREDENTIALS.pid})
        m.post(AP_LOGIN_URL, payload={"result": -1})
        with pytest.raises(AuthenticationError):
            await client_noauth.register_player(TEST_CREDENTIALS.uid, "password")
    login_payload = {
        "uid": TEST_CREDENTIALS.uid,
        "pass": "password",
        "pid": TEST_CREDENTIALS.pid,
        "type": "dpvr",
    }
    get = mocker.spy(client_noauth._session, "get")
    post = mocker.spy(client_noauth._session, "post")
    with aioresponses() as m:  # type: ignore
        url = merge_params(AP_REG_URL, params={"pid": device_id})
        m.get(url, payload={"result": 0, "mp_no": TEST_CREDENTIALS.pid})
        m.post(
            AP_LOGIN_URL,
            payload={
                "data": {
                    "mid": TEST_CREDENTIALS.mid,
                    "st": TEST_CREDENTIALS.st,
                },
                "result": 1,
            },
        )
        creds = await client_noauth.register_player(TEST_CREDENTIALS.uid, "password")
    get.assert_called_once_with(AP_REG_URL, params={"pid": device_id})
    post.assert_called_once_with(AP_LOGIN_URL, data=login_payload)
    assert creds == TEST_CREDENTIALS
    assert client_noauth.creds == TEST_CREDENTIALS
