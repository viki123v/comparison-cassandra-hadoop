from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from time import perf_counter
from typing import Any, Callable

from cassandra import ConsistencyLevel
from cassandra.query import SimpleStatement


TWO_MONTH_WINDOW_DAYS = 60
ONE_YEAR_WINDOW_DAYS = 365
EARTH_RADIUS_KM = 6_371.0088

USE_CASE_NOTES = {
    "relevant-business": (
        "The business table is scanned and distance is calculated in Python."
    ),
    "recent-business-tips": (
        "Date filtering is performed in Python after reading the business "
        "partition. Only fields stored by Cassandra are returned."
    ),
    "top-business-tippers": (
        "Repeated tips from one user to one business may have overwritten each "
        "other during loading. Ranking uses the rows stored in Cassandra."
    ),
    "user-name": "",
    "highest-star-business-review": (
        "Stars are sorted in Python; review ID is the deterministic tie-breaker."
    ),
    "review-details": (
        "Review text is unavailable because it is not stored in the current "
        "Cassandra review table."
    ),
    "user-perception": (
        "The physical compliment_cut column is exposed as compliment_cute."
    ),
    "personality-ranking": (
        "The stored user rows are scanned, scored, sorted, and ranked in Python."
    ),
    "recent-user-reviews": (
        "Date filtering and star ranking are performed in Python after reading "
        "the user partition."
    ),
    "user-friends": (
        "Only friend rows preserved by the loader are available; names may be "
        "blank because the dataset files were trimmed independently."
    ),
}


@dataclass(frozen=True)
class QueryResult:
    rows: list[dict[str, Any]]
    database_time_ms: float
    processing_time_ms: float
    total_time_ms: float
    notes: str = ""

    @property
    def row_count(self) -> int:
        return len(self.rows)


@dataclass(frozen=True)
class PreparedQueries:
    recent_business_tips: Any
    top_business_tippers: Any
    user_name: Any
    highest_star_business_review: Any
    review_details: Any
    user_perception: Any
    recent_user_reviews: Any
    user_friends: Any


BUSINESS_SCAN = SimpleStatement(
    """
    SELECT id, longitude, latitude, review_count
    FROM nosql.business
    """,
    consistency_level=ConsistencyLevel.LOCAL_ONE,
    fetch_size=1_000,
)

PERSONALITY_SCAN = SimpleStatement(
    """
    SELECT user_id, friends, elite, cool, fans
    FROM nosql.user_by_personality_score
    """,
    consistency_level=ConsistencyLevel.LOCAL_ONE,
    fetch_size=1_000,
)


def prepare_query_statements(session) -> PreparedQueries:
    """Prepare all parameterized statements once, outside measured query runs."""

    def prepare(cql: str):
        statement = session.prepare(cql)
        statement.consistency_level = ConsistencyLevel.LOCAL_ONE
        return statement

    return PreparedQueries(
        recent_business_tips=prepare(
            """
            SELECT business_id, tip_id, tipped_at
            FROM nosql.tips_by_business
            WHERE business_id = ?
            """
        ),
        top_business_tippers=prepare(
            """
            SELECT id, tip_business_id, tipped_at
            FROM nosql.users_by_business
            WHERE tip_business_id = ?
            """
        ),
        user_name=prepare(
            """
            SELECT id, username
            FROM nosql.user
            WHERE id = ?
            """
        ),
        highest_star_business_review=prepare(
            """
            SELECT business_id, review_id, stars
            FROM nosql.review_by_business
            WHERE business_id = ?
            """
        ),
        review_details=prepare(
            """
            SELECT id, stars, username
            FROM nosql.review
            WHERE id = ?
            """
        ),
        user_perception=prepare(
            """
            SELECT id, username, compliment_hot, compliment_cut,
                   compliment_cool, compliment_funny
            FROM nosql.user
            WHERE id = ?
            """
        ),
        recent_user_reviews=prepare(
            """
            SELECT user_id, review_id, reviewed_at, stars
            FROM nosql.review_by_user
            WHERE user_id = ?
            """
        ),
        user_friends=prepare(
            """
            SELECT user_id, friend_id, friend_name
            FROM nosql.user_by_friends
            WHERE user_id = ?
            """
        ),
    )


def haversine_distance_km(
    longitude_a: float,
    latitude_a: float,
    longitude_b: float,
    latitude_b: float,
) -> float:
    """Return the great-circle distance between two coordinates in kilometres."""
    longitude_delta = radians(longitude_b - longitude_a)
    latitude_delta = radians(latitude_b - latitude_a)
    latitude_a_radians = radians(latitude_a)
    latitude_b_radians = radians(latitude_b)

    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(latitude_a_radians)
        * cos(latitude_b_radians)
        * sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * asin(sqrt(haversine))


