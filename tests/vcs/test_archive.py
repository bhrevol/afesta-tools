"""Tests for the VCS archive module."""
from typing import AsyncGenerator
from typing import cast
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from lxml import etree  # noqa: S410
from pytest_mock import MockerFixture

from afesta_tools.vcs import GoodsType
from afesta_tools.vcs import VCZArchive


TEST_PARAMS_XML = b"""<?xml version="1.0" encoding="UTF-8" ?>
<params>
  <system>
    <title>Title</title>
    <image>image.jpg</image>
    <HeadKey ext="1d+">HeadKey1d+.bin</HeadKey>
    <ChapterControl>ChapterControl.bin</ChapterControl>
    <Vorze_CycloneSA>Vorze_CycloneSA.bin</Vorze_CycloneSA>
    <Vorze_Piston>Vorze_Piston.bin</Vorze_Piston>
    <Vorze_OnaRhythm>Vorze_OnaRhythm.bin</Vorze_OnaRhythm>
    <projection>FishEye</projection>
    <DomeAngle>180</DomeAngle>
    <stereo>1</stereo>
  </system>
</params>
"""


@pytest.fixture
def zmock(mocker: MockerFixture) -> MagicMock:
    """Fixture to mock zipfile class."""
    mock = mocker.MagicMock()
    mocker.patch("zipfile.ZipFile", return_value=mock)
    return cast(MagicMock, mock)


@pytest.fixture
def params(mocker: MockerFixture) -> etree._Element:
    """Fixture to mock test params.xml."""
    params = etree.fromstring(TEST_PARAMS_XML)  # noqa: S320
    mocker.patch("lxml.etree.fromstring", return_value=params)
    return params


@pytest_asyncio.fixture
async def vcz(
    mocker: MockerFixture, zmock: MagicMock, params: etree._Element
) -> AsyncGenerator[VCZArchive, None]:
    """Fixture to generate test/mocked VCZ."""
    zmock.namelist = mocker.Mock(
        return_value=[
            "HeadKey1d+.bin",
            "ChapterControl.bin",
            "Vorze_CycloneSA.bin",
            "Vorze_Piston.bin",
            "Vorze_OnaRhythm.bin",
        ]
    )
    async with VCZArchive("foo.vcz") as vcz:
        yield vcz


def test_invalid_no_params(mocker: MockerFixture, zmock: MagicMock) -> None:
    """Init should fail."""
    zmock.getinfo = mocker.Mock(side_effect=KeyError)
    with pytest.raises(ValueError):
        VCZArchive("foo.vcz")


def test_invalid_no_system(mocker: MockerFixture, zmock: MagicMock) -> None:
    """Init should fail."""
    mocker.patch("lxml.etree.fromstring", return_value=etree.Element("params"))
    with pytest.raises(ValueError):
        VCZArchive("foo.vcz")


async def test_init(vcz: VCZArchive) -> None:
    """Params should be initialized."""
    assert vcz.title == "Title"
    print(vcz._name_infos)
    assert vcz.namelist() == [
        "HeadKey",
        "ChapterControl",
        "Vorze_CycloneSA",
        "Vorze_Piston",
        "Vorze_OnaRhythm",
    ]


async def test_read(mocker: MockerFixture, vcz: VCZArchive) -> None:
    """Should return zip data."""
    data = b"data"
    read = mocker.patch.object(vcz._zip, "read", return_value=data)
    with pytest.raises(KeyError):
        await vcz.read("not_in_archive")
    assert await vcz.read("HeadKey") == data
    assert read.called_with("HeadKey1d+.bin")


@pytest.mark.parametrize(
    "typ", [GoodsType.CYCLONE, GoodsType.ONARHYTHM, GoodsType.PISTON]
)
async def test_read_script(
    mocker: MockerFixture, vcz: VCZArchive, typ: GoodsType
) -> None:
    """Should call load_script."""
    mocker.patch.object(vcz._zip, "read", return_value=b"data")
    load_script = mocker.patch("afesta_tools.vcs.archive.load_script")
    await vcz.read_script(typ)
    assert load_script.called_with(typ, b"data")
