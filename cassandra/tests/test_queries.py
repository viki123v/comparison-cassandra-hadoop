import csv
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from unittest.mock import patch

from cassandra_nosql.queries import (
    BUSINESS_SCAN,
    PERSONALITY_SCAN,
    PreparedQueries,
    find_relevant_business,
    get_highest_star_business_review,
    get_personality_ranking,
    get_recent_business_tips,
    get_recent_user_reviews,
    get_review_details,
    get_top_business_tippers,
    get_user_friends,
    get_user_name,
    get_user_perception,
    haversine_distance_km,
)
from cassandra_nosql.run_queries import run_measurements, write_reports


class FakeSession:
    def __init__(self, rows_by_statement):
        self.rows_by_statement = rows_by_statement

    def execute(self, statement, parameters=None):
        del parameters
        return self.rows_by_statement.get(statement, [])


STATEMENTS = PreparedQueries(
    recent_business_tips="recent-business-tips",
    top_business_tippers="top-business-tippers",
    user_name="user-name",
    highest_star_business_review="highest-star-business-review",
    review_details="review-details",
    user_perception="user-perception",
    recent_user_reviews="recent-user-reviews",
    user_friends="user-friends",
)


class QueryProcessingTests(unittest.TestCase):
    def test_relevant_business_uses_distance_then_review_count(self):
        session = FakeSession(
            {
                BUSINESS_SCAN: [
                    {
                        "id": "lower-reviews",
                        "longitude": 10,
                        "latitude": 20,
                        "review_count": 2,
                    },
                    {
                        "id": "higher-reviews",
                        "longitude": 10,
                        "latitude": 20,
                        "review_count": 20,
                    },
                ]
            }
        )

        result = find_relevant_business(session, 10, 20)

        self.assertEqual(result.rows[0]["business_id"], "higher-reviews")
        self.assertAlmostEqual(haversine_distance_km(10, 20, 10, 20), 0)

    def test_tip_queries_filter_dates_and_rank_stored_rows(self):
        session = FakeSession(
            {
                "recent-business-tips": [
                    {
                        "business_id": "b1",
                        "tip_id": 1,
                        "tipped_at": date(2022, 1, 18),
                    },
                    {
                        "business_id": "b1",
                        "tip_id": 2,
                        "tipped_at": date(2021, 1, 1),
                    },
                ],
                "top-business-tippers": [
                    {"id": "u2", "tipped_at": date(2022, 1, 1)},
                    {"id": "u1", "tipped_at": date(2022, 1, 2)},
                    {"id": "u1", "tipped_at": date(2022, 1, 3)},
                    {"id": "old", "tipped_at": date(2020, 1, 1)},
                ],
            }
        )

        tips = get_recent_business_tips(session, STATEMENTS, "b1", date(2022, 1, 19))
        tippers = get_top_business_tippers(session, STATEMENTS, "b1", date(2022, 1, 19))

        self.assertEqual([tip["tip_id"] for tip in tips.rows], [1])
        self.assertEqual(tippers.rows[0]["user_id"], "u1")
        self.assertEqual(tippers.rows[0]["stored_tip_count"], 2)

    def test_exact_lookup_review_and_friend_queries(self):
        session = FakeSession(
            {
                "user-name": [{"id": "u1", "username": "Ada"}],
                "highest-star-business-review": [
                    {"business_id": "b1", "review_id": "z", "stars": 5},
                    {"business_id": "b1", "review_id": "a", "stars": 5},
                    {"business_id": "b1", "review_id": "m", "stars": 4},
                ],
                "review-details": [{"id": "r1", "stars": 4, "username": "Ada"}],
                "user-perception": [
                    {
                        "id": "u1",
                        "username": "Ada",
                        "compliment_hot": 1,
                        "compliment_cut": 2,
                        "compliment_cool": 3,
                        "compliment_funny": 4,
                    }
                ],
                "user-friends": [
                    {"user_id": "u1", "friend_id": "u3", "friend_name": ""},
                    {"user_id": "u1", "friend_id": "u2", "friend_name": "Bob"},
                ],
            }
        )

        self.assertEqual(get_user_name(session, STATEMENTS, "u1").row_count, 1)
        best_review = get_highest_star_business_review(session, STATEMENTS, "b1")
        self.assertEqual(best_review.rows[0]["review_id"], "a")
        self.assertEqual(
            get_review_details(session, STATEMENTS, "r1").rows[0]["stars"], 4
        )
        perception = get_user_perception(session, STATEMENTS, "u1")
        self.assertEqual(perception.rows[0]["compliment_cute"], 2)
        friends = get_user_friends(session, STATEMENTS, "u1")
        self.assertTrue(friends.rows[1]["name_missing"])

    def test_personality_and_recent_review_ranking(self):
        session = FakeSession(
            {
                PERSONALITY_SCAN: [
                    {
                        "user_id": "u1",
                        "friends": 4,
                        "cool": 4,
                        "elite": 4,
                        "fans": 4,
                    },
                    {
                        "user_id": "u2",
                        "friends": 8,
                        "cool": 8,
                        "elite": 8,
                        "fans": 8,
                    },
                ],
                "recent-user-reviews": [
                    {
                        "user_id": "u1",
                        "review_id": "older-five",
                        "reviewed_at": date(2021, 12, 1),
                        "stars": 5,
                    },
                    {
                        "user_id": "u1",
                        "review_id": "newer-five",
                        "reviewed_at": date(2022, 1, 1),
                        "stars": 5,
                    },
                    {
                        "user_id": "u1",
                        "review_id": "old",
                        "reviewed_at": date(2020, 1, 1),
                        "stars": 5,
                    },
                ],
            }
        )

        personality = get_personality_ranking(session, "u1")
        reviews = get_recent_user_reviews(session, STATEMENTS, "u1", date(2022, 1, 19))

        self.assertEqual(personality.rows[0]["rank"], 2)
        self.assertEqual(reviews.rows[0]["review_id"], "newer-five")
        self.assertEqual(len(reviews.rows), 2)


