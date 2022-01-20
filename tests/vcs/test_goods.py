"""Tests for the VCS goods module."""
from typing import Type
from typing import TypeVar

import pytest
from a10sa_script.command.vorze import BaseVorzeCommand
from a10sa_script.script import VCSXCycloneScript
from a10sa_script.script import VCSXOnaRhythmScript
from a10sa_script.script import VCSXPistonScript
from a10sa_script.script import VCSXScript
from pytest_mock import MockerFixture

from afesta_tools.vcs.goods import GoodsScript
from afesta_tools.vcs.goods import GoodsType
from afesta_tools.vcs.goods import load_script


_T = TypeVar("_T", bound=BaseVorzeCommand)


@pytest.mark.parametrize(
    "typ, cls",
    [
        (GoodsType.CYCLONE, VCSXCycloneScript),
        (GoodsType.PISTON, VCSXPistonScript),
        (GoodsType.ONARHYTHM, VCSXOnaRhythmScript),
    ],
)
def test_load_script(
    mocker: MockerFixture, typ: GoodsType, cls: Type[VCSXScript[_T]]
) -> None:
    """Should load the approrpiate script class."""
    mocker.patch.object(cls, "load", return_value=cls([]))
    script: GoodsScript = load_script(typ, b"foo")
    assert isinstance(script, cls)
