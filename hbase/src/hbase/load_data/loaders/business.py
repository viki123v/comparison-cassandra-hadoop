from hbase.db import connect_to_hbase
from hbase.load_data.loaders.constants import BATCH_SIZE, YELP_JSON_DIR
from hbase.load_data.loaders.utils import columns, read_ndjson
from hbase.models.yelp.business import Business
from hbase.row_keys import business_by_location_key
from hbase.schema import BUSINESS_BY_LOCATION


def load() -> int:
    connection = connect_to_hbase()
    loaded = 0
    try:
        table = connection.table(BUSINESS_BY_LOCATION)
        with table.batch(batch_size=BATCH_SIZE) as batch:
            for business in read_ndjson(
                YELP_JSON_DIR / "business.json",
                Business,
            ):
                batch.put(
                    business_by_location_key(
                        business.business_id,
                        business.latitude,
                        business.longitude,
                        business.review_count,
                    ),
                    columns(
                        business_id=business.business_id,
                        longitude=business.longitude,
                        latitude=business.latitude,
                        review_count=business.review_count,
                    ),
                )
                loaded += 1
    finally:
        connection.close()
    return loaded