class CsvReportTests(unittest.TestCase):
    def test_all_query_run_records_failure_and_continues(self):
        successful_result = type(
            "Result",
            (),
            {
                "database_time_ms": 1.0,
                "processing_time_ms": 0.1,
                "total_time_ms": 1.1,
                "row_count": 1,
                "rows": [{"review_id": "r1"}],
                "notes": "",
            },
        )()

        def fake_execute(query_slug, session, statements, parameters):
            del session, statements, parameters
            if query_slug == "user-name":
                raise RuntimeError("expected test failure")
            return successful_result

        with (
            patch(
                "cassandra_nosql.run_queries.execute_query",
                side_effect=fake_execute,
            ),
            redirect_stdout(io.StringIO()),
        ):
            records, any_failed = run_measurements(
                ["user-name", "review-details"],
                session=None,
                statements=None,
                parameters={"user_id": "u1", "review_id": "r1"},
                warmup_runs=0,
                measured_runs=1,
            )

        self.assertTrue(any_failed)
        self.assertFalse(records[0]["success"])
        self.assertTrue(records[1]["success"])

    def test_detail_and_summary_csv_are_created(self):
        records = [
            {
                "database": "Cassandra",
                "query_id": 4,
                "query_name": "user-name",
                "run_number": 1,
                "parameters": '{"user_id":"u1"}',
                "database_time_ms": 1.0,
                "processing_time_ms": 0.1,
                "total_time_ms": 1.1,
                "row_count": 1,
                "success": True,
                "error_message": "",
                "notes": "",
            }
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "query_results.csv"

            detail_path, summary_path = write_reports(records, output)

            self.assertTrue(detail_path.exists())
            self.assertTrue(summary_path.exists())
            with detail_path.open(encoding="utf-8") as detail_file:
                rows = list(csv.DictReader(detail_file))
            self.assertEqual(rows[0]["query_name"], "user-name")


if __name__ == "__main__":
    unittest.main()
