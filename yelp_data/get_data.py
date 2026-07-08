#!/usr/bin/env python3

from __future__ import annotations

import os
from pathlib import Path

import kagglehub
from kagglehub.config import get_kaggle_credentials


DATASET_HANDLE = "yelp-dataset/yelp-dataset"
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(__file__).resolve().parent / "data"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def main() -> None:
    load_env_file(ROOT_DIR / ".env")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if get_kaggle_credentials() is None:
        kagglehub.login()

    downloaded_path = kagglehub.dataset_download(
        DATASET_HANDLE,
        output_dir=str(DATA_DIR),
    )

    print(f"Downloaded Yelp dataset to: {downloaded_path}")


if __name__ == "__main__":
    main()
