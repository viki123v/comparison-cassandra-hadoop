from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import TypeVar

import msgspec

from hbase.load_data.loaders.constants import RELATION_LIMIT


T = TypeVar("T")


def read_ndjson(path: Path, model_type: type[T]) -> Iterator[T]:
    decoder = msgspec.json.Decoder(type=model_type)
    with path.open("rb") as source:
        for line in source:
            if line.strip():
                yield decoder.decode(line)


def parse_date(value: str) -> date:
    return date.fromisoformat(value[:10])


def split_composite(value: str, limit: int | None = None) -> list[str]:
    if not value or value == "None":
        return []
    values = value.split(", ")
    return values if limit is None else values[:limit]


def limited_relations(value: str) -> list[str]:
    return split_composite(value, RELATION_LIMIT)


def count_composite(value: str) -> int:
    return len(split_composite(value))


def columns(**values: str | int | float) -> dict[bytes, bytes]:
    return {
        f"d:{name}".encode("ascii"): _encode(value) for name, value in values.items()
    }


def _encode(value: str | int | float) -> bytes:
    if isinstance(value, str):
        return value.encode("utf-8")
    return str(value).encode("ascii")
