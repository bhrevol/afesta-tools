"""LPEG API client."""
import asyncio
import enum
import html
import json
import os
import re
import unicodedata
from abc import abstractmethod
from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from functools import partial
from typing import Any
from typing import AsyncContextManager
from collections.abc import AsyncIterator
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Iterable
from typing import cast
from typing import Literal
from typing import Optional

import aiohttp
from funcy import wraps

from ..exceptions import AfestaError
from ..exceptions import AuthenticationError
from ..exceptions import BadFIDError
from ..progress import ProgressCallback
from ..types import PathLike
from .credentials import BaseCredentials
from .credentials import FourDCredentials


AP_STATUS_CHK_URL = "https://www.lpeg.jp/manage/ap_status_chk.php"
AP_LOGIN_URL = "https://www.lpeg.jp/manage/ap_login.php"
AP_REG_URL = "http://www.lpeg.jp/manage/ap_reg.php"
DL_URL = "https://lpeg.jp/h/"
MP4_DL_URL = "https://www.lpeg.jp/point/mp4_dl.php"
PS_GET_LIST_URL = "https://www.lpeg.jp/manage/ps_get_list.php"
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


class PSListType(enum.IntEnum):
    """Request type for ps_get_list."""

    PURCHASES = 1
    FAVORITES = 2


_CLEAN_TITLE_RE = re.compile(r"^(?:(?:【.*】)|(?:\[?.*\]))*\s*(?P<title>.*)$")
_FID_RE = re.compile(r"^(?P<full>(?P<fid>.*?)(?:(?P<set_suffix>\-(?:R|Part))\d+)?)_st$")


