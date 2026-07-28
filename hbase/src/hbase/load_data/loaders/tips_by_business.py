from hbase.db import connect_to_hbase
from hbase.load_data.loaders.constants import BATCH_SIZE, YELP_JSON_DIR
from hbase.load_data.loaders.utils import columns, parse_date, read_ndjson
from hbase.models.yelp.tip import Tip
from hbase.row_keys import tip_by_business_key
from hbase.schema import TIPS_BY_BUSINESS


def load() -> int:
    connection = connect_to_hbase()
    loaded = 0
    try:
        table = connection.table(TIPS_BY_BUSINESS)
        with table.batch(batch_size=BATCH_SIZE) as batch:
            tips = read_ndjson(YELP_JSON_DIR / "tip.json", Tip)
            for tip_id, tip in enumerate(tips):
                tipped_at = parse_date(tip.date)
                batch.put(
                    tip_by_business_key(
                        tip.business_id,
                        tipped_at,
                        tip_id,
                    ),
                    columns(
                        business_id=tip.business_id,
                        tip_id=tip_id,
                        tipped_at=tipped_at.isoformat(),
                        user_id=tip.user_id,
                    ),
                )
                loaded += 1
    finally:
        connection.close()
    return loaded
