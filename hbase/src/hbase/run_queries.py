from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

from hbase.db import connect_to_hbase
from hbase.queries import QUESTION_SLUGS, QueryResult, execute_query


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PARAMETERS_FILE = PROJECT_ROOT / "hbase" / "query_parameters.json"
DEFAULT_OUTPUT_FILE = PROJECT_ROOT / "reports" / "hbase" / "query_summary.csv"

QUESTION_IDS = {slug: question_id for question_id, slug in QUESTION_SLUGS.items()}
CSV_COLUMNS = ["question_id", "median_time_ms"]
MAX_MEASURED_ATTEMPTS = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the HBase Yelp benchmark. Question IDs follow the "
            "ordering in docs/shared/yelp/queries.md."
        )
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--query",
        choices=QUESTION_IDS,
        help="Run one question for diagnosis without replacing the benchmark CSV.",
    )
    selection.add_argument(
        "--all",
        action="store_true",
        dest="run_all",
        help="Run all ten questions and write the benchmark CSV.",
    )
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
        help="Unrecorded warm-up executions per question (recommended: 2)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Successful measured executions per question (recommended: 10)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_FILE,
        help=f"Two-column benchmark CSV (default: {DEFAULT_OUTPUT_FILE})",
    )
    return parser


def load_parameters(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as parameter_file:
        parameters = json.load(parameter_file)
    if not isinstance(parameters, dict):
        raise ValueError("The parameter file must contain one JSON object")
    return parameters


def run_measurements(
    question_ids: list[int],
    connection,
    parameters: dict[str, Any],
    warmup_runs: int,
    measured_runs: int,
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []

    for question_id in question_ids:
        print(f"\nQuestion {question_id}")

        for warmup_number in range(1, warmup_runs + 1):
            try:
                execute_query(question_id, connection, parameters)
            except Exception as error:
                raise RuntimeError(
                    f"Question {question_id} warm-up failed: "
                    f"{type(error).__name__}: {error}"
                ) from error
            print(f"  warm-up {warmup_number}/{warmup_runs}: success")

        timings: list[float] = []
        measured_attempt = 0
        maximum_attempts = measured_runs * MAX_MEASURED_ATTEMPTS

        while len(timings) < measured_runs and measured_attempt < maximum_attempts:
            measured_attempt += 1
            try:
                measured_start = perf_counter()
                result = execute_query(question_id, connection, parameters)
                elapsed_ms = (perf_counter() - measured_start) * 1_000
            except Exception as original_error:
                print(
                    f"  measured attempt {measured_attempt}: failed; "
                    "running one untimed diagnostic retry"
                )
                try:
                    execute_query(question_id, connection, parameters)
                except Exception as retry_error:
                    raise RuntimeError(
                        f"Question {question_id} failed during a measured "
                        f"execution ({type(original_error).__name__}: "
                        f"{original_error}); its diagnostic retry also failed "
                        f"({type(retry_error).__name__}: {retry_error})"
                    ) from original_error
                print("    diagnostic retry succeeded; no timing was recorded")
                continue

            timings.append(elapsed_ms)
            successful_run = len(timings)
            print(
                f"  measured run {successful_run}/{measured_runs}: {elapsed_ms:.3f} ms"
            )
            if successful_run == 1:
                _print_preview(result)

        if len(timings) != measured_runs:
            raise RuntimeError(
                f"Question {question_id} collected {len(timings)} of "
                f"{measured_runs} required successful timings after "
                f"{measured_attempt} measured attempts"
            )

        median_time_ms = round(statistics.median(timings), 6)
        summaries.append({"question_id": question_id, "median_time_ms": median_time_ms})
        print(f"  median: {median_time_ms:.6f} ms")

    return summaries


def write_report(summaries: list[dict[str, Any]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(summaries)
    return output_path


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

    question_ids = (
        list(QUESTION_SLUGS) if arguments.run_all else [QUESTION_IDS[arguments.query]]
    )
    connection = None
    try:
        connection = connect_to_hbase()
        summaries = run_measurements(
            question_ids,
            connection,
            parameters,
            arguments.warmup_runs,
            arguments.runs,
        )
        if arguments.run_all:
            output_path = write_report(summaries, arguments.output)
            print(f"\nBenchmark CSV: {output_path}")
        return 0
    except Exception as error:
        print(
            f"HBase benchmark failed: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1
    finally:
        if connection is not None:
            connection.close()


def _print_preview(result: QueryResult, preview_size: int = 3) -> None:
    if not result.rows:
        print("    result: no rows found")
        return
    print("    result preview:")
    preview = json.dumps(result.rows[:preview_size], indent=2, default=str)
    for line in preview.splitlines():
        print(f"      {line}")


if __name__ == "__main__":
    raise SystemExit(main())
