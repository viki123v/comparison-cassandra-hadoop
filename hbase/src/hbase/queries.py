from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from math import asin, cos, radians, sin, sqrt
from typing import Any, Callable

from happybase import Connection

from hbase.row_keys import ROW_KEY_SEPARATOR, reverse_date
from hbase.schema import (
    BUSINESS_BY_LOCATION,
    FRIENDS_BY_USER,
    PERSONALITY_RANKING,
    REVIEW,
    REVIEW_BY_BUSINESS,
    REVIEW_BY_USER,
    TIPS_BY_BUSINESS,
    USER,
)


TWO_MONTH_WINDOW_DAYS = 60
ONE_YEAR_WINDOW_DAYS = 365
EARTH_RADIUS_KM = 6_371.0088
DATA_PREFIX = b"d:"

QUESTION_SLUGS = {
    1: "relevant-business",
    2: "recent-business-tips",
    3: "top-business-tippers",
    4: "user-name",
    5: "highest-star-business-review",
    6: "review-details",
    7: "user-perception",
    8: "personality-ranking",
    9: "recent-user-reviews",
    10: "user-friends",
}


@dataclass(frozen=True)
class QueryResult:
    rows: list[dict[str, Any]]

    @property
    def row_count(self) -> int:
        return len(self.rows)


QueryHandler = Callable[[Connection, dict[str, Any]], QueryResult]


