from datetime import date
from pathlib import Path

from cassandra_nosql.load_data.loaders.constants import YELP_JSON_DIR
from cassandra_nosql.load_data.loaders.utils import read_ndjson
from cassandra_nosql.models.cassndra import UsersByBusiness as CassandraUsersByBusiness
from cassandra_nosql.models.yelp.tip import Tip as YelpTip


def conversion(yelp_model: YelpTip) -> CassandraUsersByBusiness:
    cassandra_model = CassandraUsersByBusiness()
    cassandra_model.id = yelp_model.user_id
    cassandra_model.tip_business_id = yelp_model.business_id
    cassandra_model.tipped_at = date.fromisoformat(yelp_model.date[:10])
    return cassandra_model


def convert(path: Path) -> list[CassandraUsersByBusiness]:
    yelp_models = read_ndjson(path, YelpTip)
    cassandra_models = [conversion(yelp_model) for yelp_model in yelp_models]

    for cassandra_model in cassandra_models:
        cassandra_model.save()

    return cassandra_models


def load():
    convert(YELP_JSON_DIR / "tip.json")
