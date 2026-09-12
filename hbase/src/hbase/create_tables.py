from hbase.db import connect_to_hbase
from hbase.schema import recreate_tables


def create_tables() -> None:
    connection = connect_to_hbase()
    try:
        recreate_tables(connection)
    finally:
        connection.close()


if __name__ == "__main__":
    create_tables()
