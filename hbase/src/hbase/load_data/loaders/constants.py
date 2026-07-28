from pathlib import Path


YELP_JSON_DIR = Path(__file__).resolve().parents[5] / "yelp_data" / "data" / "output"
BATCH_SIZE = 1_000
RELATION_LIMIT = 5
