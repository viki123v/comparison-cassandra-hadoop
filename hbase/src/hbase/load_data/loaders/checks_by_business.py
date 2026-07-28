from hbase.db import connect_to_hbase
from hbase.load_data.loaders.constants import BATCH_SIZE, YELP_JSON_DIR
from hbase.load_data.loaders.utils import (
    columns,
    limited_relations,
    parse_date,
    read_ndjson,
)
from hbase.models.yelp.checkin import Checkin
from hbase.row_keys import check_by_business_key
from hbase.schema import CHECKS_BY_BUSINESS


def load() -> int:
    connection = connect_to_hbase()
    loaded = 0
    try:
        table = connection.table(CHECKS_BY_BUSINESS)
        with table.batch(batch_size=BATCH_SIZE) as batch:
            for checkin in read_ndjson(
                YELP_JSON_DIR / "checkin.json",
                Checkin,
            ):
                for checked_at_value in limited_relations(checkin.date):
                    checked_at = parse_date(checked_at_value)
                    batch.put(
                        check_by_business_key(
                            checkin.business_id,
                            checked_at,
                        ),
                        columns(
                            business_id=checkin.business_id,
                            checked_at=checked_at.isoformat(),
                        ),
                    )
                    loaded += 1
    finally:
        connection.close()
    return loaded
