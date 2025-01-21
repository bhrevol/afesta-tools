"""Test cases for the progress module."""
from collections.abc import Generator

import pytest
from tqdm import tqdm

from afesta_tools.progress import ProgressCallback


PbarFixture = Generator[tqdm, None, None]


@pytest.fixture
def pbar() -> PbarFixture:
    """Fixture for default progress bar."""
    with tqdm() as pbar:
        yield pbar


def test_set_desc(pbar: PbarFixture) -> None:
    """Callback should update pbar description."""
    progress = ProgressCallback(pbar)
    progress.set_desc("foo")
    assert pbar.desc == "foo: "  # type: ignore[attr-defined]


@pytest.mark.parametrize("n", [10, 10.0])
def test_set_total(pbar: PbarFixture, n: int | float) -> None:
    """Callback should update pbar total."""
    progress = ProgressCallback(pbar)
    progress.set_total(n)
    assert pbar.total == n  # type: ignore[attr-defined]


@pytest.mark.parametrize("n", [1, 1.0])
def test_update(pbar: PbarFixture, n: int | float) -> None:
    """Callback should update pbar counter."""
    progress = ProgressCallback(pbar)
    progress.update(n)
    assert pbar.n == n  # type: ignore[attr-defined]
    progress.update(n)
    assert pbar.n == 2 * n  # type: ignore[attr-defined]
