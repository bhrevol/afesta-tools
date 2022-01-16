"""LPEG API client."""
import enum
import os
from abc import abstractmethod
from contextlib import AsyncExitStack
from typing import Any
from typing import AsyncContextManager
from typing import Awaitable
from typing import Callable
from typing import Optional

import aiohttp
from funcy import wraps

from ..exceptions import AfestaError
from ..exceptions import AuthenticationError
from ..progress import ProgressCallback
from ..types import PathLike
from .credentials import BaseCredentials
from .credentials import FourDCredentials


AP_STATUS_CHK_URL = "https://www.lpeg.jp/manage/ap_status_chk.php"
AP_LOGIN_URL = "https://www.lpeg.jp/manage/ap_login.php"
AP_REG_URL = "http://www.lpeg.jp/manage/ap_reg.php"
DL_URL = "https://lpeg.jp/h/"
VCS_DL_URL = "https://data.lpeg.jp/ap_vcs_dl.php"


class VideoQuality(enum.Enum):
    """Video download quality.

    Attributes:
        H264: Best available H.264 quality.
        H265: Best avaialable HEVC quality.
        PC_SBS: Alias for H264.

    Note: `VideoQuality` maps qualities as they are listed in the LPEG web
        UI to the `type` field used in the backend LPEG API. The `type` string
        does not always correspond to the actual video codec and/or resolution.

        In general, for 4K VR content `PC_SBS` will map to PC 4K. In some
        cases, the `PC_SBS` video will be 3K, even though the video has a
        4K HEVC option available.
    """

    H264 = "h264"  # 3K/4K H264
    H265 = "h265"  # 3K/4K HEVC
    PC_SBS = "h264"  # PC 3K/4K


def require_auth(coroutine: Callable[..., Awaitable[Any]]) -> Any:
    """Decorator for API calls which require authentication.

    Arguments:
        coroutine: Coroutine to decorate.

    Returns:
        Decorated function.

    Raises:
        AuthenticationError: Auth credentials are unavailable.
    """

    @wraps(coroutine)  # type: ignore[misc]
    async def wrapper(obj: "BaseLpegClient", *args: Any, **kwargs: Any) -> Any:
        if not obj.creds:
            raise AuthenticationError(
                f"{coroutine.__name__} requires valid credentials."
            )
        return await coroutine(obj, *args, **kwargs)

    return wrapper


