'''Common utilities for RunRunner.'''
from __future__ import annotations

from datetime import datetime
import shlex
import subprocess
from pathlib import Path


def simple_run(cmd: str) -> subprocess.CompletedProcess:
    '''Run a subprocess.

    Wrapper for subprocess.run with simple default.
    '''
    return subprocess.run(
        shlex.split(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True)


def quote(str_or_path: str | Path) -> str:
    '''Return a quoted str for str or Path inputs.

    Wrapper around shlex.quote that convert "str_or_path" to string
    before quoting. Prevents an error when passing a pathlib.Path.
    '''
    return shlex.quote(str(str_or_path))


def timestampedname() -> str:
    '''Return a str formed from the date and time.

    Example: "20220211.151805.542754"
    '''
    return datetime.now().strftime('%Y%m%d.%H%M%S.%f')
