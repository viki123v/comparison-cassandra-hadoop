from collections import Counter

from hbase.db import connect_to_hbase
from hbase.schema import CHECKS_BY_BUSINESS, FRIENDS_BY_USER, TABLES


SAMPLE_SIZE = 5
SCAN_BATCH_SIZE = 1_000
RELATION_LIMIT = 5


def decode(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


def print_sample_row(index: int, row_key: bytes, values: dict[bytes, bytes]) -> None:
    print(f"  {index}. row_key: {decode(row_key)}")
    for column, value in sorted(values.items()):
        print(f"     {decode(column)}: {decode(value)}")


def validate() -> bool:
    connection = connect_to_hbase()
    friend_counts: Counter[bytes] = Counter()
    checkin_counts: Counter[bytes] = Counter()
    is_valid = True

    try:
        existing_tables = {decode(name) for name in connection.tables()}
        missing_tables = set(TABLES) - existing_tables
        if missing_tables:
            print("Missing expected tables:")
            for table_name in sorted(missing_tables):
                print(f"  - {table_name}")
            return False

        for table_name in TABLES:
            row_count = 0
            sample_rows: list[tuple[bytes, dict[bytes, bytes]]] = []

            for row_key, values in connection.table(table_name).scan(
                batch_size=SCAN_BATCH_SIZE
            ):
                row_count += 1

                if len(sample_rows) < SAMPLE_SIZE:
                    sample_rows.append((row_key, values))

                relation_owner, separator, _ = row_key.partition(b"|")
                if not separator:
                    continue
                if table_name == FRIENDS_BY_USER:
                    friend_counts[relation_owner] += 1
                elif table_name == CHECKS_BY_BUSINESS:
                    checkin_counts[relation_owner] += 1

            print(f"\nTable: {table_name}")
            print(f"Row count: {row_count}")
            print(f"First {min(SAMPLE_SIZE, row_count)} rows:")
            for index, (row_key, values) in enumerate(sample_rows, start=1):
                print_sample_row(index, row_key, values)

        print("\nRelation-limit validation")
        is_valid &= print_limit_result(
            relation_name="friends per user",
            counts=friend_counts,
        )
        is_valid &= print_limit_result(
            relation_name="check-in dates per business",
            counts=checkin_counts,
        )
    finally:
        connection.close()

    return is_valid


def print_limit_result(
    relation_name: str,
    counts: Counter[bytes],
) -> bool:
    maximum = max(counts.values(), default=0)
    offenders = [
        (decode(owner_id), count)
        for owner_id, count in counts.items()
        if count > RELATION_LIMIT
    ]

    if not offenders:
        print(
            f"  PASS: {relation_name} <= {RELATION_LIMIT} "
            f"(maximum observed: {maximum})"
        )
        return True

    print(
        f"  FAIL: {len(offenders)} owner(s) exceed the "
        f"{RELATION_LIMIT} {relation_name} limit"
    )
    for owner_id, count in sorted(offenders)[:SAMPLE_SIZE]:
        print(f"    {owner_id}: {count}")
    return False


def main() -> None:
    if validate():
        print("\nValidation passed.")
        return

    print("\nValidation failed.")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
