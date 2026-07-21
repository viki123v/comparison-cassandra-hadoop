from pathlib import Path

from cassandra_nosql.load_data.loaders.constants import YELP_JSON_DIR
from cassandra_nosql.load_data.loaders.utils import handle_composite_object, read_ndjson
from cassandra_nosql.models.cassndra import UserByFriends as CassandraUserByFriends
from cassandra_nosql.models.yelp.user import User as YelpUser


def friend_ids(value: str) -> list[str]:
    if not value or value == "None":
        return []

    return handle_composite_object(value)


def conversion(
    yelp_model: YelpUser,
    friend_id: str,
    users_by_id: dict[str, YelpUser],
) -> CassandraUserByFriends:
    friend = users_by_id.get(friend_id)
    cassandra_model = CassandraUserByFriends()
    cassandra_model.user_id = yelp_model.user_id
    cassandra_model.friend_id = friend_id
    cassandra_model.friend_name = friend.name if friend else ""
    return cassandra_model


def convert(path: Path) -> list[CassandraUserByFriends]:
    yelp_models = read_ndjson(path, YelpUser)
    users_by_id = {yelp_model.user_id: yelp_model for yelp_model in yelp_models}
    cassandra_models = [
        conversion(yelp_model, friend_id, users_by_id)
        for yelp_model in yelp_models
        for friend_id in friend_ids(yelp_model.friends)
    ]

    for cassandra_model in cassandra_models:
        cassandra_model.save()

    return cassandra_models


def load():
    convert(YELP_JSON_DIR / "user.json")
