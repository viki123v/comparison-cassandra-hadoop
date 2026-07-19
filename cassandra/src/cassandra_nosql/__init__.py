from cassandra.cqlengine import connection
from cassandra.cluster import Cluster

session = Cluster(['127.0.0.1']).connect()

# Used implicitly by cassandra.cqlengine.model.Model.save()
connection.register_connection('default', session=session)