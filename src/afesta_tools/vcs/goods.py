"""VCS interlocking goods module."""
import enum
import io
from typing import Literal
from typing import Union
from typing import cast

from a10sa_script.script import FunscriptScript
from a10sa_script.script import VCSXCycloneScript
from a10sa_script.script import VCSXOnaRhythmScript
from a10sa_script.script import VCSXPistonScript
from a10sa_script.script import VorzeLinearScript
from a10sa_script.script import VorzeRotateScript
from a10sa_script.script import VorzeVibrateScript


GoodsScript = Union[
    VCSXCycloneScript,
    VCSXOnaRhythmScript,
    VCSXPistonScript,
]
ConvertedScript = Union[
    GoodsScript,
    FunscriptScript,
    VorzeLinearScript,
    VorzeRotateScript,
    VorzeVibrateScript,
]
ScriptFormat = Literal["csv", "vcsx", "funscript"]


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
            return cast(VCSXCycloneScript, VCSXCycloneScript.load(f))
        if typ == GoodsType.PISTON:
            return cast(VCSXPistonScript, VCSXPistonScript.load(f))
        if typ == GoodsType.ONARHYTHM:
            return cast(VCSXOnaRhythmScript, VCSXOnaRhythmScript.load(f))
    raise ValueError("Invalid goods type")


def convert_script(script: GoodsScript, fmt: ScriptFormat) -> ConvertedScript:
    """Convert interlocking goods script data.

    Arguments:
        script: Goods script.
        fmt: Output script format.

    Returns:
        Converted script.

    Raises:
        ValueError: Unsupported output format.
    """
    if fmt == "vcsx":
        return script
    if isinstance(script, VCSXCycloneScript):
        if fmt == "csv":
            return VorzeRotateScript(script.commands)
    if isinstance(script, VCSXOnaRhythmScript):
        if fmt == "csv":
            return VorzeVibrateScript(script.commands)
    if isinstance(script, VCSXPistonScript):
        if fmt == "csv":
            return VorzeLinearScript(script.commands)
        if fmt == "funscript":
            return FunscriptScript(script.commands)
    raise ValueError(f"Unable to convert {script} to format {fmt}")
