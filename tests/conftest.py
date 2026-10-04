"""Shared fixtures."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrinium import categories as cat_mod      # noqa: E402
from scrinium import rules as rules_mod          # noqa: E402


@pytest.fixture
def empty_dir(tmp_path):
    d = tmp_path / "Downloads"
    d.mkdir()
    return d


@pytest.fixture
def targets(empty_dir):
    return {k: str(empty_dir / cat_mod.folder_name(k, "de"))
            for k in cat_mod.DEFAULT_KEYS}


@pytest.fixture
def resolver():
    return rules_mod.Resolver()


@pytest.fixture
def make_file(empty_dir):
    """Create a file with a given name, size and mtime offset in seconds."""
    def _make(name, size=100, age_s=0):
        p = empty_dir / name
        p.write_bytes(b"x" * size)
        if age_s:
            import time

            t = time.time() - age_s
            os.utime(p, (t, t))
        return p
    return _make