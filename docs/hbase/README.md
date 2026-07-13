# HBase documentation

This directory will contain HBase-specific documentation for the Yelp comparison, including:

- logical data modeling based on the shared use cases
- row-key design
- column-family design
- access patterns and scans
- denormalization decisions
- HBase table definitions
- HBase-specific query implementation notes

Shared Yelp documentation:

- [Conceptual model](../shared/yelp/conceptual.md)
- [Shared use cases and queries](../shared/yelp/queries.md)
- [Dataset columns](../shared/yelp/columns/)

HBase should implement the same shared logical use cases and expected outputs, but its physical design does not need to match Cassandra.
