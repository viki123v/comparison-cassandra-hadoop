from cassandra_nosql.load_data import loaders 
from cassandra_nosql import session
from cassandra_nosql.models.cassndra import KEYSPACE
from pathlib import Path 

SCHEMA_SQL_PATH = Path(__file__).parent.parent.parent.parent / "schema.cql"

def clean_database():
    session.execute(f"DROP KEYSPACE IF EXISTS {KEYSPACE}")
    with open(SCHEMA_SQL_PATH, "r") as f:
        schema = f.read()
        session.execute(schema)


def import_data():
    loaders.business.load() 

def run():
    clean_database() 
    import_data()

if __name__ == "__main__":
    run() 
