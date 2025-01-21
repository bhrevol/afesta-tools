"""General utilities module."""
import asyncio
import contextvars
import functools
from collections.abc import Callable
from typing import TypeVar

from typing_extensions import ParamSpec


_P = ParamSpec("_P")
_R = TypeVar("_R")


async def to_thread(func: Callable[_P, _R], *args: _P.args, **kwargs: _P.kwargs) -> _R:
    """Backport of asyncio.to_thread."""
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)