def find_relevant_business(
    session,
    longitude: float,
    latitude: float,
    limit: int = 1,
) -> QueryResult:
    _validate_coordinates(longitude, latitude)
    _validate_limit(limit)

    def process(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        businesses = []
        for row in rows:
            business_longitude = float(row["longitude"])
            business_latitude = float(row["latitude"])
            businesses.append(
                {
                    "business_id": row["id"],
                    "longitude": business_longitude,
                    "latitude": business_latitude,
                    "review_count": int(row.get("review_count") or 0),
                    "distance_km": haversine_distance_km(
                        longitude,
                        latitude,
                        business_longitude,
                        business_latitude,
                    ),
                }
            )

        businesses.sort(
            key=lambda business: (
                business["distance_km"],
                -business["review_count"],
                business["business_id"],
            )
        )
        return businesses[:limit]

    return _execute_and_process(
        session,
        BUSINESS_SCAN,
        None,
        process,
        USE_CASE_NOTES["relevant-business"],
    )


def get_recent_business_tips(
    session,
    statements: PreparedQueries,
    business_id: str,
    reference_date: date,
    limit: int = 10,
) -> QueryResult:
    _validate_identifier("business_id", business_id)
    _validate_limit(limit)
    window_start = reference_date - timedelta(days=TWO_MONTH_WINDOW_DAYS)

    def process(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        recent_tips = []
        for row in rows:
            tipped_at = _as_date(row["tipped_at"])
            if window_start <= tipped_at <= reference_date:
                recent_tips.append(
                    {
                        "business_id": row["business_id"],
                        "tip_id": int(row["tip_id"]),
                        "tipped_at": tipped_at.isoformat(),
                    }
                )
        recent_tips.sort(
            key=lambda tip: (tip["tipped_at"], tip["tip_id"]),
            reverse=True,
        )
        return recent_tips[:limit]

    return _execute_and_process(
        session,
        statements.recent_business_tips,
        (business_id,),
        process,
        USE_CASE_NOTES["recent-business-tips"],
    )


def get_top_business_tippers(
    session,
    statements: PreparedQueries,
    business_id: str,
    reference_date: date,
    limit: int = 10,
) -> QueryResult:
    _validate_identifier("business_id", business_id)
    _validate_limit(limit)
    window_start = reference_date - timedelta(days=ONE_YEAR_WINDOW_DAYS)

    def process(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        counts: Counter[str] = Counter()
        for row in rows:
            tipped_at = _as_date(row["tipped_at"])
            if window_start <= tipped_at <= reference_date:
                counts[str(row["id"])] += 1

        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [
            {"rank": rank, "user_id": user_id, "stored_tip_count": tip_count}
            for rank, (user_id, tip_count) in enumerate(ranked[:limit], start=1)
        ]

    return _execute_and_process(
        session,
        statements.top_business_tippers,
        (business_id,),
        process,
        USE_CASE_NOTES["top-business-tippers"],
    )


def get_user_name(
    session,
    statements: PreparedQueries,
    user_id: str,
) -> QueryResult:
    _validate_identifier("user_id", user_id)
    return _execute_and_process(
        session,
        statements.user_name,
        (user_id,),
        lambda rows: [
            {"user_id": row["id"], "username": row.get("username") or ""}
            for row in rows
        ],
        USE_CASE_NOTES["user-name"],
    )


def get_highest_star_business_review(
    session,
    statements: PreparedQueries,
    business_id: str,
) -> QueryResult:
    _validate_identifier("business_id", business_id)

    def process(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        reviews = [
            {
                "business_id": row["business_id"],
                "review_id": row["review_id"],
                "stars": int(row.get("stars") or 0),
            }
            for row in rows
        ]
        reviews.sort(key=lambda review: (-review["stars"], review["review_id"]))
        return reviews[:1]

    return _execute_and_process(
        session,
        statements.highest_star_business_review,
        (business_id,),
        process,
        USE_CASE_NOTES["highest-star-business-review"],
    )


def get_review_details(
    session,
    statements: PreparedQueries,
    review_id: str,
) -> QueryResult:
    _validate_identifier("review_id", review_id)
    return _execute_and_process(
        session,
        statements.review_details,
        (review_id,),
        lambda rows: [
            {
                "review_id": row["id"],
                "stars": int(row.get("stars") or 0),
                "username": row.get("username") or "",
            }
            for row in rows
        ],
        USE_CASE_NOTES["review-details"],
    )


def get_user_perception(
    session,
    statements: PreparedQueries,
    user_id: str,
) -> QueryResult:
    _validate_identifier("user_id", user_id)
    return _execute_and_process(
        session,
        statements.user_perception,
        (user_id,),
        lambda rows: [
            {
                "user_id": row["id"],
                "username": row.get("username") or "",
                "compliment_hot": int(row.get("compliment_hot") or 0),
                "compliment_cute": int(row.get("compliment_cut") or 0),
                "compliment_cool": int(row.get("compliment_cool") or 0),
                "compliment_funny": int(row.get("compliment_funny") or 0),
            }
            for row in rows
        ],
        USE_CASE_NOTES["user-perception"],
    )


def get_personality_ranking(
    session,
    user_id: str | None = None,
    limit: int = 10,
) -> QueryResult:
    if user_id is not None:
        _validate_identifier("user_id", user_id)
    _validate_limit(limit)

    def process(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        scored_users = []
        for row in rows:
            friends = int(row.get("friends") or 0)
            cool = int(row.get("cool") or 0)
            elite = int(row.get("elite") or 0)
            fans = int(row.get("fans") or 0)
            scored_users.append(
                {
                    "user_id": row["user_id"],
                    "friends": friends,
                    "cool": cool,
                    "elite": elite,
                    "fans": fans,
                    "personality_score": (friends + cool + elite + fans) / 4,
                }
            )

        scored_users.sort(
            key=lambda user: (-user["personality_score"], user["user_id"])
        )
        ranked_users = [
            {"rank": rank, **user} for rank, user in enumerate(scored_users, start=1)
        ]
        if user_id is not None:
            return [user for user in ranked_users if user["user_id"] == user_id]
        return ranked_users[:limit]

    return _execute_and_process(
        session,
        PERSONALITY_SCAN,
        None,
        process,
        USE_CASE_NOTES["personality-ranking"],
    )


def get_recent_user_reviews(
    session,
    statements: PreparedQueries,
    user_id: str,
    reference_date: date,
    limit: int = 10,
) -> QueryResult:
    _validate_identifier("user_id", user_id)
    _validate_limit(limit)
    window_start = reference_date - timedelta(days=ONE_YEAR_WINDOW_DAYS)

    def process(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        reviews = []
        for row in rows:
            reviewed_at = _as_date(row["reviewed_at"])
            if window_start <= reviewed_at <= reference_date:
                reviews.append(
                    {
                        "user_id": row["user_id"],
                        "review_id": row["review_id"],
                        "reviewed_at": reviewed_at.isoformat(),
                        "stars": int(row.get("stars") or 0),
                    }
                )
        reviews.sort(
            key=lambda review: (
                -review["stars"],
                -date.fromisoformat(review["reviewed_at"]).toordinal(),
                review["review_id"],
            )
        )
        return reviews[:limit]

    return _execute_and_process(
        session,
        statements.recent_user_reviews,
        (user_id,),
        process,
        USE_CASE_NOTES["recent-user-reviews"],
    )


def get_user_friends(
    session,
    statements: PreparedQueries,
    user_id: str,
    limit: int | None = None,
) -> QueryResult:
    _validate_identifier("user_id", user_id)
    if limit is not None:
        _validate_limit(limit)

    def process(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        friends = [
            {
                "user_id": row["user_id"],
                "friend_id": row["friend_id"],
                "friend_name": row.get("friend_name") or "",
                "name_missing": not bool(row.get("friend_name")),
            }
            for row in rows
        ]
        friends.sort(key=lambda friend: friend["friend_id"])
        return friends if limit is None else friends[:limit]

    result = _execute_and_process(
        session,
        statements.user_friends,
        (user_id,),
        process,
        USE_CASE_NOTES["user-friends"],
    )
    missing_names = sum(friend["name_missing"] for friend in result.rows)
    return replace(
        result,
        notes=f"{result.notes} Missing names in returned rows: {missing_names}.",
    )


def _execute_and_process(
    session,
    statement,
    parameters: tuple[Any, ...] | None,
    processor: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
    notes: str,
) -> QueryResult:
    total_start = perf_counter()
    database_start = perf_counter()
    if parameters is None:
        result_set = session.execute(statement)
    else:
        result_set = session.execute(statement, parameters)
    raw_rows = list(result_set)
    database_end = perf_counter()

    processed_rows = processor(raw_rows)
    total_end = perf_counter()
    return QueryResult(
        rows=processed_rows,
        database_time_ms=(database_end - database_start) * 1_000,
        processing_time_ms=(total_end - database_end) * 1_000,
        total_time_ms=(total_end - total_start) * 1_000,
        notes=notes,
    )


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _validate_identifier(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    if value.startswith("REPLACE_WITH_"):
        raise ValueError(f"{name} is still a placeholder in the parameter file")


def _validate_limit(limit: int) -> None:
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        raise ValueError("limit must be a positive integer")


def _validate_coordinates(longitude: float, latitude: float) -> None:
    if not isinstance(longitude, (int, float)) or isinstance(longitude, bool):
        raise ValueError("longitude must be a number")
    if not isinstance(latitude, (int, float)) or isinstance(latitude, bool):
        raise ValueError("latitude must be a number")
    if not -180 <= longitude <= 180:
        raise ValueError("longitude must be between -180 and 180")
    if not -90 <= latitude <= 90:
        raise ValueError("latitude must be between -90 and 90")
