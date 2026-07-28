from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

from cassandra_nosql.db import close_cassandra, connect_to_cassandra
from cassandra_nosql.queries import (
    USE_CASE_NOTES,
    PreparedQueries,
    QueryResult,
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
    prepare_query_statements,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PARAMETERS_FILE = PROJECT_ROOT / "cassandra" / "query_parameters.json"
DEFAULT_OUTPUT_FILE = PROJECT_ROOT / "reports" / "cassandra" / "query_results.csv"

QUERY_INFO = {
    "relevant-business": (
        1,
        "Get the closest business by longitude and latitude, sorted by review count",
    ),
    "recent-business-tips": (
        2,
        "Find tips received by the business in the past two months",
    ),
    "top-business-tippers": (
        3,
        "Find the top ten users with the most stored tips in the past year",
    ),
    "user-name": (4, "Find a user's name"),
    "highest-star-business-review": (
        5,
        "Find the most starred review for the business",
    ),
    "review-details": (
        6,
        "Find the stored stars and username for a review",
    ),
    "user-perception": (7, "Fetch the community's perception of a user"),
    "personality-ranking": (
        8,
        "Calculate the user's global personality ranking",
    ),
    "recent-user-reviews": (
        9,
        "Find the user's reviews from the past year, ranked by stars",
    ),
    "user-friends": (10, "Get the stored names of a user's friends"),
}

QUERY_PARAMETER_KEYS = {
    "relevant-business": ("longitude", "latitude", "business_result_limit"),
    "recent-business-tips": ("business_id", "reference_date", "result_limit"),
    "top-business-tippers": ("business_id", "reference_date", "result_limit"),
    "user-name": ("user_id",),
    "highest-star-business-review": ("business_id",),
    "review-details": ("review_id",),
    "user-perception": ("user_id",),
    "personality-ranking": ("personality_user_id", "result_limit"),
    "recent-user-reviews": ("user_id", "reference_date", "result_limit"),
    "user-friends": ("user_id", "friend_result_limit"),
}

DETAIL_COLUMNS = [
    "database",
    "query_id",
    "query_name",
    "run_number",
    "parameters",
    "database_time_ms",
    "processing_time_ms",
    "total_time_ms",
    "row_count",
    "success",
    "error_message",
    "notes",
]

SUMMARY_COLUMNS = [
    "database",
    "query_id",
    "query_name",
    "measured_runs",
    "success_count",
    "failure_count",
    "average_total_time_ms",
    "median_total_time_ms",
    "minimum_total_time_ms",
    "maximum_total_time_ms",
    "average_database_time_ms",
    "average_processing_time_ms",
    "row_count",
    "notes",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run and measure the Cassandra Yelp comparison queries."
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--query", choices=QUERY_INFO)
    selection.add_argument("--all", action="store_true", dest="run_all")
    parser.add_argument(
        "--parameters-file",
        type=Path,
        default=DEFAULT_PARAMETERS_FILE,
        help=f"JSON query parameters (default: {DEFAULT_PARAMETERS_FILE})",
    )
    parser.add_argument(
        "--warmup-runs",
        type=int,
        default=0,
        help="Unrecorded warm-up executions per query (benchmark recommendation: 2)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Measured executions per query (benchmark recommendation: 10)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_FILE,
        help=f"Detailed CSV output (default: {DEFAULT_OUTPUT_FILE})",
    )
    return parser


def load_parameters(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as parameter_file:
        parameters = json.load(parameter_file)
    if not isinstance(parameters, dict):
        raise ValueError("The parameter file must contain one JSON object")
    return parameters


def execute_query(
    query_slug: str,
    session,
    statements: PreparedQueries,
    parameters: dict[str, Any],
) -> QueryResult:
    result_limit = parameters.get("result_limit", 10)

    if query_slug == "relevant-business":
        return find_relevant_business(
            session,
            _required(parameters, "longitude"),
            _required(parameters, "latitude"),
            parameters.get("business_result_limit", 1),
        )
    if query_slug == "recent-business-tips":
        return get_recent_business_tips(
            session,
            statements,
            _required(parameters, "business_id"),
            _reference_date(parameters),
            result_limit,
        )
    if query_slug == "top-business-tippers":
        return get_top_business_tippers(
            session,
            statements,
            _required(parameters, "business_id"),
            _reference_date(parameters),
            min(result_limit, 10),
        )
    if query_slug == "user-name":
        return get_user_name(
            session,
            statements,
            _required(parameters, "user_id"),
        )
    if query_slug == "highest-star-business-review":
        return get_highest_star_business_review(
            session,
            statements,
            _required(parameters, "business_id"),
        )
    if query_slug == "review-details":
        return get_review_details(
            session,
            statements,
            _required(parameters, "review_id"),
        )
    if query_slug == "user-perception":
        return get_user_perception(
            session,
            statements,
            _required(parameters, "user_id"),
        )
    if query_slug == "personality-ranking":
        personality_user_id = parameters.get(
            "personality_user_id", parameters.get("user_id")
        )
        return get_personality_ranking(
            session,
            personality_user_id,
            result_limit,
        )
    if query_slug == "recent-user-reviews":
        return get_recent_user_reviews(
            session,
            statements,
            _required(parameters, "user_id"),
            _reference_date(parameters),
            result_limit,
        )
    if query_slug == "user-friends":
        return get_user_friends(
            session,
            statements,
            _required(parameters, "user_id"),
            parameters.get("friend_result_limit"),
        )
    raise ValueError(f"Unknown query: {query_slug}")


def run_measurements(
    query_slugs: list[str],
    session,
    statements: PreparedQueries,
    parameters: dict[str, Any],
    warmup_runs: int,
    measured_runs: int,
) -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    any_failed = False

    for query_slug in query_slugs:
        query_id, query_name = QUERY_INFO[query_slug]
        compact_parameters = _compact_parameters(query_slug, parameters)
        print(f"\n[{query_id}] {query_slug}: {query_name}")

        for warmup_number in range(1, warmup_runs + 1):
            try:
                execute_query(query_slug, session, statements, parameters)
                print(f"  warm-up {warmup_number}/{warmup_runs}: success")
            except Exception as error:
                any_failed = True
                print(
                    f"  warm-up {warmup_number}/{warmup_runs}: "
                    f"{type(error).__name__}: {error}"
                )

        for run_number in range(1, measured_runs + 1):
            failure_start = perf_counter()
            try:
                result = execute_query(
                    query_slug,
                    session,
                    statements,
                    parameters,
                )
                record = {
                    "database": "Cassandra",
                    "query_id": query_id,
                    "query_name": query_slug,
                    "run_number": run_number,
                    "parameters": compact_parameters,
                    "database_time_ms": _rounded(result.database_time_ms),
                    "processing_time_ms": _rounded(result.processing_time_ms),
                    "total_time_ms": _rounded(result.total_time_ms),
                    "row_count": result.row_count,
                    "success": True,
                    "error_message": "",
                    "notes": result.notes,
                }
                records.append(record)
                print(
                    f"  run {run_number}/{measured_runs}: "
                    f"{result.row_count} row(s), "
                    f"db={result.database_time_ms:.3f} ms, "
                    f"python={result.processing_time_ms:.3f} ms, "
                    f"total={result.total_time_ms:.3f} ms"
                )
                if run_number == 1:
                    _print_preview(result)
            except Exception as error:
                any_failed = True
                failure_time_ms = (perf_counter() - failure_start) * 1_000
                error_message = f"{type(error).__name__}: {error}"
                records.append(
                    {
                        "database": "Cassandra",
                        "query_id": query_id,
                        "query_name": query_slug,
                        "run_number": run_number,
                        "parameters": compact_parameters,
                        "database_time_ms": "",
                        "processing_time_ms": "",
                        "total_time_ms": _rounded(failure_time_ms),
                        "row_count": 0,
                        "success": False,
                        "error_message": error_message,
                        "notes": USE_CASE_NOTES[query_slug],
                    }
                )
                print(f"  run {run_number}/{measured_runs}: FAILED: {error_message}")

        if USE_CASE_NOTES[query_slug]:
            print(f"  note: {USE_CASE_NOTES[query_slug]}")

    return records, any_failed


def write_reports(
    records: list[dict[str, Any]],
    output_path: Path,
) -> tuple[Path, Path]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=DETAIL_COLUMNS)
        writer.writeheader()
        writer.writerows(records)

    summary_path = (
        output_path.with_name("query_summary.csv")
        if output_path.name == "query_results.csv"
        else output_path.with_name(f"{output_path.stem}_summary.csv")
    )
    summaries = summarize_records(records)
    with summary_path.open("w", encoding="utf-8", newline="") as summary_file:
        writer = csv.DictWriter(summary_file, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summaries)

    return output_path, summary_path


def summarize_records(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(int(record["query_id"]), []).append(record)

    summaries = []
    for query_id in sorted(grouped):
        query_records = grouped[query_id]
        successful = [record for record in query_records if record["success"]]
        total_times = [float(record["total_time_ms"]) for record in successful]
        database_times = [float(record["database_time_ms"]) for record in successful]
        processing_times = [
            float(record["processing_time_ms"]) for record in successful
        ]
        summaries.append(
            {
                "database": "Cassandra",
                "query_id": query_id,
                "query_name": query_records[0]["query_name"],
                "measured_runs": len(query_records),
                "success_count": len(successful),
                "failure_count": len(query_records) - len(successful),
                "average_total_time_ms": _statistic(total_times, statistics.fmean),
                "median_total_time_ms": _statistic(total_times, statistics.median),
                "minimum_total_time_ms": _statistic(total_times, min),
                "maximum_total_time_ms": _statistic(total_times, max),
                "average_database_time_ms": _statistic(
                    database_times, statistics.fmean
                ),
                "average_processing_time_ms": _statistic(
                    processing_times, statistics.fmean
                ),
                "row_count": successful[0]["row_count"] if successful else 0,
                "notes": query_records[0]["notes"],
            }
        )
    return summaries


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.runs <= 0:
        parser.error("--runs must be greater than zero")
    if arguments.warmup_runs < 0:
        parser.error("--warmup-runs cannot be negative")

    try:
        parameters = load_parameters(arguments.parameters_file)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Could not load query parameters: {error}", file=sys.stderr)
        return 2

    query_slugs = list(QUERY_INFO) if arguments.run_all else [arguments.query]
    session = None
    try:
        session = connect_to_cassandra()
        statements = prepare_query_statements(session)
        records, any_failed = run_measurements(
            query_slugs,
            session,
            statements,
            parameters,
            arguments.warmup_runs,
            arguments.runs,
        )
        output_path, summary_path = write_reports(records, arguments.output)
        print(f"\nDetailed CSV: {output_path}")
        print(f"Summary CSV:  {summary_path}")
        return 1 if any_failed else 0
    except Exception as error:
        print(
            f"Cassandra query runner could not start: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1
    finally:
        if session is not None:
            close_cassandra(session)


def _required(parameters: dict[str, Any], name: str) -> Any:
    if name not in parameters or parameters[name] is None:
        raise ValueError(f"Missing required parameter: {name}")
    return parameters[name]


def _reference_date(parameters: dict[str, Any]) -> date:
    value = _required(parameters, "reference_date")
    try:
        return date.fromisoformat(str(value))
    except ValueError as error:
        raise ValueError("reference_date must use YYYY-MM-DD format") from error


def _compact_parameters(
    query_slug: str,
    parameters: dict[str, Any],
) -> str:
    selected = {
        key: parameters.get(key)
        for key in QUERY_PARAMETER_KEYS[query_slug]
        if key in parameters
    }
    if (
        query_slug == "personality-ranking"
        and "personality_user_id" not in selected
        and "user_id" in parameters
    ):
        selected["user_id"] = parameters["user_id"]
    return json.dumps(selected, separators=(",", ":"), sort_keys=True)


def _print_preview(result: QueryResult, preview_size: int = 3) -> None:
    if not result.rows:
        print("    result: no rows found")
        return
    print("    result preview:")
    preview = json.dumps(result.rows[:preview_size], indent=2, default=str)
    for line in preview.splitlines():
        print(f"      {line}")


def _rounded(value: float) -> float:
    return round(value, 6)


def _statistic(values: list[float], function) -> float | str:
    return _rounded(function(values)) if values else ""


if __name__ == "__main__":
    raise SystemExit(main())
