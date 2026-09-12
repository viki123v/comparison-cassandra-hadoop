from msgspec import Struct


class Business(Struct):
    business_id: str
    latitude: float
    longitude: float
    review_count: int
