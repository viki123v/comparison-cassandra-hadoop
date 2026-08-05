from pathlib import Path

from cassandra_nosql.load_data.loaders.constants import YELP_JSON_DIR
from cassandra_nosql.load_data.loaders.utils import read_ndjson
from cassandra_nosql.models.cassndra import User as CassandraUser
from cassandra_nosql.models.yelp.user import User as YelpUser


def conversion(yelp_model: YelpUser) -> CassandraUser:
    cassandra_model = CassandraUser()
    cassandra_model.id = yelp_model.user_id
    cassandra_model.username = yelp_model.name
    cassandra_model.compliment_hot = yelp_model.compliment_hot
    cassandra_model.compliment_cut = yelp_model.compliment_cute
    cassandra_model.compliment_cool = yelp_model.compliment_cool
    cassandra_model.compliment_funny = yelp_model.compliment_funny
    return cassandra_model


def convert(path: Path) -> list[CassandraUser]:
    yelp_models = read_ndjson(path, YelpUser)
    cassandra_models = [conversion(yelp_model) for yelp_model in yelp_models]

    for cassandra_model in cassandra_models:
        cassandra_model.save()

    return cassandra_models


def load():
    convert(YELP_JSON_DIR / "user.json")