def _relevant_business(
    connection: Connection,
    parameters: dict[str, Any],
) -> QueryResult:
    longitude = _number(parameters, "longitude")
    latitude = _number(parameters, "latitude")
    _validate_coordinates(longitude, latitude)
    limit = _limit(parameters, "business_result_limit", default=1)

    # ponytail: exact global nearest-neighbour search scans every business;
    # add a dedicated geospatial index only if this becomes a measured bottleneck.
    businesses = []
    for _row_key, row in connection.table(BUSINESS_BY_LOCATION).scan(
        columns=_columns("business_id", "longitude", "latitude", "review_count")
    ):
        business_longitude = _float(row, "longitude")
        business_latitude = _float(row, "latitude")
        businesses.append(
            {
                "business_id": _text(row, "business_id"),
                "longitude": business_longitude,
                "latitude": business_latitude,
                "review_count": _integer(row, "review_count"),
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
    return QueryResult(businesses[:limit])


def _recent_business_tips(
    connection: Connection,
    parameters: dict[str, Any],
) -> QueryResult:
    business_id = _identifier(parameters, "business_id")
    reference_date = _reference_date(parameters)
    window_start = reference_date - timedelta(days=TWO_MONTH_WINDOW_DAYS)
    rows = _date_scan(
        connection.table(TIPS_BY_BUSINESS),
        business_id,
        window_start,
        reference_date,
        columns=_columns("business_id", "tip_id", "tipped_at", "user_id", "tip_text"),
        limit=_limit(parameters, "result_limit", default=10),
    )
    return QueryResult(
        [
            {
                "business_id": _text(row, "business_id"),
                "tip_id": _integer(row, "tip_id"),
                "tipped_at": _text(row, "tipped_at"),
                "user_id": _text(row, "user_id"),
                "tip_text": _text(row, "tip_text"),
            }
            for _row_key, row in rows
        ]
    )


def _top_business_tippers(
    connection: Connection,
    parameters: dict[str, Any],
) -> QueryResult:
    business_id = _identifier(parameters, "business_id")
    reference_date = _reference_date(parameters)
    window_start = reference_date - timedelta(days=ONE_YEAR_WINDOW_DAYS)
    rows = _date_scan(
        connection.table(TIPS_BY_BUSINESS),
        business_id,
        window_start,
        reference_date,
        columns=_columns("user_id"),
    )
    counts = Counter(_text(row, "user_id") for _row_key, row in rows)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    limit = min(_limit(parameters, "result_limit", default=10), 10)
    return QueryResult(
        [
            {"rank": rank, "user_id": user_id, "tip_count": tip_count}
            for rank, (user_id, tip_count) in enumerate(ranked[:limit], start=1)
        ]
    )


def _user_name(connection: Connection, parameters: dict[str, Any]) -> QueryResult:
    user_id = _identifier(parameters, "user_id")
    row = connection.table(USER).row(
        user_id.encode("utf-8"), columns=_columns("username")
    )
    return QueryResult(
        [] if not row else [{"user_id": user_id, "username": _text(row, "username")}]
    )


def _highest_star_business_review(
    connection: Connection,
    parameters: dict[str, Any],
) -> QueryResult:
    business_id = _identifier(parameters, "business_id")
    rows = connection.table(REVIEW_BY_BUSINESS).scan(
        row_prefix=_prefix(business_id),
        columns=_columns("business_id", "review_id", "stars"),
        limit=1,
    )
    return QueryResult(
        [
            {
                "business_id": _text(row, "business_id"),
                "review_id": _text(row, "review_id"),
                "stars": _integer(row, "stars"),
            }
            for _row_key, row in rows
        ]
    )


def _review_details(
    connection: Connection,
    parameters: dict[str, Any],
) -> QueryResult:
    review_id = _identifier(parameters, "review_id")
    row = connection.table(REVIEW).row(
        review_id.encode("utf-8"),
        columns=_columns("stars", "description", "username"),
    )
    return QueryResult(
        []
        if not row
        else [
            {
                "review_id": review_id,
                "stars": _integer(row, "stars"),
                "description": _text(row, "description"),
                "username": _text(row, "username"),
            }
        ]
    )


def _user_perception(
    connection: Connection,
    parameters: dict[str, Any],
) -> QueryResult:
    user_id = _identifier(parameters, "user_id")
    row = connection.table(USER).row(
        user_id.encode("utf-8"),
        columns=_columns(
            "username",
            "compliment_hot",
            "compliment_cut",
            "compliment_cool",
            "compliment_funny",
        ),
    )
    return QueryResult(
        []
        if not row
        else [
            {
                "user_id": user_id,
                "username": _text(row, "username"),
                "compliment_hot": _integer(row, "compliment_hot"),
                "compliment_cute": _integer(row, "compliment_cut"),
                "compliment_cool": _integer(row, "compliment_cool"),
                "compliment_funny": _integer(row, "compliment_funny"),
            }
        ]
    )


def _personality_ranking(
    connection: Connection,
    parameters: dict[str, Any],
) -> QueryResult:
    user_id = _identifier(
        parameters,
        "personality_user_id",
        fallback_name="user_id",
    )
    # ponytail: the ordered scan derives rank without another table; add a
    # user-to-rank lookup only if rank-query latency becomes important.
    for rank, (_row_key, row) in enumerate(
        connection.table(PERSONALITY_RANKING).scan(
            columns=_columns("user_id", "friends", "elite", "cool", "fans")
        ),
        start=1,
    ):
        if _text(row, "user_id") != user_id:
            continue
        friends = _integer(row, "friends")
        elite = _integer(row, "elite")
        cool = _integer(row, "cool")
        fans = _integer(row, "fans")
        return QueryResult(
            [
                {
                    "rank": rank,
                    "user_id": user_id,
                    "friends": friends,
                    "cool": cool,
                    "elite": elite,
                    "fans": fans,
                    "personality_score": (friends + elite + cool + fans) / 4,
                }
            ]
        )
    return QueryResult([])


def _recent_user_reviews(
    connection: Connection,
    parameters: dict[str, Any],
) -> QueryResult:
    user_id = _identifier(parameters, "user_id")
    reference_date = _reference_date(parameters)
    window_start = reference_date - timedelta(days=ONE_YEAR_WINDOW_DAYS)
    rows = _date_scan(
        connection.table(REVIEW_BY_USER),
        user_id,
        window_start,
        reference_date,
        columns=_columns("user_id", "review_id", "reviewed_at", "stars"),
    )
    reviews = [
        {
            "user_id": _text(row, "user_id"),
            "review_id": _text(row, "review_id"),
            "reviewed_at": _text(row, "reviewed_at"),
            "stars": _integer(row, "stars"),
        }
        for _row_key, row in rows
    ]
    reviews.sort(
        key=lambda review: (
            -review["stars"],
            -date.fromisoformat(review["reviewed_at"]).toordinal(),
            review["review_id"],
        )
    )
    return QueryResult(reviews[: _limit(parameters, "result_limit", default=10)])


def _user_friends(
    connection: Connection,
    parameters: dict[str, Any],
) -> QueryResult:
    user_id = _identifier(parameters, "user_id")
    rows = connection.table(FRIENDS_BY_USER).scan(
        row_prefix=_prefix(user_id),
        columns=_columns("user_id", "friend_id", "friend_name"),
        limit=_optional_limit(parameters, "friend_result_limit"),
    )
    return QueryResult(
        [
            {
                "user_id": _text(row, "user_id"),
                "friend_id": _text(row, "friend_id"),
                "friend_name": _text(row, "friend_name"),
            }
            for _row_key, row in rows
        ]
    )


QUERY_HANDLERS: dict[int, QueryHandler] = {
    1: _relevant_business,
    2: _recent_business_tips,
    3: _top_business_tippers,
    4: _user_name,
    5: _highest_star_business_review,
    6: _review_details,
    7: _user_perception,
    8: _personality_ranking,
    9: _recent_user_reviews,
    10: _user_friends,
}


def execute_query(
    question_id: int,
    connection: Connection,
    parameters: dict[str, Any],
) -> QueryResult:
    try:
        handler = QUERY_HANDLERS[question_id]
    except KeyError as error:
        raise ValueError(f"Unknown question ID: {question_id}") from error
    return handler(connection, parameters)


def haversine_distance_km(
    longitude_a: float,
    latitude_a: float,
    longitude_b: float,
    latitude_b: float,
) -> float:
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


def _date_scan(
    table,
    identifier: str,
    window_start: date,
    window_end: date,
    columns: list[bytes],
    limit: int | None = None,
):
    start = _date_prefix(identifier, window_end)
    stop = _date_prefix(identifier, window_start) + b"\xff"
    return table.scan(
        row_start=start,
        row_stop=stop,
        columns=columns,
        limit=limit,
    )


def _date_prefix(identifier: str, value: date) -> bytes:
    return f"{identifier}{ROW_KEY_SEPARATOR}{reverse_date(value)}{ROW_KEY_SEPARATOR}".encode(
        "utf-8"
    )


def _prefix(identifier: str) -> bytes:
    return f"{identifier}{ROW_KEY_SEPARATOR}".encode("utf-8")


def _columns(*names: str) -> list[bytes]:
    return [DATA_PREFIX + name.encode("ascii") for name in names]


def _text(row: dict[bytes, bytes], name: str) -> str:
    value = row.get(DATA_PREFIX + name.encode("ascii"))
    return "" if value is None else value.decode("utf-8")


def _integer(row: dict[bytes, bytes], name: str) -> int:
    value = row.get(DATA_PREFIX + name.encode("ascii"))
    return 0 if value is None else int(value)


def _float(row: dict[bytes, bytes], name: str) -> float:
    value = row.get(DATA_PREFIX + name.encode("ascii"))
    return 0.0 if value is None else float(value)


def _required(parameters: dict[str, Any], name: str) -> Any:
    if name not in parameters or parameters[name] is None:
        raise ValueError(f"Missing required parameter: {name}")
    return parameters[name]


def _identifier(
    parameters: dict[str, Any],
    name: str,
    fallback_name: str | None = None,
) -> str:
    value = parameters.get(name)
    if value is None and fallback_name is not None:
        value = parameters.get(fallback_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    if value.startswith("REPLACE_WITH_"):
        raise ValueError(f"{name} is still a placeholder in the parameter file")
    if ROW_KEY_SEPARATOR in value:
        raise ValueError(f"{name} cannot contain {ROW_KEY_SEPARATOR!r}")
    return value


def _reference_date(parameters: dict[str, Any]) -> date:
    value = _required(parameters, "reference_date")
    try:
        return date.fromisoformat(str(value))
    except ValueError as error:
        raise ValueError("reference_date must use YYYY-MM-DD format") from error


def _number(parameters: dict[str, Any], name: str) -> float:
    value = _required(parameters, name)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    return float(value)


def _limit(parameters: dict[str, Any], name: str, default: int) -> int:
    value = parameters.get(name, default)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _optional_limit(parameters: dict[str, Any], name: str) -> int | None:
    value = parameters.get(name)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer or null")
    return value


def _validate_coordinates(longitude: float, latitude: float) -> None:
    if not -180 <= longitude <= 180:
        raise ValueError("longitude must be between -180 and 180")
    if not -90 <= latitude <= 90:
        raise ValueError("latitude must be between -90 and 90")