class BaseLpegClient(AsyncContextManager["BaseLpegClient"]):
    """lpeg.jp API client.

    Can be used as an async context manager. When used as a context manager,
    `close` will be called automatically on exit.
    """

    CHUNK_SIZE = 4096
    DEFAULT_VIDEO_QUALITY = VideoQuality.PC_SBS

    def __init__(self, creds: Optional[BaseCredentials] = None) -> None:
        """Construct a new client.

        Arguments:
            creds: LPEG API credentials. Required to make authenticated API calls.
                Public (unauthenticated) API calls can still be made when `creds`
                is not set.
        """
        super().__init__()
        self.creds = creds
        self._exit_stack = AsyncExitStack()
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": self.user_agent},
            raise_for_status=True,
        )

    async def __aenter__(self) -> "BaseLpegClient":
        await self._exit_stack.enter_async_context(self._session)
        return self

    async def __aexit__(self, *args: Any, **kwargs: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close this client."""
        async with self._exit_stack:
            pass

    @property
    @abstractmethod
    def user_agent(self) -> str:
        """Return the HTTP User-Agent for this client."""

    async def _get(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        return await self._session.get(url, **kwargs)

    async def _post(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        return await self._session.post(url, **kwargs)

    @require_auth
    async def status_chk(self) -> None:
        """Run ap_status_chk API request."""
        assert self.creds is not None
        payload = {
            "st": self.creds.st,
            "mid": self.creds.mid,
            "pid": self.creds.pid,
            "type": "dpvr",
        }
        await self._post(AP_STATUS_CHK_URL, data=payload)

    async def _download(
        self,
        response: aiohttp.ClientResponse,
        download_dir: Optional[PathLike] = None,
        progress: Optional[ProgressCallback] = None,
    ) -> None:
        if response.content_disposition:
            filename: Optional[str] = response.content_disposition.filename
        else:  # pragma: no cover
            filename = None
        if not filename:  # pragma: no cover
            raise AfestaError("Not a valid file download URL")
        if download_dir:
            filename = os.path.join(download_dir, filename)
        if progress:
            progress.set_desc(f"Downloading {filename}")
            if "Content-Length" in response.headers:  # pragma: no cover
                progress.set_total(int(response.headers["Content-Length"]))
        with open(filename, mode="wb") as fp:
            async for chunk in response.content.iter_chunked(self.CHUNK_SIZE):
                fp.write(chunk)
                if progress:
                    progress.update(len(chunk))

    @require_auth
    async def download_video(
        self,
        code: str,
        download_dir: Optional[PathLike] = None,
        quality: Optional[VideoQuality] = None,
        progress: Optional[ProgressCallback] = None,
    ) -> None:
        """Download a video.

        Arguments:
            code: Video code (LPEG tr... code).
            download_dir: Directory for downloaded files. Defaults to the
                current working dir.
            quality: Video quality. Defaults to `DEFAULT_VIDEO_QUALITY`.
            progress: Optional progress callback.

        Note:
            Actual download quality may be worse than the requested value
            depending on the video.
        """
        resp = await self._request_video(code, quality=quality)
        await self._download(resp, download_dir=download_dir, progress=progress)

    async def _request_video(
        self,
        code: str,
        quality: Optional[VideoQuality] = None,
    ) -> aiohttp.ClientResponse:
        assert self.creds is not None
        if quality is None:
            quality = self.DEFAULT_VIDEO_QUALITY
        params = {
            "op": 1,
            "type": quality.value,
            "code": code,
            "pid": self.creds.pid,
        }
        return await self._get(DL_URL, params=params)

    async def download_vcz(
        self,
        fid: str,
        download_dir: Optional[PathLike] = None,
        progress: Optional["ProgressCallback"] = None,
    ) -> None:
        """Download a vcz.

        Arguments:
            fid: Video FID.
            download_dir: Directory for downloaded files. Defaults to the
                current working dir.
            progress: Optional progress callback.
        """
        await self.status_chk()
        resp = await self._request_vcz(fid)
        await self._download(resp, download_dir=download_dir, progress=progress)

    async def _request_vcz(self, fid: str) -> aiohttp.ClientResponse:
        assert self.creds is not None
        params = {
            "pid": self.creds.pid,
            "fid": fid,
        }
        headers = {"Accept-Encoding": "gzip, identity"}
        return await self._get(VCS_DL_URL, params=params, headers=headers)

    async def register_player(
        self,
        username: str,
        password: str,
    ) -> BaseCredentials:
        """Login to LPEG and register as new VR-capable player.

        Arguments:
            username: Afesta/LPEG login username.
            password: Password for `username` account.

        Note:
            `password` will not be saved. Only `username` and API tokens are
            saved in credentials.

        Returns:
            Newly registered credentials.

        Raises:
            AuthenticationError: An authentication error occured.
        """
        device_id = BaseCredentials.get_device_id()
        try:
            resp = await self._get(AP_REG_URL, params={"pid": device_id})
            data = await resp.json()
            pid = data["mp_no"]
        except (aiohttp.ClientError, KeyError) as exc:
            raise AuthenticationError("Player registration failed.") from exc
        try:
            resp = await self._post(
                AP_LOGIN_URL,
                data={
                    "uid": username,
                    "pass": password,
                    "pid": pid,
                    "type": "dpvr",
                },
            )
            data = (await resp.json()).get("data", {})
            mid = data["mid"]
            st = data["st"]
        except (aiohttp.ClientError, KeyError) as exc:
            raise AuthenticationError("Login failed.") from exc
        self.creds = self.new_credentials(uid=username, st=st, mid=mid, pid=pid)
        return self.creds

    @abstractmethod
    def new_credentials(self, *args: Any, **kwargs: Any) -> BaseCredentials:
        """Return a new credentials instance."""


class FourDClient(BaseLpegClient):
    """4D Media Player client.

    All LPEG API calls will be made in the same way as 4D Media Player, except
    for video downloads. Video quality will default to `VideoQuality.PC_SBS`,
    which is the Afesta default in the web UI for PC downloads, and
    is the default for in-client 4D Media Player downloads.
    """

    @property
    def user_agent(self) -> str:
        """Return the HTTP User-Agent for this client."""
        return "BestHTTP 1.12.3"  # UA as of 4D Media Player 2.0.1

    def new_credentials(self, *args: Any, **kwargs: Any) -> FourDCredentials:
        """Return a new credentials instance."""
        return FourDCredentials(*args, **kwargs)
