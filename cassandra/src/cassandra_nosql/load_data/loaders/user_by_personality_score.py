from pathlib import Path

import msgspec

from cassandra_nosql.load_data.loaders.constants import YELP_JSON_DIR
from cassandra_nosql.models.cassndra import (
    UserByPersonalityScore as CassandraUserByPersonalityScore,
)
from cassandra_nosql.models.yelp.user import User as YelpUser


def count_values(value: str) -> int:
    if not value or value == "None":
        return 0

    return len(value.split(", "))


def conversion(yelp_model: YelpUser) -> CassandraUserByPersonalityScore:
    cassandra_model = CassandraUserByPersonalityScore()
    cassandra_model.user_id = yelp_model.user_id
    cassandra_model.friends = count_values(yelp_model.friends)
    cassandra_model.elite = count_values(yelp_model.elite)
    cassandra_model.cool = yelp_model.cool
    cassandra_model.fans = yelp_model.fans
    return cassandra_model


def convert(path: Path) -> list[CassandraUserByPersonalityScore]:
    with open(path, "rb") as yelp_model_json:
        yelp_models = msgspec.json.decode(
            yelp_model_json.read(),
            type=list[YelpUser],
        )
        cassandra_models = [conversion(yelp_model) for yelp_model in yelp_models]

        for cassandra_model in cassandra_models:
            cassandra_model.save()

    return cassandra_models


def load():
    convert(YELP_JSON_DIR / "user.json")
