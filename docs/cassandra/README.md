# Cassandra documentation

This directory will contain Cassandra-specific documentation for the Yelp comparison, including:

- logical data modeling based on the shared use cases
- query-specific Cassandra tables
- partition-key and clustering-key decisions
- denormalization decisions
- physical CQL schema
- Cassandra-specific query implementation notes

Shared Yelp documentation:

- [Conceptual model](../shared/yelp/conceptual.md)
- [Shared use cases and queries](../shared/yelp/queries.md)
- [Dataset columns](../shared/yelp/columns/)

Cassandra should implement the shared logical use cases, but its physical schema can be designed specifically for Cassandra.
