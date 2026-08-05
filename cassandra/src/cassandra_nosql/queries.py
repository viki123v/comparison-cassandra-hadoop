from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from typing import Any, Callable, Protocol

from cassandra import ConsistencyLevel


TWO_MONTH_WINDOW_DAYS = 60
ONE_YEAR_WINDOW_DAYS = 365
EARTH_RADIUS_KM = 6_371.0088

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


class QueryHandler(Protocol):
    def prepare(self, session) -> Any: ...

    def execute(
        self,
        session,
        prepared_statement: Any,
        parameters: dict[str, Any],
    ) -> QueryResult: ...


ParameterBuilder = Callable[[dict[str, Any]], tuple[Any, ...]]
RowTransformer = Callable[[list[dict[str, Any]], dict[str, Any]], list[dict[str, Any]]]
PreparedQueries = dict[int, Any]


@dataclass(frozen=True)
class SimpleQueryHandler:
    cql: str
    parameter_builder: ParameterBuilder
    row_transformer: RowTransformer

    def prepare(self, session):
        return _prepare(session, self.cql)

    def execute(
        self,
        session,
        prepared_statement,
        parameters: dict[str, Any],
    ) -> QueryResult:
        values = self.parameter_builder(parameters)
        rows = list(session.execute(prepared_statement, values))
        return QueryResult(self.row_transformer(rows, parameters))


class RelevantBusinessQuery:
    cql = """
        SELECT id, longitude, latitude, review_count
        FROM nosql.business
    """

    def prepare(self, session):
        return _prepare(session, self.cql)

    def execute(
        self,
        session,
        prepared_statement,
        parameters: dict[str, Any],
    ) -> QueryResult:
        longitude = _number(parameters, "longitude")
        latitude = _number(parameters, "latitude")
        _validate_coordinates(longitude, latitude)
        limit = _limit(parameters, "business_result_limit", default=1)

        businesses = []
        for row in session.execute(prepared_statement):
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
        return QueryResult(businesses[:limit])


class TopBusinessTippersQuery:
    cql = """
        SELECT id, tipped_at
        FROM nosql.users_by_business
        WHERE tip_business_id = ?
          AND tipped_at >= ?
          AND tipped_at <= ?
    """

    def prepare(self, session):
        return _prepare(session, self.cql)

    def execute(
        self,
        session,
        prepared_statement,
        parameters: dict[str, Any],
    ) -> QueryResult:
        business_id = _identifier(parameters, "business_id")
        reference_date = _reference_date(parameters)
        window_start = reference_date - timedelta(days=ONE_YEAR_WINDOW_DAYS)
        limit = min(_limit(parameters, "result_limit", default=10), 10)

        rows = session.execute(
            prepared_statement,
            (business_id, window_start, reference_date),
        )
        counts = Counter(str(row["id"]) for row in rows)
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return QueryResult(
            [
                {"rank": rank, "user_id": user_id, "tip_count": tip_count}
                for rank, (user_id, tip_count) in enumerate(ranked[:limit], start=1)
            ]
        )


class RecentUserReviewsQuery:
    cql = """
        SELECT user_id, review_id, reviewed_at, stars
        FROM nosql.review_by_user
        WHERE user_id = ?
          AND stars = ?
          AND reviewed_at >= ?
          AND reviewed_at <= ?
        LIMIT ?
    """

    def prepare(self, session):
        return _prepare(session, self.cql)

    def execute(
        self,
        session,
        prepared_statement,
        parameters: dict[str, Any],
    ) -> QueryResult:
        user_id = _identifier(parameters, "user_id")
        reference_date = _reference_date(parameters)
        window_start = reference_date - timedelta(days=ONE_YEAR_WINDOW_DAYS)
        limit = _limit(parameters, "result_limit", default=10)
        reviews: list[dict[str, Any]] = []

        # Cassandra orders each fixed-star slice by reviewed_at. Reading the
        # five star values from high to low produces the requested global order.
        for stars in range(5, 0, -1):
            remaining = limit - len(reviews)
            if remaining == 0:
                break
            rows = session.execute(
                prepared_statement,
                (user_id, stars, window_start, reference_date, remaining),
            )
            reviews.extend(
                {
                    "user_id": row["user_id"],
                    "review_id": row["review_id"],
                    "reviewed_at": _as_date(row["reviewed_at"]).isoformat(),
                    "stars": int(row["stars"]),
                }
                for row in rows
            )

        return QueryResult(reviews)


