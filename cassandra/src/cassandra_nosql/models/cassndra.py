from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model


KEYSPACE = "nosql"


class User(Model):
    __keyspace__ = KEYSPACE
    __table_name__ = "user"

    id = columns.Text(primary_key=True)
    username = columns.Text()
    compliment_hot = columns.Integer()
    compliment_cut = columns.Integer()
    compliment_cool = columns.Integer()
    compliment_funny = columns.Integer()


class Business(Model):
    __keyspace__ = KEYSPACE
    __table_name__ = "business"

    id = columns.Text(primary_key=True)
    longitude = columns.Decimal()
    latitude = columns.Decimal()
    review_count = columns.Integer()


class ReviewByBusiness(Model):
    __keyspace__ = KEYSPACE
    __table_name__ = "review_by_business"

    business_id = columns.Text(primary_key=True, partition_key=True)
    stars = columns.Integer(primary_key=True, clustering_order="DESC")
    review_id = columns.Text(primary_key=True, clustering_order="ASC")


class ReviewByUser(Model):
    __keyspace__ = KEYSPACE
    __table_name__ = "review_by_user"

    user_id = columns.Text(primary_key=True, partition_key=True)
    stars = columns.Integer(primary_key=True, clustering_order="DESC")
    reviewed_at = columns.Date(primary_key=True, clustering_order="DESC")
    review_id = columns.Text(primary_key=True, clustering_order="ASC")


class TipsByBusiness(Model):
    __keyspace__ = KEYSPACE
    __table_name__ = "tips_by_business"

    business_id = columns.Text(primary_key=True, partition_key=True)
    tipped_at = columns.Date(primary_key=True, clustering_order="DESC")
    tip_id = columns.Integer(primary_key=True, clustering_order="ASC")
    user_id = columns.Text()
    tip_text = columns.Text()


class ChecksByBusiness(Model):
    __keyspace__ = KEYSPACE
    __table_name__ = "checks_by_business"

    business_id = columns.Text(primary_key=True)
    checked_at = columns.Date(primary_key=True)


class UsersByBusiness(Model):
    __keyspace__ = KEYSPACE
    __table_name__ = "users_by_business"

    tip_business_id = columns.Text(primary_key=True, partition_key=True)
    tipped_at = columns.Date(primary_key=True, clustering_order="DESC")
    id = columns.Text(primary_key=True, clustering_order="ASC")
    tip_id = columns.Integer(primary_key=True, clustering_order="ASC")


class UserByPersonalityScore(Model):
    __keyspace__ = KEYSPACE
    __table_name__ = "user_by_personality_score"

    user_id = columns.Text(primary_key=True)
    friends = columns.Integer()
    elite = columns.Integer()
    cool = columns.Integer()
    fans = columns.Integer()
    personality_score = columns.Double()
    global_rank = columns.Integer()


class UserByFriends(Model):
    __keyspace__ = KEYSPACE
    __table_name__ = "user_by_friends"

    user_id = columns.Text(primary_key=True)
    friend_id = columns.Text(primary_key=True)
    friend_name = columns.Text()


class Review(Model):
    __keyspace__ = KEYSPACE
    __table_name__ = "review"

    id = columns.Text(primary_key=True)
    stars = columns.Integer()
    description = columns.Text()
    username = columns.Text()
