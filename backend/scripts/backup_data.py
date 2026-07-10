"""SQLite DB と JSON データを backups/ にスナップショット保存する（14世代）。

Usage:
    cd backend && python -m scripts.backup_data
    cd backend && python -m scripts.backup_data --keep 30
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from config import BACKEND_DIR, DATA_DIR

DB_PATH = BACKEND_DIR / "juku_shift.db"
BACKUPS_DIR = BACKEND_DIR / "backups"
DEFAULT_KEEP = 14


def _backup_sqlite(dest: Path) -> None:
    """書き込み中でも整合性が保たれる sqlite3 の backup API を使う。"""
    src = sqlite3.connect(DB_PATH)
    try:
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def _prune_old(keep: int) -> list[str]:
    snapshots = sorted(p for p in BACKUPS_DIR.iterdir() if p.is_dir())
    removed = []
    for old in snapshots[:-keep] if keep > 0 else []:
        shutil.rmtree(old)
        removed.append(old.name)
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description="DB と JSON データをバックアップする")
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP, help="保持する世代数")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    snapshot_dir = BACKUPS_DIR / stamp
    suffix = 1
    while snapshot_dir.exists():
        snapshot_dir = BACKUPS_DIR / f"{stamp}-{suffix}"
        suffix += 1
    snapshot_dir.mkdir(parents=True)

    if DB_PATH.is_file():
        _backup_sqlite(snapshot_dir / DB_PATH.name)
    if DATA_DIR.is_dir():
        shutil.copytree(DATA_DIR, snapshot_dir / "data")

    removed = _prune_old(args.keep)
    print(f"バックアップ完了: {snapshot_dir}")
    if removed:
        print(f"世代管理で削除: {', '.join(removed)}")


if __name__ == "__main__":
    main()
