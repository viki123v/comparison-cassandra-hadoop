# Cassandra Yelp experiment

## Install dependencies

From the repository root:

```powershell
uv sync --package cassandra-nosql
```

## Start and load Cassandra

From the `cassandra` directory:

```powershell
docker compose up -d
uv run --package cassandra-nosql python -m cassandra_nosql.load_data
```

The loader drops and recreates the `nosql` keyspace, so only run it when the
database needs to be reloaded. The experiment intentionally uses the trimmed
Yelp data.

Several tables are denormalized for the benchmark access patterns. Tips are
clustered by date within a business, business reviews by stars, and user
reviews by stars and date. The personality table stores the score and global
rank computed while loading. Each stored tip event has a unique key so repeated
tips from the same user are preserved. Review descriptions are copied from the
Yelp review source.

## Query parameters

`query_parameters.json` contains IDs and coordinates because some use cases
look up a specific business, user, review, or geographical point. Real IDs
verified against the loaded Yelp data make those executions return meaningful
results. Reusing the same parameters will let Cassandra and Hadoop execute
equivalent use cases with comparable inputs. Coordinates and limits are present
only for use cases that need them.

The dataset-relative `reference_date` is `2018-05-05`, the maximum stored tip
date in the trimmed data. It keeps the two-month and one-year windows meaningful
and is intentionally not the current date.

## Run the benchmark

Question IDs `1` through `10` correspond directly to the ordering in
`docs/shared/yelp/queries.md`.

Run one question for diagnosis (this does not replace the ten-row benchmark
CSV):

```powershell
uv run --package cassandra-nosql cassandra-query `
  --query user-name `
  --parameters-file cassandra/query_parameters.json
```

Run all ten questions with warm-up and measured executions:

```powershell
uv run --package cassandra-nosql cassandra-query `
  --all `
  --parameters-file cassandra/query_parameters.json `
  --warmup-runs 2 `
  --runs 10 `
  --output reports/cassandra/query_summary.csv
```

The `cassandra-query` entry point accepts the same arguments. All prepared
statements are created before warm-up starts. Warm-up executions, statement
preparation, failed measured attempts, and diagnostic retries are excluded from
the recorded medians.

The runner writes exactly one report for an all-question benchmark:
`reports/cassandra/query_summary.csv`. It contains only `question_id` and
`median_time_ms`, with one row for each question.

## Remaining processing limitations

- Nearest-business selection scans the business table and calculates distance
  in Python because the schema has no spatial index.
- Cassandra applies the one-year date window for top tippers, but Python counts
  and ranks the returned events because Cassandra cannot aggregate and sort that
  sliding window efficiently without a reference-date-specific pre-aggregate.

These results describe a small local school experiment. They do not establish
production scalability or universal database performance.

## Generated Yelp models

The Yelp input models are generated with `genson` and `datamodel-codegen`, then
decoded with `msgspec`.
