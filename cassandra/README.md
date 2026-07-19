# Creating the models 

## Before queries 
Run `uv run poe bootstrap_cassandra`. This will execute the following
- `uv run poe trim`
    - Trims the data in the `yelp_data` 
- `uv run poe load_data`
    - Executes the `src.cassandra_nosql.load_data` module 

# Description 
The schema is created using `genson`. `Genson` outputs a json schema for a given json document. Then, with the help of `datamodel-codegen` we create the `msgspec` structs. `msgspec` is a lightweight, fast, serialization / deserialization / processing library for json and other file formats. 