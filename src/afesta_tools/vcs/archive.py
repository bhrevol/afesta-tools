"""VCZ (zip-compressed VCS) archive module."""
import threading
import zipfile
from functools import cached_property
from typing import Any
from typing import AsyncContextManager
from typing import List
from typing import Literal
from typing import Optional
from typing import Union

from lxml import etree  # noqa: S410

from ..types import PathLike
from ..utils import to_thread
from .goods import GoodsScript
from .goods import GoodsType
from .goods import load_script


class VCZArchive(AsyncContextManager["VCZArchive"]):
    """VCZ archive."""

    def __init__(self, filename: PathLike, mode: Literal["r", "a"] = "r") -> None:
        """Open a VCZ archive.

        Arguments:
            filename: Path to VCZ file.
            mode: ``r`` to read an existing file, ``a`` to append (edit) an existing
                file.

        Raises:
            ValueError: `filename` is not a valid VCZ archive.
        """
        self.filename = filename
        self._zip = zipfile.ZipFile(self.filename, mode=mode)
        self._lock = threading.Lock()
        params = self._load_params()
        sys_params = params.find("system")
        if sys_params is None:
            raise ValueError(f"{filename} has no VCS system params")
        self._sys_params = sys_params
        names = self._zip.namelist()
        self._name_infos = {
            element.tag: element.text
            for element in self._sys_params
            if element.text in names
        }

    def _load_params(self) -> etree._Element:
        """Return the contents of params.xml."""
        try:
            params_info = self._zip.getinfo("params.xml")
        except KeyError as e:
            raise ValueError(f"{self.filename} has no VCS params") from e
        parser = etree.XMLParser(resolve_entities=False)
        return etree.fromstring(  # noqa: S320
            self._zip_read(params_info), parser=parser
        )

    @cached_property
    def title(self) -> Optional[str]:
        """Video title."""
        return self._sys_params.findtext("title")

    def namelist(self) -> List[str]:
        """Return a list of archive members by name."""
        return list(self._name_infos.keys())

    async def __aexit__(self, *args: Any, **kwargs: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close this client."""
        self._zip.close()

    def _zip_read(self, name: Union[str, zipfile.ZipInfo]) -> bytes:
        with self._lock:
            return self._zip.read(name)

    async def read(self, name: str) -> bytes:
        """Read the specified file from this archive.

        Arguments:
            name: File to read.

        Returns:
            File data.

        Raises:
            KeyError: `name` does not exist in the archive.
        """
        return await to_thread(self._zip_read, self._name_infos[name])

    async def read_script(self, typ: GoodsType) -> GoodsScript:
        """Read the specified interlocking goods script.

        Arguments:
            typ: Goods type.

        Returns:
            VCSX script.

        Raises:
            KeyError: The specified goods type is not supported for this video.
        """
        data = await self.read(typ.value)
        return load_script(typ, data)
