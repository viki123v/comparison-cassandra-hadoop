CREATE KEYSPACE IF NOT EXISTS nosql
WITH REPLICATION = {
  'class': 'SimpleStrategy',
  'replication_factor': 1
};