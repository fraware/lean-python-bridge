#!/usr/bin/env python3
"""
Regenerate python/requirements-{runtime,dev}.lock.txt with sha256 hashes.

Targets Linux x86_64 + CPython 3.11 wheels (matches CI and python:3.11-slim images).
Requires: pip (bundles packaging). Invokes `pip download` and `pip hash`.
"""
from __future__ import annotations

import email.parser
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from packaging.utils import parse_wheel_filename

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "python"
WHEEL_ARGS = [
    "--platform",
    "manylinux2014_x86_64",
    "--python-version",
    "311",
    "--implementation",
    "cp",
    "--abi",
    "cp311",
    "--only-binary=:all:",
]


def _canonical_name_from_wheel(path: Path) -> str:
    """Read Package-Name from wheel METADATA (handles boolean.py, PyYAML, etc.)."""
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if name.endswith(".dist-info/METADATA"):
                raw = zf.read(name).decode("utf-8", errors="replace")
                msg = email.parser.Parser().parsestr(raw)
                pkg = msg.get("Name")
                if pkg:
                    return pkg.strip()
                break
    return str(parse_wheel_filename(path.name)[0])


def _pip_hash(path: Path) -> str:
    out = subprocess.check_output(
        [sys.executable, "-m", "pip", "hash", str(path)],
        text=True,
    )
    for line in out.splitlines():
        line = line.strip()
        prefix = "--hash=sha256:"
        if line.startswith(prefix):
            return line[len(prefix) :]
    raise RuntimeError(f"No hash in pip hash output for {path}")


def _build_lock(req_in: Path, out_lock: Path, scratch: Path) -> None:
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "-r",
            str(req_in),
            "-d",
            str(scratch),
            *WHEEL_ARGS,
        ],
        cwd=ROOT,
    )
    entries: list[tuple[str, str]] = []
    for whl in sorted(scratch.glob("*.whl")):
        _name, version, _build, _tags = parse_wheel_filename(whl.name)
        h = _pip_hash(whl)
        req_name = _canonical_name_from_wheel(whl)
        line = f"{req_name}=={version} --hash=sha256:{h}"
        entries.append((req_name.lower(), line))

    header = (
        "# Hashed lock for Linux x86_64, CPython 3.11 (manylinux2014_x86_64 wheels).\n"
        "# Regenerate: python scripts/compile_python_locks.py\n"
    )
    sorted_lines = [e[1] for e in sorted(entries, key=lambda x: x[0])]
    out_lock.write_text(header + "\n".join(sorted_lines) + "\n", encoding="utf-8")


def main() -> None:
    _build_lock(
        PYTHON / "requirements-runtime.in",
        PYTHON / "requirements-runtime.lock.txt",
        ROOT / ".pip-wheelhouse-runtime",
    )
    _build_lock(
        PYTHON / "requirements-dev.in",
        PYTHON / "requirements-dev.lock.txt",
        ROOT / ".pip-wheelhouse-dev",
    )
    print("Wrote", PYTHON / "requirements-runtime.lock.txt")
    print("Wrote", PYTHON / "requirements-dev.lock.txt")


if __name__ == "__main__":
    main()
