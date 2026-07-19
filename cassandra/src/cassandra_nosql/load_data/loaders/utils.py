from pathlib import Path
from typing import TypeVar

import msgspec

T = TypeVar("T")

def read_ndjson(path: Path, model_type: type[T]) -> list[T]:
    decoder = msgspec.json.Decoder(type=model_type)
    with open(path, "rb") as yelp_model_json:
        return [
            decoder.decode(line)
            for line in yelp_model_json
            if line.strip()
        ]

SPLIT_BOUND=5
def handle_composite_object(composite:str, delimiter: str = ', '):
    composite_split = composite.split(delimiter)
    return composite_split[:SPLIT_BOUND]
