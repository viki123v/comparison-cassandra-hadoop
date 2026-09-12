import csv
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from hbase.queries import execute_query
from hbase.row_keys import (
    business_by_location_key,
    friend_by_user_key,
    personality_ranking_key,
    review_by_business_key,
    review_by_user_key,
    tip_by_business_key,
)
from hbase.run_queries import write_report
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


def columns(**values: str | int | float) -> dict[bytes, bytes]:
    return {f"d:{name}".encode(): str(value).encode() for name, value in values.items()}


class FakeTable:
    def __init__(self, rows: dict[bytes, dict[bytes, bytes]]):
        self.rows = rows

    def row(self, row_key: bytes, columns=None):
        return self._project(self.rows.get(row_key, {}), columns)

    def scan(
        self,
        row_start=None,
        row_stop=None,
        row_prefix=None,
        columns=None,
        limit=None,
    ):
        returned = 0
        for row_key in sorted(self.rows):
            if row_prefix is not None and not row_key.startswith(row_prefix):
                continue
            if row_start is not None and row_key < row_start:
                continue
            if row_stop is not None and row_key >= row_stop:
                continue
            yield row_key, self._project(self.rows[row_key], columns)
            returned += 1
            if limit is not None and returned == limit:
                return

    @staticmethod
    def _project(row: dict[bytes, bytes], selected) -> dict[bytes, bytes]:
        if selected is None:
            return dict(row)
        return {column: row[column] for column in selected if column in row}


class FakeConnection:
    def __init__(self, tables: dict[str, dict[bytes, dict[bytes, bytes]]]):
        self.tables = {name: FakeTable(rows) for name, rows in tables.items()}

    def table(self, name: str) -> FakeTable:
        return self.tables[name]


class QueryTests(unittest.TestCase):
    def setUp(self):
        reference_date = date(2018, 5, 5)
        recent_boundary = reference_date - timedelta(days=60)
        year_boundary = reference_date - timedelta(days=365)
        self.parameters = {
            "reference_date": reference_date.isoformat(),
            "business_id": "b1",
            "user_id": "u1",
            "personality_user_id": "u1",
            "review_id": "r1",
            "longitude": 0.0,
            "latitude": 0.0,
            "business_result_limit": 1,
            "result_limit": 10,
            "friend_result_limit": None,
        }
        self.connection = FakeConnection(
            {
                BUSINESS_BY_LOCATION: {
                    business_by_location_key("b1", 0.0, 0.0, 5): columns(
                        business_id="b1",
                        longitude=0.0,
                        latitude=0.0,
                        review_count=5,
                    ),
                    business_by_location_key("b2", 1.0, 1.0, 100): columns(
                        business_id="b2",
                        longitude=1.0,
                        latitude=1.0,
                        review_count=100,
                    ),
                },
                TIPS_BY_BUSINESS: {
                    tip_by_business_key("b1", reference_date, 1): columns(
                        business_id="b1",
                        tip_id=1,
                        tipped_at=reference_date.isoformat(),
                        user_id="u2",
                        tip_text="new",
                    ),
                    tip_by_business_key("b1", recent_boundary, 2): columns(
                        business_id="b1",
                        tip_id=2,
                        tipped_at=recent_boundary.isoformat(),
                        user_id="u2",
                        tip_text="boundary",
                    ),
                    tip_by_business_key(
                        "b1", recent_boundary - timedelta(days=1), 3
                    ): columns(
                        business_id="b1",
                        tip_id=3,
                        tipped_at=(recent_boundary - timedelta(days=1)).isoformat(),
                        user_id="u1",
                        tip_text="older",
                    ),
                },
                USER: {
                    b"u1": columns(
                        username="Alice",
                        compliment_hot=1,
                        compliment_cut=2,
                        compliment_cool=3,
                        compliment_funny=4,
                    )
                },
                REVIEW_BY_BUSINESS: {
                    review_by_business_key("b1", 3, "r2"): columns(
                        business_id="b1", review_id="r2", stars=3
                    ),
                    review_by_business_key("b1", 5, "r1"): columns(
                        business_id="b1", review_id="r1", stars=5
                    ),
                },
                REVIEW: {
                    b"r1": columns(stars=5, description="Excellent", username="Alice")
                },
                PERSONALITY_RANKING: {
                    personality_ranking_key(20, "u2"): columns(
                        user_id="u2", friends=5, elite=5, cool=5, fans=5
                    ),
                    personality_ranking_key(10, "u1"): columns(
                        user_id="u1", friends=4, elite=3, cool=2, fans=1
                    ),
                },
                REVIEW_BY_USER: {
                    review_by_user_key(
                        "u1", reference_date - timedelta(days=2), 3, "ur1"
                    ): columns(
                        user_id="u1",
                        review_id="ur1",
                        reviewed_at=(reference_date - timedelta(days=2)).isoformat(),
                        stars=3,
                    ),
                    review_by_user_key("u1", year_boundary, 5, "ur2"): columns(
                        user_id="u1",
                        review_id="ur2",
                        reviewed_at=year_boundary.isoformat(),
                        stars=5,
                    ),
                    review_by_user_key(
                        "u1", year_boundary - timedelta(days=1), 5, "outside"
                    ): columns(
                        user_id="u1",
                        review_id="outside",
                        reviewed_at=(year_boundary - timedelta(days=1)).isoformat(),
                        stars=5,
                    ),
                },
                FRIENDS_BY_USER: {
                    friend_by_user_key("u1", "u2"): columns(
                        user_id="u1", friend_id="u2", friend_name="Bob"
                    ),
                    friend_by_user_key("u1", "u3"): columns(
                        user_id="u1", friend_id="u3", friend_name="Carol"
                    ),
                },
            }
        )

    def test_all_queries(self):
        results = {
            question_id: execute_query(
                question_id, self.connection, self.parameters
            ).rows
            for question_id in range(1, 11)
        }

        self.assertEqual(results[1][0]["business_id"], "b1")
        self.assertEqual([row["tip_id"] for row in results[2]], [1, 2])
        self.assertEqual(results[3][0], {"rank": 1, "user_id": "u2", "tip_count": 2})
        self.assertEqual(results[4], [{"user_id": "u1", "username": "Alice"}])
        self.assertEqual(results[5][0]["review_id"], "r1")
        self.assertEqual(results[6][0]["description"], "Excellent")
        self.assertEqual(results[7][0]["compliment_cute"], 2)
        self.assertEqual(results[8][0]["rank"], 2)
        self.assertEqual(results[8][0]["personality_score"], 2.5)
        self.assertEqual([row["review_id"] for row in results[9]], ["ur2", "ur1"])
        self.assertEqual([row["friend_name"] for row in results[10]], ["Bob", "Carol"])

    def test_rejects_bad_query_input(self):
        with self.assertRaisesRegex(ValueError, "Unknown question ID"):
            execute_query(11, self.connection, self.parameters)

        invalid = {**self.parameters, "user_id": "REPLACE_WITH_USER"}
        with self.assertRaisesRegex(ValueError, "still a placeholder"):
            execute_query(4, self.connection, invalid)

    def test_report_has_the_shared_two_column_format(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "query_summary.csv"
            write_report(
                [{"question_id": 1, "median_time_ms": 1.25}],
                output,
            )
            with output.open(newline="", encoding="utf-8") as report:
                self.assertEqual(
                    list(csv.DictReader(report)),
                    [{"question_id": "1", "median_time_ms": "1.25"}],
                )


if __name__ == "__main__":
    unittest.main()
