from cassandra_nosql.load_data import loaders 
from cassandra_nosql import session
from cassandra_nosql.models.cassndra import KEYSPACE
from pathlib import Path 

KEYSPACE_CQL_PATH= Path(__file__).parent.parent.parent.parent / "cql" / "keyspace.cql"
SCHEMA_CQL_PATH = Path(__file__).parent.parent.parent.parent / "cql" / "schema.cql"

# The session.execute executes ONLY a single statement 
def execute_cql_file(path: Path):
    with open(path, "r") as f:
        statements = f.read().split(";")

    for statement in statements:
        statement = statement.strip()
        if statement:
            session.execute(statement)


def clean_database():
    session.execute(f"DROP KEYSPACE IF EXISTS {KEYSPACE}")

    execute_cql_file(KEYSPACE_CQL_PATH)
    execute_cql_file(SCHEMA_CQL_PATH)


def import_data():
    loaders.business.load() 

def run():
    clean_database() 
    import_data()

if __name__ == "__main__":
    run() 
