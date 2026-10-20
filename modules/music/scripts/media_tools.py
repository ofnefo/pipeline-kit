"""Locate operator-installed FFmpeg/ffprobe on PATH; never download tools."""
from __future__ import annotations

import os
import shutil
from pathlib import Path


def find_binary(name='ffmpeg'):
    return shutil.which(name)


def require_binary(name: str = "ffmpeg") -> str:
    found = find_binary(name)
    if not found:
        raise FileNotFoundError(f"{name} not found; install it and add its directory to PATH")
    return found
