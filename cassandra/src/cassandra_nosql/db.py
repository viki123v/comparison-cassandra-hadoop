from cassandra.cluster import Cluster
from cassandra.cqlengine import connection
from cassandra.policies import DCAwareRoundRobinPolicy
from cassandra.query import dict_factory


def connect_to_cassandra():
    session = Cluster(
        ["127.0.0.1"],
        protocol_version=5,
        load_balancing_policy=DCAwareRoundRobinPolicy(local_dc="datacenter1"),
    ).connect()
    session.row_factory = dict_factory
    connection.set_session(session)
    return session
