from datetime import date


ROW_KEY_SEPARATOR = "|"
GEOHASH_ALPHABET = "0123456789bcdefghjkmnpqrstuvwxyz"
MAX_SIGNED_64_BIT = (1 << 63) - 1
MAX_DATE_ORDINAL = date.max.toordinal()


def geohash(latitude: float, longitude: float, precision: int = 5) -> str:
    if not -90 <= latitude <= 90:
        raise ValueError(f"Invalid latitude: {latitude}")
    if not -180 <= longitude <= 180:
        raise ValueError(f"Invalid longitude: {longitude}")
    if precision < 1:
        raise ValueError("Geohash precision must be positive")

    latitude_interval = [-90.0, 90.0]
    longitude_interval = [-180.0, 180.0]
    encoded: list[str] = []
    bits = (16, 8, 4, 2, 1)
    bit_index = 0
    character = 0
    use_longitude = True

    while len(encoded) < precision:
        interval = longitude_interval if use_longitude else latitude_interval
        coordinate = longitude if use_longitude else latitude
        midpoint = (interval[0] + interval[1]) / 2
        if coordinate >= midpoint:
            character |= bits[bit_index]
            interval[0] = midpoint
        else:
            interval[1] = midpoint

        use_longitude = not use_longitude
        if bit_index < 4:
            bit_index += 1
            continue

        encoded.append(GEOHASH_ALPHABET[character])
        bit_index = 0
        character = 0

    return "".join(encoded)


def inverse_integer(value: int) -> str:
    if not 0 <= value <= MAX_SIGNED_64_BIT:
        raise ValueError(f"Value is outside the supported range: {value}")
    return f"{MAX_SIGNED_64_BIT - value:019d}"


def reverse_date(value: date) -> str:
    return f"{MAX_DATE_ORDINAL - value.toordinal():07d}"


def business_by_location_key(
    business_id: str,
    latitude: float,
    longitude: float,
    review_count: int,
) -> bytes:
    return _key(
        geohash(latitude, longitude),
        inverse_integer(review_count),
        business_id,
    )


def tip_by_business_key(
    business_id: str,
    tipped_at: date,
    tip_id: int,
) -> bytes:
    return _key(
        business_id,
        reverse_date(tipped_at),
        f"{tip_id:012d}",
    )


def review_by_business_key(
    business_id: str,
    stars: int,
    review_id: str,
) -> bytes:
    return _key(business_id, _inverse_stars(stars), review_id)


def personality_ranking_key(score_sum: int, user_id: str) -> bytes:
    return _key(inverse_integer(score_sum), user_id)


def review_by_user_key(
    user_id: str,
    reviewed_at: date,
    stars: int,
    review_id: str,
) -> bytes:
    return _key(
        user_id,
        reverse_date(reviewed_at),
        _inverse_stars(stars),
        review_id,
    )


def friend_by_user_key(user_id: str, friend_id: str) -> bytes:
    return _key(user_id, friend_id)


def check_by_business_key(business_id: str, checked_at: date) -> bytes:
    return _key(business_id, reverse_date(checked_at))


def _inverse_stars(stars: int) -> str:
    if not 1 <= stars <= 5:
        raise ValueError(f"Stars must be between 1 and 5: {stars}")
    return str(5 - stars)


def _key(*parts: str) -> bytes:
    if any(ROW_KEY_SEPARATOR in part for part in parts):
        raise ValueError(f"Row-key values cannot contain {ROW_KEY_SEPARATOR!r}")
    return ROW_KEY_SEPARATOR.join(parts).encode("utf-8")
