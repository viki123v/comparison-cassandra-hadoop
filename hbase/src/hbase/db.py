import os

import happybase


HBASE_HOST = os.getenv("HBASE_HOST", "localhost")
HBASE_PORT = int(os.getenv("HBASE_PORT", "9090"))
HBASE_TIMEOUT_MS = int(os.getenv("HBASE_TIMEOUT_MS", "120000"))


def connect_to_hbase() -> happybase.Connection:
    return happybase.Connection(
        host=HBASE_HOST,
        port=HBASE_PORT,
        timeout=HBASE_TIMEOUT_MS,
        autoconnect=True,
    )
