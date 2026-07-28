import os

from gevent import monkey

# cassandra-driver's default asyncore reactor is unavailable on Python 3.13.
# Patching before importing the driver lets it select its bundled gevent reactor.
monkey.patch_all()

from cassandra.cluster import Cluster  # noqa: E402
from cassandra.cqlengine import connection  # noqa: E402
from cassandra.policies import DCAwareRoundRobinPolicy  # noqa: E402
from cassandra.query import dict_factory  # noqa: E402


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
    session = cluster.connect(configured_keyspace)
    session.default_timeout = float(os.getenv("CASSANDRA_REQUEST_TIMEOUT", "30"))
    session.row_factory = dict_factory
    connection.set_session(session)
    return session


def close_cassandra(session) -> None:
    """Close the session and its owning cluster."""
    cluster = session.cluster
    session.shutdown()
    cluster.shutdown()
