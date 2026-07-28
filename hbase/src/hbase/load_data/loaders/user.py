from contextlib import ExitStack

from hbase.db import connect_to_hbase
from hbase.load_data.loaders.constants import BATCH_SIZE, YELP_JSON_DIR
from hbase.load_data.loaders.utils import (
    columns,
    count_composite,
    limited_relations,
    read_ndjson,
)
from hbase.models.yelp.user import User
from hbase.row_keys import friend_by_user_key, personality_ranking_key
from hbase.schema import FRIENDS_BY_USER, PERSONALITY_RANKING, USER


def load() -> int:
    path = YELP_JSON_DIR / "user.json"
    users_by_id = {user.user_id: user.name for user in read_ndjson(path, User)}

    connection = connect_to_hbase()
    loaded = 0
    try:
        with ExitStack() as stack:
            user_batch = stack.enter_context(
                connection.table(USER).batch(batch_size=BATCH_SIZE)
            )
            personality_batch = stack.enter_context(
                connection.table(PERSONALITY_RANKING).batch(batch_size=BATCH_SIZE)
            )
            friends_batch = stack.enter_context(
                connection.table(FRIENDS_BY_USER).batch(batch_size=BATCH_SIZE)
            )

            for user in read_ndjson(path, User):
                friend_count = count_composite(user.friends)
                elite_count = count_composite(user.elite)
                score_sum = friend_count + elite_count + user.cool + user.fans

                user_batch.put(
                    user.user_id.encode("utf-8"),
                    columns(
                        user_id=user.user_id,
                        username=user.name,
                        compliment_hot=user.compliment_hot,
                        compliment_cut=user.compliment_cute,
                        compliment_cool=user.compliment_cool,
                        compliment_funny=user.compliment_funny,
                    ),
                )
                personality_batch.put(
                    personality_ranking_key(score_sum, user.user_id),
                    columns(
                        user_id=user.user_id,
                        friends=friend_count,
                        elite=elite_count,
                        cool=user.cool,
                        fans=user.fans,
                    ),
                )
                loaded += 2

                for friend_id in limited_relations(user.friends):
                    friends_batch.put(
                        friend_by_user_key(user.user_id, friend_id),
                        columns(
                            user_id=user.user_id,
                            friend_id=friend_id,
                            friend_name=users_by_id.get(friend_id, ""),
                        ),
                    )
                    loaded += 1
    finally:
        connection.close()
    return loaded
