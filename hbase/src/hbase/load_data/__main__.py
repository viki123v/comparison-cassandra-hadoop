import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

from hbase.db import connect_to_hbase
from hbase.load_data.loaders.constants import YELP_JSON_DIR
from hbase.load_data.worker import configure_logging, run_loader
from hbase.schema import recreate_tables


logger = logging.getLogger(__name__)

INPUT_FILES = (
    "business.json",
    "checkin.json",
    "review.json",
    "tip.json",
    "user.json",
)

LOADING_TASKS = (
    ("business", "Business"),
    ("checks_by_business", "Checks by Business"),
    ("review", "Reviews"),
    ("tips_by_business", "Tips by Business"),
    ("user", "Users"),
)


def validate_inputs() -> None:
    missing = [
        str(YELP_JSON_DIR / filename)
        for filename in INPUT_FILES
        if not (YELP_JSON_DIR / filename).is_file()
    ]
    if missing:
        missing_list = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            f"Missing prepared Yelp input files:\n{missing_list}\n"
            "Run the shared trim task before loading HBase."
        )


def clean_database() -> None:
    logger.info("Recreating HBase schema")
    connection = connect_to_hbase()
    try:
        recreate_tables(connection)
    finally:
        connection.close()
    logger.info("HBase schema recreated")


def import_data() -> None:
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(run_loader, module_name, task_name): task_name
            for module_name, task_name in LOADING_TASKS
        }
        for future in as_completed(futures):
            task_name, mutation_count = future.result()
            logger.info(
                "Loader [%s] completed with %d mutations",
                task_name,
                mutation_count,
            )


def run() -> None:
    configure_logging()
    validate_inputs()
    clean_database()
    import_data()


if __name__ == "__main__":
    run()
