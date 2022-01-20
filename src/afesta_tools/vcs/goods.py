"""VCS interlocking goods module."""
import enum
import io
from typing import Union

from a10sa_script.command import VorzeLinearCommand
from a10sa_script.command import VorzeRotateCommand
from a10sa_script.command import VorzeVibrateCommand
from a10sa_script.script import VCSXCycloneScript
from a10sa_script.script import VCSXOnaRhythmScript
from a10sa_script.script import VCSXPistonScript
from a10sa_script.script import VCSXScript


GoodsScript = Union[
    VCSXScript[VorzeLinearCommand],
    VCSXScript[VorzeRotateCommand],
    VCSXScript[VorzeVibrateCommand],
]


class GoodsType(enum.Enum):
    """Interlocking goods type.

    Attributes:
        CYCLONE: Vorze CycloneSA devices.
        PISTON: Vorze Piston devices.
        ONARHYTHM: Vorze OnaRhythm devices (Rocket+1D).
    """

    CYCLONE = "Vorze_CycloneSA"
    PISTON = "Vorze_Piston"
    ONARHYTHM = "Vorze_OnaRhythm"


def load_script(typ: GoodsType, data: bytes) -> GoodsScript:
    """Load interlocking goods script data.

    Arguments:
        typ: Goods type.
        data: Script binary (VCSX) data.

    Returns:
        VCSX script.

    Raises:
        ValueError: Invalid goods type.
    """
    with io.BytesIO(data) as f:
        if typ == GoodsType.CYCLONE:
            return VCSXCycloneScript.load(f)
        if typ == GoodsType.PISTON:
            return VCSXPistonScript.load(f)
        # else typ == GoodsType.ONARHYTHM
        return VCSXOnaRhythmScript.load(f)
