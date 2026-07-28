from msgspec import Struct


class Review(Struct):
    review_id: str
    user_id: str
    business_id: str
    stars: float
    date: str
