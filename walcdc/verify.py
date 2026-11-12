"""Sink vs expected — you may implement this as part of the task.

A default, incomplete stub is provided so the command exists.
"""
from __future__ import annotations

import json
from pathlib import Path


def verify(sink: str, expect: str) -> tuple[bool, str]:
    exp = json.loads(Path(expect).read_text())
    # Implementation should load compacted rows from the sink and compare by table/key.
    raise NotImplementedError("implement verify against expected image")
