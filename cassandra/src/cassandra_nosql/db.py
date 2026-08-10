import os

from cassandra.cluster import Cluster
from cassandra.cqlengine import connection
from cassandra.policies import DCAwareRoundRobinPolicy
from cassandra.query import dict_factory


def connect_to_cassandra(
    contact_points: list[str] | None = None,
    port: int | None = None,
    keyspace: str | None = None,
):
    """Connect to the local experiment cluster using small environment overrides."""
    configured_hosts = os.getenv("CASSANDRA_HOSTS", "127.0.0.1")
    hosts = contact_points or [
        host.strip() for host in configured_hosts.split(",") if host.strip()
    ]
    configured_port = port or int(os.getenv("CASSANDRA_PORT", "9042"))
    configured_keyspace = keyspace or os.getenv("CASSANDRA_KEYSPACE", "nosql")
    local_dc = os.getenv("CASSANDRA_LOCAL_DC", "datacenter1")

    cluster = Cluster(
        hosts,
        port=configured_port,
        protocol_version=5,
        load_balancing_policy=DCAwareRoundRobinPolicy(local_dc=local_dc),
    )
    try:
        session = cluster.connect(configured_keyspace)
    except Exception as error:
        cluster.shutdown()
        raise ConnectionError(
            "Could not connect to Cassandra at "
            f"{','.join(hosts)}:{configured_port} in keyspace "
            f"{configured_keyspace}"
        ) from error
    session.default_timeout = float(os.getenv("CASSANDRA_REQUEST_TIMEOUT", "30"))
    session.row_factory = dict_factory
    connection.set_session(session)
    return session


def close_cassandra(session) -> None:
    """Close the session and its owning cluster."""
    cluster = session.cluster
    try:
        session.shutdown()
    finally:
        cluster.shutdown()
