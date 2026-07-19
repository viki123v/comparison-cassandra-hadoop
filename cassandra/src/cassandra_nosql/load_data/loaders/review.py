from pathlib import Path

import msgspec

from cassandra_nosql.load_data.loaders.constants import YELP_JSON_DIR
from cassandra_nosql.models.cassndra import Review as CassandraReview
from cassandra_nosql.models.yelp.review import Review as YelpReview
from cassandra_nosql.models.yelp.user import User as YelpUser


def conversion(
    yelp_model: YelpReview,
    users_by_id: dict[str, YelpUser],
) -> CassandraReview:
    user = users_by_id.get(yelp_model.user_id)
    cassandra_model = CassandraReview()
    cassandra_model.id = yelp_model.review_id
    cassandra_model.stars = int(yelp_model.stars)
    cassandra_model.username = user.name if user else ""
    return cassandra_model


def convert(
    path: Path,
    user_path: Path = YELP_JSON_DIR / "user.json",
) -> list[CassandraReview]:
    with open(user_path, "rb") as yelp_user_json:
        yelp_users = msgspec.json.decode(
            yelp_user_json.read(),
            type=list[YelpUser],
        )
        users_by_id = {yelp_user.user_id: yelp_user for yelp_user in yelp_users}

    with open(path, "rb") as yelp_model_json:
        yelp_models = msgspec.json.decode(
            yelp_model_json.read(),
            type=list[YelpReview],
        )
        cassandra_models = [
            conversion(yelp_model, users_by_id) for yelp_model in yelp_models
        ]

        for cassandra_model in cassandra_models:
            cassandra_model.save()

    return cassandra_models


def load():
    convert(YELP_JSON_DIR / "review.json")
