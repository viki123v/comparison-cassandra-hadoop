from pathlib import Path

from cassandra_nosql.load_data.loaders.constants import YELP_JSON_DIR
from cassandra_nosql.load_data.loaders.utils import read_ndjson
from cassandra_nosql.models.cassndra import (
    UserByPersonalityScore as CassandraUserByPersonalityScore,
)
from cassandra_nosql.models.yelp.user import User as YelpUser


def count_values(value: str) -> int:
    if not value or value == "None":
        return 0

    return len(value.split(", "))


def conversion(yelp_model: YelpUser) -> CassandraUserByPersonalityScore:
    friends = count_values(yelp_model.friends)
    elite = count_values(yelp_model.elite)
    cassandra_model = CassandraUserByPersonalityScore()
    cassandra_model.user_id = yelp_model.user_id
    cassandra_model.friends = friends
    cassandra_model.elite = elite
    cassandra_model.cool = yelp_model.cool
    cassandra_model.fans = yelp_model.fans
    cassandra_model.personality_score = (
        friends + elite + yelp_model.cool + yelp_model.fans
    ) / 4
    return cassandra_model


def convert(path: Path) -> list[CassandraUserByPersonalityScore]:
    yelp_models = read_ndjson(path, YelpUser)
    cassandra_models = [conversion(yelp_model) for yelp_model in yelp_models]
    cassandra_models.sort(key=lambda model: (-model.personality_score, model.user_id))
    for rank, cassandra_model in enumerate(cassandra_models, start=1):
        cassandra_model.global_rank = rank

    for cassandra_model in cassandra_models:
        cassandra_model.save()

    return cassandra_models


def load():
    convert(YELP_JSON_DIR / "user.json")
