from datetime import date
from pathlib import Path

import msgspec

from cassandra_nosql.load_data.loaders.constants import YELP_JSON_DIR
from cassandra_nosql.models.cassndra import UsersByBusiness as CassandraUsersByBusiness
from cassandra_nosql.models.yelp.tip import Tip as YelpTip


def conversion(yelp_model: YelpTip) -> CassandraUsersByBusiness:
    cassandra_model = CassandraUsersByBusiness()
    cassandra_model.id = int(yelp_model.user_id)
    cassandra_model.tip_business_id = int(yelp_model.business_id)
    cassandra_model.tipped_at = date.fromisoformat(yelp_model.date[:10])
    return cassandra_model


def convert(path: Path) -> list[CassandraUsersByBusiness]:
    with open(path, "rb") as yelp_model_json:
        yelp_models = msgspec.json.decode(
            yelp_model_json.read(),
            type=list[YelpTip],
        )
        cassandra_models = [conversion(yelp_model) for yelp_model in yelp_models]

        for cassandra_model in cassandra_models:
            cassandra_model.save()

    return cassandra_models


def load():
    convert(YELP_JSON_DIR / "tip.json")
