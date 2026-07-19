import logging
from multiprocessing import Process, Semaphore

from cassandra_nosql.db import connect_to_cassandra
from cassandra_nosql.load_data.worker import configure_logging, run_loader
from cassandra_nosql.models.cassndra import KEYSPACE
from pathlib import Path

KEYSPACE_CQL_PATH = Path(__file__).parent.parent.parent.parent / "cql" / "keyspace.cql"
SCHEMA_CQL_PATH = Path(__file__).parent.parent.parent.parent / "cql" / "schema.cql"
logger = logging.getLogger(__name__)
session = connect_to_cassandra()


# The session.execute executes ONLY a single statement
def execute_cql_file(path: Path):
    with open(path, "r") as f:
        statements = f.read().split(";")

    for statement in statements:
        statement = statement.strip()
        if statement:
            session.execute(statement)


def clean_database():
    logger.info("Cleaning Cassandra keyspace %s", KEYSPACE)
    session.execute(f"DROP KEYSPACE IF EXISTS {KEYSPACE}")

    execute_cql_file(KEYSPACE_CQL_PATH)
    execute_cql_file(SCHEMA_CQL_PATH)
    logger.info("Cassandra schema recreated")


def import_data():
    semaphore = Semaphore(3)

    loading_tasks = [
        # Cannot use modules, not pickle friendly 
        ("business", "Business"),
        ("checks_by_business", "Checks by Business"),
        ("review_by_business", "Review by Business"),
        ("review_by_user", "Review by User"),
        ("review", "Review"),
        ("tips_by_business", "Tips by Business"),
        ("user_by_friends", "User by Friends"),
        ("user_by_personality_score", "User by Personality Score"),
        ("user", "User"),
        ("users_by_business", "Users by Business"),
    ]

    processes: list[tuple[str, Process]] = []
    for loader_module_name, task_name in loading_tasks:
        semaphore.acquire()
        process = Process(
            target=run_loader,
            args=(loader_module_name, task_name, semaphore),
            name=f"loader-{task_name.lower().replace(' ', '-')}",
        )
        process.start()
        processes.append((task_name, process))

    # If processes=[p1] then main process won't wait for the semaphore 
    # This assures that the main process doesn't exit until all children are done
    for task_name, process in processes:
        process.join()
        if process.exitcode:
            logger.error("Loader %s exited with code %s", task_name, process.exitcode)

def run():
    configure_logging()
    clean_database()
    import_data()


if __name__ == "__main__":
    run()
