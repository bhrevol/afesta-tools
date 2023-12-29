"""CLI progress module."""
from typing import Optional
from typing import Union

import tqdm.std


class ProgressCallback:
    """Callbacks for displaying progress in CLI commands."""

    def __init__(self, pbar: tqdm.std.tqdm) -> None:
        """Construct a callback."""
        self.pbar = pbar

    def set_desc(self, desc: str) -> None:
        """Set pbar description."""
        self.pbar.set_description(desc)

    def set_total(self, total: Optional[Union[int, float]]) -> None:
        """Set pbar total."""
        if total is not None:  # pragma: no cover
            self.pbar.total = total
            self.pbar.refresh()

    def inc_total(self, inc: Optional[Union[int, float]]) -> None:
        """Increment pbar total."""
        if inc is not None:
            total = 0 if self.pbar.total is None else self.pbar.total
            self.set_total(total + inc)

    def update(self, inc: Union[int, float] = 1) -> None:
        """Increment pbar progress."""
        self.pbar.update(inc)
