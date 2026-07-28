# Cassandra Yelp experiment

## Install dependencies

From the `cassandra` directory:

```bash
uv sync
```

## Start and load Cassandra

From the `cassandra` directory:

```powershell
docker compose up -d
uv run python -m cassandra_nosql.load_data
```

The loader drops and recreates the `nosql` keyspace, so only run it when the
database needs to be reloaded. The experiment intentionally uses the trimmed
Yelp data.

## Query parameters

`query_parameters.json` contains IDs and coordinates verified against the
currently loaded trimmed Yelp data. The selected business exists in
`business`, `tips_by_business`, `users_by_business`, and
`review_by_business`. The selected user exists in `user`, `review_by_user`,
`user_by_friends`, and `user_by_personality_score`.

The fixed dataset-relative `reference_date` is `2018-05-05`, the maximum
stored tip date in both tip-related tables. This keeps the 60-day tip window
meaningful while also returning reviews in the preceding 365 days. It is
intentionally not the current date.

## Run queries

Run one query:

```powershell
uv run python -m cassandra_nosql.run_queries `
  --query user-name `
  --parameters-file query_parameters.json
```

Run all ten shared use cases once:

```powershell
uv run python -m cassandra_nosql.run_queries `
  --all `
  --parameters-file query_parameters.json
```

Run the simple warm benchmark and create CSV reports:

```powershell
uv run python -m cassandra_nosql.run_queries `
  --all `
  --parameters-file query_parameters.json `
  --warmup-runs 2 `
  --runs 10 `
  --output ../reports/cassandra/query_results.csv
```

The `cassandra-query` package entry point accepts the same arguments:

```powershell
uv run cassandra-query --query user-name `
  --parameters-file query_parameters.json
```

The runner writes one row per measured execution to `query_results.csv` and a
small aggregate report to `query_summary.csv`. Warm-up runs are not written.
Each measured row separates Cassandra fetch time, Python processing time, and
total time. Cassandra results are fully consumed before the database timer
stops so automatic result paging is included.

For `--all`, a failed query is recorded and later queries continue. The command
returns a nonzero exit status if any query failed. A missing database row is a
successful empty result.

## Experiment limitations

- Relevant-business and personality-ranking queries scan their stored tables.
- Recent tip filtering is done in Python and only stored tip fields are
  available.
- Repeated tips for one user/business may have overwritten each other.
- Review text is not stored in the Cassandra review table.
- Recent user reviews are filtered and sorted in Python.
- Only friend rows preserved by the loader are available, and some names may
  be blank because the Yelp files were trimmed independently.

These results describe a small local school experiment. They do not establish
production scalability or universal database performance.

## Generated Yelp models

The Yelp input models are generated with `genson` and
`datamodel-codegen`, then decoded with `msgspec`.
