from decimal import Decimal
from pathlib import Path

from cassandra_nosql.load_data.loaders.constants import YELP_JSON_DIR
from cassandra_nosql.load_data.loaders.utils import read_ndjson
from cassandra_nosql.models.cassndra import Business as CassandraBusiness
from cassandra_nosql.models.yelp.business import Business as YelpBusiness


def convert(path: Path) -> list[CassandraBusiness]:
    yelp_models = read_ndjson(path, YelpBusiness)
    cassandra_models = [conversion(yelp_model) for yelp_model in yelp_models]

    for cassandra_model in cassandra_models:
        cassandra_model.save()

    return cassandra_models


def conversion(yelp_model: YelpBusiness) -> CassandraBusiness:
    cassandra_model = CassandraBusiness()
    cassandra_model.id = yelp_model.business_id
    cassandra_model.longitude = Decimal(str(yelp_model.longitude))
    cassandra_model.latitude = Decimal(str(yelp_model.latitude))
    cassandra_model.review_count = int(yelp_model.review_count)
    return cassandra_model


def load():
    convert(YELP_JSON_DIR / "business.json")
