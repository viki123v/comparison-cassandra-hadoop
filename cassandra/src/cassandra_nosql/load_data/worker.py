import importlib
import logging
import time

from cassandra_nosql.db import connect_to_cassandra

logger = logging.getLogger(__name__)


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(processName)s] %(message)s",
    )


def run_loader(loader_module_name: str, task_name: str, semaphore):
    configure_logging()
    start = time.perf_counter()

    try:
        connect_to_cassandra()
        logger.info("Started loading [%s]", task_name)
        loader = importlib.import_module(
            f"cassandra_nosql.load_data.loaders.{loader_module_name}"
        )
        loader.load()
    except Exception:
        logger.exception("Failed loading [%s]", task_name)
        raise
    finally:
        elapsed = time.perf_counter() - start
        logger.info("Finished loading [%s] in %.2fs", task_name, elapsed)
        semaphore.release()