@dataclass(frozen=True)
class PSListEntry:
    """PS Video list entry.

    Attributes:
        acters: Actresses.
        big_img: Main cover image URL.
        categories: Genre tags.
        code: Purchase code. Only applicable when `dl` is True.
        comment: Video description.
        dl: True if video can be downloaded.
        favorite: True if video is favorited.
        file_name: Streaming playlist filename.
        id: Page entry ID. Note that this is not a video ID. The ID only has meaning
            within a single page of the ps_get_list response list.
        img: First preview/gallery image URL.
        maker: Video maker, never set.
        quality: Quality abbreviation (i.e. "HQ60").
        release_date: Release timestamp.
        set_num: 0-indexed number of parts for this video set. None if video does not
            have multiple parts.
        signal: True if video supports linked goods.
        time: Total video duration in seconds.
        title: Abbreviated video title.
        title_all: Full video title.
        ai3d: Video is AI generated.
    """

    acters: list[str]
    big_img: str
    categories: list[str]
    code: str | None
    comment: str
    dl: bool
    favorite: bool
    file_name: str
    id: int
    img: str
    maker: str
    quality: str
    release_date: datetime
    set_num: int | None
    signal: bool
    time: int
    title: str
    title_all: str
    item_id: str
    ai3d: int

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PSListEntry":
        """Return an entry from an LPEG API JSON dict."""
        acters = [actor.strip() for actor in d.pop("acters").split(",")]
        categories = [cat.strip() for cat in d.pop("categories").split(",")]
        comment = html.unescape(d.pop("comment")).replace("<BR>", "\n")
        dl = d.pop("dl") != 0
        favorite = d.pop("favorite") != 0
        release_date = datetime.fromisoformat(d.pop("release_date")).replace(
            tzinfo=timezone(timedelta(hours=9), name="JST")
        )
        n = d.pop("set_num")
        set_num = int(n) if n != "0" else None
        signal = d.pop("signal") != 0
        return cls(
            acters=acters,
            categories=categories,
            comment=comment,
            dl=dl,
            favorite=favorite,
            release_date=release_date,
            set_num=set_num,
            signal=signal,
            **d,
        )

    @property
    def title_clean(self) -> str:
        """Return clean title.

        Any quality prefix blocks (i.e. 【4K匠】) will be stripped and unicode
        characters will be normalized in the NFKC form.
        """
        m = _CLEAN_TITLE_RE.match(self.title_all)
        title = m.group("title") if m else self.title_all
        return unicodedata.normalize("NFKC", title)

    def get_fid(self, part: int | None = None) -> str:
        """Return Afesta FID.

        Arguments:
            part: FID for the specified set part will be returned when specified.

        Returns:
            Video FID.

        Raises:
            ValueError: `part` is invalid.
        """
        if part is not None:
            if part < 1 or (self.num_parts is not None and part > self.num_parts):
                raise ValueError("Invalid part number")
        stem, _ = os.path.splitext(self.file_name)
        m = _FID_RE.match(stem)
        if m:
            if self.num_parts is None:
                return m.group("full")
            fid = m.group("fid")
            if part is None:
                return fid
            set_suffix = m.group("set_suffix")
            return f"{fid}{set_suffix}{part}"
        return stem

    @property
    def num_parts(self) -> int | None:
        """Return total number of parts."""
        if self.set_num is None:
            return None
        return self.set_num + 1

    @property
    def duration(self) -> timedelta:
        """Return total video duration as a Python timedelta."""
        return timedelta(seconds=self.time)


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
    _CLIENT_TIMEOUT = 5 * 60

    def __init__(self, creds: BaseCredentials | None = None) -> None:
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

    @property
    def _dl_timeout(self) -> aiohttp.ClientTimeout:
        """Return download timeout."""
        return aiohttp.ClientTimeout(
            total=None,
            connect=self._CLIENT_TIMEOUT,
            sock_connect=self._CLIENT_TIMEOUT,
            sock_read=None,
        )

    async def _get(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        return await self._session.get(url, **kwargs)

    async def _post(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        return await self._session.post(url, **kwargs)

    @require_auth
    async def status_chk(self) -> dict[str, Any]:
        """Run ap_status_chk API request."""
        assert self.creds is not None
        payload = {
            "st": self.creds.st,
            "mid": self.creds.mid,
            "pid": self.creds.pid,
            "type": "dpvr",
        }
        resp = await self._post(AP_STATUS_CHK_URL, data=payload)
        return cast(dict[str, Any], await resp.json())

    async def _download(
        self,
        response: aiohttp.ClientResponse,
        download_dir: PathLike | None = None,
        progress: ProgressCallback | None = None,
    ) -> None:
        if response.content_disposition:
            filename: str | None = response.content_disposition.filename
        else:  # pragma: no cover
            filename = None
        if not filename:  # pragma: no cover
            raise AfestaError("Not a valid file download URL")
        if download_dir:
            filename = os.path.join(download_dir, filename)
        if progress:
            if "Content-Length" in response.headers:  # pragma: no cover
                progress.set_total(int(response.headers["Content-Length"]))
        with open(filename, mode="wb") as fp:
            async for chunk in response.content.iter_chunked(self.CHUNK_SIZE):
                fp.write(chunk)
                if progress is not None:
                    progress.update(len(chunk))

    @require_auth
    async def download_video(  # noqa: C901
        self,
        code: str | None = None,
        fid: str | None = None,
        download_dir: PathLike | None = None,
        quality: VideoQuality | None = None,
        progress: ProgressCallback | None = None,
        vr: bool = True,
        parts: Iterable[int] | None = None,
        lang: Literal["JP", "EN"] = "JP",
    ) -> None:
        """Download a video.

        Arguments:
            code: Video code (LPEG purchase code). Takes precedence over `fid`.
            fid: Video FID. When `fid` is set, client will attempt to search for an
                available download matching the specified `fid`.
            download_dir: Directory for downloaded files. Defaults to the
                current working dir.
            quality: Video quality. Defaults to `DEFAULT_VIDEO_QUALITY`.
            progress: Optional progress callback.
            vr: True for VR listing, False for 2D. Only applicable when using `fid`.
            parts: Specific parts to download. Defaults to downloading all parts. Only
                applicable when using `fid`.
            lang: Metadata language for returned videos when using `fid`.

        Either `code` or `fid` must be set.

        Note:
            Actual download quality may be worse than the requested value
            depending on the video.

        Raises:
            ValueError: Both `code` and `fid` were not set.
            BadFIDError: The specified `fid` was invalid or ambiguous.
            AfestaError: An unexpected error occurred while downloading.
        """
        if code:
            codes = [code]
            desc = f"Downloading purchase {code}"
        else:
            if not fid:
                raise ValueError("Either code or fid must be set.")
            videos = [
                video async for video in self.get_videos(vr=vr, words=fid, lang=lang)
            ]
            if not videos:
                raise BadFIDError(f"Could not find any video matching FID {fid}.")
            if len(videos) > 1:
                matches = [v.get_fid() for v in videos]
                raise BadFIDError(
                    f"Got multiple possible matches for FID: {', '.join(matches)}"
                )
            video = videos[0]
            assert video.code
            if video.set_num is None:
                codes = [video.code]
                desc_parts = ""
            else:
                codes = []
                assert video.num_parts is not None
                for part in parts or range(1, video.num_parts + 1):
                    # NOTE: multipart download codes are 0-indexed
                    # i.e. <code>_1 corresponds to video part <fid>-R2
                    if part > video.num_parts:
                        pass
                    elif part == 1:
                        codes.append(video.code)
                    else:
                        codes.append(f"{video.code}_{part - 1}")
                desc_parts = f" ({len(codes)} parts)"
            desc = f"Downloading {video.get_fid()}: {video.title}{desc_parts}"

        if progress is not None:
            progress.set_desc(desc)
        results = await asyncio.gather(
            *(
                self._download_code(
                    code, download_dir=download_dir, quality=quality, progress=progress
                )
                for code in codes
            ),
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, BaseException):
                raise AfestaError("File download failed") from r

    async def _download_code(
        self,
        code: str,
        download_dir: PathLike | None = None,
        quality: VideoQuality | None = None,
        progress: ProgressCallback | None = None,
    ) -> None:
        resp = await self._request_video(code, quality=quality)
        await self._download(resp, download_dir=download_dir, progress=progress)

    async def _request_video(
        self,
        code: str,
        quality: VideoQuality | None = None,
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
        return await self._get(DL_URL, params=params, timeout=self._dl_timeout)

    async def download_vcz(
        self,
        fid: str,
        download_dir: PathLike | None = None,
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
        return await self._get(
            VCS_DL_URL, params=params, headers=headers, timeout=self._dl_timeout
        )

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
            result = await resp.json()
            data = result.get("data", {})
            mid = data["mid"]
            st = data["st"]
        except (aiohttp.ClientError, KeyError) as exc:
            raise AuthenticationError("Login failed.") from exc
        if result.get("result", 0) != 1:
            raise AuthenticationError("Login failed.")
        self.creds = self.new_credentials(uid=username, st=st, mid=mid, pid=pid)
        if (await self.status_chk()).get("reg", 0) != 1:
            raise AuthenticationError("Player registration failed.")
        return self.creds

    @abstractmethod
    def new_credentials(self, *args: Any, **kwargs: Any) -> BaseCredentials:
        """Return a new credentials instance."""

    async def get_videos(
        self,
        typ: PSListType = PSListType.PURCHASES,
        lang: Literal["EN", "JP"] = "JP",
        vr: bool = True,
        words: str | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[PSListEntry]:
        """Iterate over videos returned by ps_get_list.

        Arguments:
            typ: List type (either purchases or favorites).
            lang: Metadata language for returned videos.
            vr: True for VR listing, False for 2D.
            words: Optional search string for filtering returned videos.
            limit: Maximum number of results to yield.

        Yields:
            Video results.
        """
        _loads = partial(
            json.loads,
            cls=cast(type[json.JSONDecoder], partial(json.JSONDecoder, strict=False)),
        )
        i = page = -1
        num = 36
        while limit is None or (i + 1 < limit):
            resp = await self._request_list(
                typ=typ,
                lang=lang,
                vr=vr,
                words=words,
                page=page + 1,
                num=num,
            )
            result = await resp.json(loads=_loads)
            count = result["page"]["count"]
            pagecount = result["page"]["pagecount"]
            page = result["page"]["pageindex"]
            limit = count if limit is None else min(count, limit)
            assert limit is not None
            for d in result.get("data", []):
                entry = PSListEntry.from_dict(d)
                i = num * page + entry.id
                yield entry
                if i + 1 >= limit:
                    break
            if page >= pagecount:
                break

    @require_auth
    async def _request_list(
        self,
        typ: PSListType = PSListType.PURCHASES,
        lang: Literal["EN", "JP"] = "JP",
        vr: bool = True,
        start: int = 0,
        page: int = 0,
        num: int = 36,
        words: str | None = None,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse:
        """Return a ps_get_list results page."""
        assert self.creds is not None
        payload = {
            "st": self.creds.st,
            "mid": self.creds.mid,
            "r": "all",
            "type": typ.value,
            "lang": lang,
            "vr": "vr" if vr else "non",
            "cat": "",
            "maker": "",
            "order": "",
            "act": "",
            "photos": "",
            "signal": "",
            "subtitle": "",
            "favorite": "",
            "start": start,
            "page": page,
            "num": num,
        }
        if words:
            payload["words"] = words
        return await self._post(PS_GET_LIST_URL, data=payload)


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