QUERY_HANDLERS: dict[int, QueryHandler] = {
    1: RelevantBusinessQuery(),
    2: SimpleQueryHandler(
        cql="""
            SELECT business_id, tip_id, tipped_at, user_id, tip_text
            FROM nosql.tips_by_business
            WHERE business_id = ?
              AND tipped_at >= ?
              AND tipped_at <= ?
            LIMIT ?
        """,
        parameter_builder=lambda parameters: _date_window_parameters(
            parameters,
            "business_id",
            TWO_MONTH_WINDOW_DAYS,
            "result_limit",
        ),
        row_transformer=lambda rows, _parameters: [
            {
                "business_id": row["business_id"],
                "tip_id": int(row["tip_id"]),
                "tipped_at": _as_date(row["tipped_at"]).isoformat(),
                "user_id": row["user_id"],
                "tip_text": row.get("tip_text") or "",
            }
            for row in rows
        ],
    ),
    3: TopBusinessTippersQuery(),
    4: SimpleQueryHandler(
        cql="""
            SELECT id, username
            FROM nosql.user
            WHERE id = ?
        """,
        parameter_builder=lambda parameters: (_identifier(parameters, "user_id"),),
        row_transformer=lambda rows, _parameters: [
            {"user_id": row["id"], "username": row.get("username") or ""}
            for row in rows
        ],
    ),
    5: SimpleQueryHandler(
        cql="""
            SELECT business_id, review_id, stars
            FROM nosql.review_by_business
            WHERE business_id = ?
            LIMIT 1
        """,
        parameter_builder=lambda parameters: (_identifier(parameters, "business_id"),),
        row_transformer=lambda rows, _parameters: [
            {
                "business_id": row["business_id"],
                "review_id": row["review_id"],
                "stars": int(row["stars"]),
            }
            for row in rows
        ],
    ),
    6: SimpleQueryHandler(
        cql="""
            SELECT id, stars, description, username
            FROM nosql.review
            WHERE id = ?
        """,
        parameter_builder=lambda parameters: (_identifier(parameters, "review_id"),),
        row_transformer=lambda rows, _parameters: [
            {
                "review_id": row["id"],
                "stars": int(row["stars"]),
                "description": row.get("description") or "",
                "username": row.get("username") or "",
            }
            for row in rows
        ],
    ),
    7: SimpleQueryHandler(
        cql="""
            SELECT id, username, compliment_hot, compliment_cut,
                   compliment_cool, compliment_funny
            FROM nosql.user
            WHERE id = ?
        """,
        parameter_builder=lambda parameters: (_identifier(parameters, "user_id"),),
        row_transformer=lambda rows, _parameters: [
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
    ),
    8: SimpleQueryHandler(
        cql="""
            SELECT user_id, friends, elite, cool, fans,
                   personality_score, global_rank
            FROM nosql.user_by_personality_score
            WHERE user_id = ?
        """,
        parameter_builder=lambda parameters: (
            _identifier(
                parameters,
                "personality_user_id",
                fallback_name="user_id",
            ),
        ),
        row_transformer=lambda rows, _parameters: [
            {
                "rank": int(row["global_rank"]),
                "user_id": row["user_id"],
                "friends": int(row.get("friends") or 0),
                "cool": int(row.get("cool") or 0),
                "elite": int(row.get("elite") or 0),
                "fans": int(row.get("fans") or 0),
                "personality_score": float(row["personality_score"]),
            }
            for row in rows
        ],
    ),
    9: RecentUserReviewsQuery(),
    10: SimpleQueryHandler(
        cql="""
            SELECT user_id, friend_id, friend_name
            FROM nosql.user_by_friends
            WHERE user_id = ?
        """,
        parameter_builder=lambda parameters: (_identifier(parameters, "user_id"),),
        row_transformer=lambda rows, parameters: _friend_rows(rows, parameters),
    ),
}


def prepare_query_statements(session) -> PreparedQueries:
    """Prepare every benchmark statement before execution begins.

    The Cassandra Python driver sends each CQL structure to Cassandra once so
    Cassandra can parse it and return prepared metadata. Later executions bind
    parameter values to that prepared statement. Preparation happens before
    warm-up and measured runs, excluding preparation overhead from timings and
    avoiding repeated preparation of identical CQL during the benchmark.
    """
    return {
        question_id: handler.prepare(session)
        for question_id, handler in QUERY_HANDLERS.items()
    }


def execute_query(
    question_id: int,
    session,
    statements: PreparedQueries,
    parameters: dict[str, Any],
) -> QueryResult:
    try:
        handler = QUERY_HANDLERS[question_id]
        prepared_statement = statements[question_id]
    except KeyError as error:
        raise ValueError(f"Unknown question ID: {question_id}") from error
    return handler.execute(session, prepared_statement, parameters)


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


def _prepare(session, cql: str):
    statement = session.prepare(cql)
    statement.consistency_level = ConsistencyLevel.LOCAL_ONE
    return statement


def _date_window_parameters(
    parameters: dict[str, Any],
    identifier_name: str,
    window_days: int,
    limit_name: str,
) -> tuple[Any, ...]:
    reference_date = _reference_date(parameters)
    return (
        _identifier(parameters, identifier_name),
        reference_date - timedelta(days=window_days),
        reference_date,
        _limit(parameters, limit_name, default=10),
    )


def _friend_rows(
    rows: list[dict[str, Any]],
    parameters: dict[str, Any],
) -> list[dict[str, Any]]:
    limit = _optional_limit(parameters, "friend_result_limit")
    friends = [
        {
            "user_id": row["user_id"],
            "friend_id": row["friend_id"],
            "friend_name": row.get("friend_name") or "",
        }
        for row in rows
    ]
    return friends if limit is None else friends[:limit]


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


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


def _limit(
    parameters: dict[str, Any],
    name: str,
    default: int,
) -> int:
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
