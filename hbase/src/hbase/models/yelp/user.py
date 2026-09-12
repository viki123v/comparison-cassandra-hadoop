from msgspec import Struct


class User(Struct):
    user_id: str
    name: str
    cool: int
    elite: str
    friends: str
    fans: int
    compliment_hot: int
    compliment_cute: int
    compliment_cool: int
    compliment_funny: int
