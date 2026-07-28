from msgspec import Struct


class Tip(Struct):
    user_id: str
    business_id: str
    date: str
