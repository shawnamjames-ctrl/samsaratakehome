from __future__ import annotations

import sqlite3
from typing import Any


EXPECTED_BASELINE = {
    "apple_driver_us": 500,
    "apple_fleet_us": 200,
    "google_driver_us": 4000,
    "google_fleet_us": 200,
}


def validate(connection: sqlite3.Connection) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    duplicates = connection.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT app_key, source_review_id, COUNT(*) AS n
            FROM reviews GROUP BY app_key, source_review_id HAVING n > 1
        )
        """
    ).fetchone()[0]
    check("stable_id_deduplication", duplicates == 0, f"duplicate groups: {duplicates}")

    invalid_rows = connection.execute(
        """
        SELECT COUNT(*) FROM reviews
        WHERE body = '' OR review_timestamp IS NULL OR rating NOT BETWEEN 1 AND 5
           OR source_platform NOT IN ('apple_app_store', 'google_play')
        """
    ).fetchone()[0]
    check("required_review_fields", invalid_rows == 0, f"invalid rows: {invalid_rows}")

    missing_provenance = connection.execute(
        """
        SELECT COUNT(*) FROM reviews
        WHERE app_key IS NULL OR source_platform IS NULL OR store_app_id IS NULL
           OR territory IS NULL OR requested_language IS NULL OR source_review_id IS NULL
        """
    ).fetchone()[0]
    check("source_provenance", missing_provenance == 0, f"rows missing provenance: {missing_provenance}")

    for app_key, expected_minimum in EXPECTED_BASELINE.items():
        actual = connection.execute(
            "SELECT COUNT(*) FROM reviews WHERE app_key = ?", (app_key,)
        ).fetchone()[0]
        check(
            f"minimum_count_{app_key}",
            actual >= expected_minimum,
            f"actual {actual}; expected at least {expected_minimum}",
        )

    successful_pulls = connection.execute(
        "SELECT COUNT(*) FROM pull_runs WHERE status = 'succeeded'"
    ).fetchone()[0]
    check("successful_pull_audit", successful_pulls >= 4, f"successful pulls: {successful_pulls}")

    orphan_observations = connection.execute(
        """
        SELECT COUNT(*) FROM review_observations AS o
        LEFT JOIN reviews AS r USING (review_key)
        WHERE r.review_key IS NULL
        """
    ).fetchone()[0]
    check("observation_referential_integrity", orphan_observations == 0, f"orphans: {orphan_observations}")

    return {
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
    }
