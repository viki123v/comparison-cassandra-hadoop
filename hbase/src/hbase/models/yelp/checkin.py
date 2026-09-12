from msgspec import Struct


class Checkin(Struct):
    business_id: str
    date: str
