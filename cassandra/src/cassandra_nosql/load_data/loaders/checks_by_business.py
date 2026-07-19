from datetime import date
from pathlib import Path

import msgspec

from cassandra_nosql.load_data.loaders.constants import YELP_JSON_DIR
from cassandra_nosql.models.cassndra import ChecksByBusiness as CassandraChecksByBusiness
from cassandra_nosql.models.yelp.checkin import Checkin as YelpCheckin


def conversion(
    yelp_model: YelpCheckin,
    checked_at: str,
) -> CassandraChecksByBusiness:
    cassandra_model = CassandraChecksByBusiness()
    cassandra_model.business_id = int(yelp_model.business_id)
    cassandra_model.checked_at = date.fromisoformat(checked_at[:10])
    return cassandra_model


def convert(path: Path) -> list[CassandraChecksByBusiness]:
    with open(path, "rb") as yelp_model_json:
        yelp_models = msgspec.json.decode(
            yelp_model_json.read(),
            type=list[YelpCheckin],
        )
        cassandra_models = [
            conversion(yelp_model, checked_at)
            for yelp_model in yelp_models
            for checked_at in yelp_model.date.split(", ")
        ]

        for cassandra_model in cassandra_models:
            cassandra_model.save()

    return cassandra_models


def load():
    convert(YELP_JSON_DIR / "checkin.json")
