from datetime import date
from pathlib import Path

from cassandra_nosql.load_data.loaders.constants import YELP_JSON_DIR
from cassandra_nosql.load_data.loaders.utils import read_ndjson
from cassandra_nosql.models.cassndra import TipsByBusiness as CassandraTipsByBusiness
from cassandra_nosql.models.yelp.tip import Tip as YelpTip


def conversion(tip_id: int, yelp_model: YelpTip) -> CassandraTipsByBusiness:
    cassandra_model = CassandraTipsByBusiness()
    cassandra_model.business_id = yelp_model.business_id
    cassandra_model.tip_id = tip_id
    cassandra_model.tipped_at = date.fromisoformat(yelp_model.date[:10])
    cassandra_model.user_id = yelp_model.user_id
    cassandra_model.tip_text = yelp_model.text
    return cassandra_model


def convert(path: Path) -> list[CassandraTipsByBusiness]:
    yelp_models = read_ndjson(path, YelpTip)
    cassandra_models = [
        conversion(tip_id, yelp_model) for tip_id, yelp_model in enumerate(yelp_models)
    ]

    for cassandra_model in cassandra_models:
        cassandra_model.save()

    return cassandra_models


def load():
    convert(YELP_JSON_DIR / "tip.json")
