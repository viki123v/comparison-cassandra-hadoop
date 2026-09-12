import logging

from happybase import Connection


logger = logging.getLogger(__name__)

DATA_FAMILY = "d"

BUSINESS_BY_LOCATION = "business_by_location"
TIPS_BY_BUSINESS = "tips_by_business"
USER = "user"
REVIEW_BY_BUSINESS = "review_by_business"
REVIEW = "review"
PERSONALITY_RANKING = "personality_ranking"
REVIEW_BY_USER = "review_by_user"
FRIENDS_BY_USER = "friends_by_user"
CHECKS_BY_BUSINESS = "checks_by_business"

TABLES = (
    BUSINESS_BY_LOCATION,
    TIPS_BY_BUSINESS,
    USER,
    REVIEW_BY_BUSINESS,
    REVIEW,
    PERSONALITY_RANKING,
    REVIEW_BY_USER,
    FRIENDS_BY_USER,
    CHECKS_BY_BUSINESS,
)

# These tables came from the original entity-oriented HBase prototype. They are
# removed during a clean bootstrap so stale data cannot be confused with the
# query-oriented schema.
LEGACY_TABLES = ("business", "checkin", "tip")


def recreate_tables(connection: Connection) -> None:
    existing = {name.decode("utf-8") for name in connection.tables()}

    for table_name in (*TABLES, *LEGACY_TABLES):
        if table_name not in existing:
            continue
        logger.info("Dropping HBase table [%s]", table_name)
        connection.delete_table(table_name, disable=True)

    family_options = {DATA_FAMILY: {"max_versions": 1}}
    for table_name in TABLES:
        logger.info("Creating HBase table [%s]", table_name)
        connection.create_table(table_name, family_options)
