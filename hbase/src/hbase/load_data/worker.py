import importlib
import logging
import time


logger = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(processName)s] %(message)s",
    )


def run_loader(loader_module_name: str, task_name: str) -> tuple[str, int]:
    configure_logging()
    start = time.perf_counter()
    logger.info("Started loading [%s]", task_name)
    try:
        loader = importlib.import_module(
            f"hbase.load_data.loaders.{loader_module_name}"
        )
        loaded = loader.load()
    except Exception:
        logger.exception("Failed loading [%s]", task_name)
        raise

    elapsed = time.perf_counter() - start
    logger.info(
        "Finished loading [%s]: %d mutations in %.2fs",
        task_name,
        loaded,
        elapsed,
    )
    return task_name, loaded
