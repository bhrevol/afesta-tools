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

    def update(self, inc: Union[int, float] = 1) -> None:
        """Increment pbar progress."""
        self.pbar.update(inc)
