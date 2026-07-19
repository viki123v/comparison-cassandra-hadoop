from datetime import date
from pathlib import Path

import msgspec

from cassandra_nosql.load_data.loaders.constants import YELP_JSON_DIR
from cassandra_nosql.models.cassndra import ReviewByUser as CassandraReviewByUser
from cassandra_nosql.models.yelp.review import Review as YelpReview


def conversion(yelp_model: YelpReview) -> CassandraReviewByUser:
    cassandra_model = CassandraReviewByUser()
    cassandra_model.user_id = int(yelp_model.user_id)
    cassandra_model.review_id = int(yelp_model.review_id)
    cassandra_model.reviewed_at = date.fromisoformat(yelp_model.date[:10])
    cassandra_model.stars = int(yelp_model.stars)
    return cassandra_model


def convert(path: Path) -> list[CassandraReviewByUser]:
    with open(path, "rb") as yelp_model_json:
        yelp_models = msgspec.json.decode(
            yelp_model_json.read(),
            type=list[YelpReview],
        )
        cassandra_models = [conversion(yelp_model) for yelp_model in yelp_models]

        for cassandra_model in cassandra_models:
            cassandra_model.save()

    return cassandra_models


def load():
    convert(YELP_JSON_DIR / "review.json")
