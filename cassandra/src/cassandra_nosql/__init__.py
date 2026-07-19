from cassandra.cqlengine import connection
from cassandra.cluster import Cluster
from cassandra.query import dict_factory

session = Cluster(['127.0.0.1']).connect()
session.row_factory = dict_factory

# Used implicitly by cassandra.cqlengine.model.Model.save()
connection.set_session(session)
