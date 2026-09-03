"""Save measurement output to disk.

Ported from ``old_spdc_to_port/spdc/savedata.py``, which hardcoded the
output path to ``/home/sci/qkd/data``. That path is now a parameter
(defaulting to ``~/qozy_data``) so this is portable and testable with a
tmp directory instead of writing into a machine-specific lab path.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np

DEFAULT_BASE_DIR = Path.home() / "qozy_data"


def day_folder(base_dir: Path | None = None, when: datetime | None = None) -> Path:
    base_dir = base_dir or DEFAULT_BASE_DIR
    when = when or datetime.now()
    folder = base_dir / str(when.year) / f"{when.month:02d}" / f"{when.day:02d}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def next_file_number(folder: Path, max_files: int = 99) -> str | None:
    """Smallest unused two-digit number in ``folder`` as ``"01"``, ``"02"``, ..."""
    for i in range(1, max_files + 1):
        candidate = f"{i:02d}"
        if not (folder / f"{candidate}.txt").exists():
            return candidate
    return None


def save_measurement(data: np.ndarray, base_dir: Path | None = None) -> Path:
    """Write ``data`` as a tab-delimited txt file in today's dated folder.

    Returns the path written to. Raises ``RuntimeError`` if today's folder
    already has the maximum number of files.
    """
    folder = day_folder(base_dir)
    file_number = next_file_number(folder)
    if file_number is None:
        raise RuntimeError(f"no free file slot in {folder} (100 files already present)")
    path = folder / f"{file_number}.txt"
    np.savetxt(path, data, delimiter="\t", fmt="%f")
    return path
