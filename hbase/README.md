# HBase Yelp experiment

The HBase implementation uses HappyBase over Thrift and query-oriented tables
whose row keys support the ten access patterns in
`docs/shared/yelp/queries.md`.

## Bootstrap

Start HBase, then recreate the tables and load the trimmed Yelp data:

```bash
docker compose -f hbase/docker-compose.yml up -d
uv run --package hbase poe -C hbase bootstrap_hbase
```

Bootstrapping drops the experiment tables before loading them. Reload after
changing loader columns or row-key formats.

## Run queries

Run one query for diagnosis without writing the benchmark report:

```bash
uv run --package hbase hbase-query \
  --query user-name \
  --parameters-file hbase/query_parameters.json
```

Run all ten queries and write their median execution times:

```bash
uv run --package hbase hbase-query \
  --all \
  --parameters-file hbase/query_parameters.json \
  --warmup-runs 2 \
  --runs 10 \
  --output reports/hbase/query_summary.csv
```

The report contains exactly `question_id` and `median_time_ms`. Connection
setup, warm-ups, failed attempts, and diagnostic retries are not timed.
