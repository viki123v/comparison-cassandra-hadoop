from contextlib import ExitStack

from hbase.db import connect_to_hbase
from hbase.load_data.loaders.constants import BATCH_SIZE, YELP_JSON_DIR
from hbase.load_data.loaders.utils import columns, parse_date, read_ndjson
from hbase.models.yelp.review import Review
from hbase.models.yelp.user import User
from hbase.row_keys import review_by_business_key, review_by_user_key
from hbase.schema import REVIEW, REVIEW_BY_BUSINESS, REVIEW_BY_USER


def load() -> int:
    users_by_id = {
        user.user_id: user.name
        for user in read_ndjson(YELP_JSON_DIR / "user.json", User)
    }

    connection = connect_to_hbase()
    loaded = 0
    try:
        with ExitStack() as stack:
            review_batch = stack.enter_context(
                connection.table(REVIEW).batch(batch_size=BATCH_SIZE)
            )
            business_batch = stack.enter_context(
                connection.table(REVIEW_BY_BUSINESS).batch(batch_size=BATCH_SIZE)
            )
            user_batch = stack.enter_context(
                connection.table(REVIEW_BY_USER).batch(batch_size=BATCH_SIZE)
            )

            for review in read_ndjson(
                YELP_JSON_DIR / "review.json",
                Review,
            ):
                stars = int(review.stars)
                reviewed_at = parse_date(review.date)

                review_batch.put(
                    review.review_id.encode("utf-8"),
                    columns(
                        review_id=review.review_id,
                        stars=stars,
                        username=users_by_id.get(review.user_id, ""),
                    ),
                )
                business_batch.put(
                    review_by_business_key(
                        review.business_id,
                        stars,
                        review.review_id,
                    ),
                    columns(
                        business_id=review.business_id,
                        review_id=review.review_id,
                        stars=stars,
                    ),
                )
                user_batch.put(
                    review_by_user_key(
                        review.user_id,
                        reviewed_at,
                        stars,
                        review.review_id,
                    ),
                    columns(
                        user_id=review.user_id,
                        review_id=review.review_id,
                        reviewed_at=reviewed_at.isoformat(),
                        stars=stars,
                    ),
                )
                loaded += 3
    finally:
        connection.close()
    return loaded
