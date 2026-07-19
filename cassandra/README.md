# Creating the models 

## Before queries 
Run `uv run poe bootstrap_cassandra`. This will execute the following
- `uv run poe trim`
    - Trims the data in the `yelp_data` 
- `uv run poe load_data`
    - Executes the `src.cassandra_nosql.load_data` module 