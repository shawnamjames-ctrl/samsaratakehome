from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .config import ProjectConfig, SourceConfig
from .util import stable_hash


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(connection: sqlite3.Connection, config: ProjectConfig) -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    connection.executescript(schema_path.read_text(encoding="utf-8"))
    for source in config.sources:
        connection.execute(
            """
            INSERT INTO apps (
                app_key, app_name, source_platform, store_app_id,
                territory, requested_language, source_url, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(app_key) DO UPDATE SET
                app_name = excluded.app_name,
                source_platform = excluded.source_platform,
                store_app_id = excluded.store_app_id,
                territory = excluded.territory,
                requested_language = excluded.requested_language,
                source_url = excluded.source_url,
                active = 1
            """,
            (
                source.app_key,
                source.app_name,
                source.source_platform,
                source.store_app_id,
                source.territory,
                source.requested_language,
                source.source_url,
            ),
        )
    connection.commit()


def start_pull(
    connection: sqlite3.Connection,
    run_id: str,
    source: SourceConfig,
    mode: str,
    started_at: str,
    request_parameters: dict[str, Any],
    parser_version: str,
) -> None:
    connection.execute(
        """
        INSERT INTO pull_runs (
            run_id, app_key, mode, started_at, status,
            request_parameters, parser_version
        ) VALUES (?, ?, ?, ?, 'running', ?, ?)
        """,
        (run_id, source.app_key, mode, started_at, json.dumps(request_parameters), parser_version),
    )
    connection.commit()


def fail_pull(
    connection: sqlite3.Connection,
    run_id: str,
    completed_at: str,
    error: str,
    raw_snapshot_path: str | None = None,
) -> None:
    connection.execute(
        """
        UPDATE pull_runs
        SET completed_at = ?, status = 'failed', error_message = ?,
            raw_snapshot_path = COALESCE(?, raw_snapshot_path)
        WHERE run_id = ?
        """,
        (completed_at, error, raw_snapshot_path, run_id),
    )
    connection.commit()


def store_collection(
    connection: sqlite3.Connection,
    run_id: str,
    source: SourceConfig,
    observed_at: str,
    raw_snapshot_path: str,
    collection: dict[str, Any],
    full_snapshot: bool = False,
) -> dict[str, int]:
    reviews = collection["reviews"]
    seen_ids: set[str] = set()
    inserted = 0
    updated = 0

    with connection:
        previously_visible: dict[str, sqlite3.Row] = {}
        if full_snapshot:
            previously_visible = {
                row["source_review_id"]: row
                for row in connection.execute(
                    """
                    SELECT review_key, source_review_id, rating, content_hash
                    FROM reviews WHERE app_key = ? AND currently_visible = 1
                    """,
                    (source.app_key,),
                ).fetchall()
            }
            connection.execute(
                "UPDATE reviews SET currently_visible = 0 WHERE app_key = ?",
                (source.app_key,),
            )
        for review in reviews:
            source_review_id = str(review["source_review_id"])
            seen_ids.add(source_review_id)
            review_key = f"{source.app_key}:{source_review_id}"
            content_hash = stable_hash(
                review.get("title"), review.get("body"), review.get("rating"), review.get("app_version")
            )
            exists = connection.execute(
                "SELECT 1 FROM reviews WHERE review_key = ?", (review_key,)
            ).fetchone()
            connection.execute(
                """
                INSERT INTO reviews (
                    review_key, app_key, source_platform, store_app_id,
                    territory, requested_language, source_review_id, source_url,
                    reviewer_display_name, title, body, rating, review_timestamp,
                    app_version, first_seen_at, last_seen_at, content_hash, currently_visible
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(review_key) DO UPDATE SET
                    source_url = excluded.source_url,
                    reviewer_display_name = excluded.reviewer_display_name,
                    title = excluded.title,
                    body = excluded.body,
                    rating = excluded.rating,
                    review_timestamp = excluded.review_timestamp,
                    app_version = excluded.app_version,
                    last_seen_at = excluded.last_seen_at,
                    content_hash = excluded.content_hash,
                    currently_visible = 1
                """,
                (
                    review_key,
                    source.app_key,
                    source.source_platform,
                    source.store_app_id,
                    source.territory,
                    source.requested_language,
                    source_review_id,
                    review.get("source_url"),
                    review.get("reviewer_display_name"),
                    review.get("title"),
                    review.get("body") or "",
                    int(review["rating"]),
                    review["review_timestamp"],
                    review.get("app_version"),
                    observed_at,
                    observed_at,
                    content_hash,
                ),
            )
            if exists:
                updated += 1
            else:
                inserted += 1

            reply_text = review.get("developer_reply_text")
            reply_hash = stable_hash(reply_text) if reply_text else None
            connection.execute(
                """
                INSERT OR REPLACE INTO review_observations (
                    review_key, observed_at, rating, content_hash, helpful_count,
                    legacy_vote_count, legacy_vote_sum, developer_reply_present,
                    developer_reply_hash, developer_reply_timestamp, currently_visible
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    review_key,
                    observed_at,
                    int(review["rating"]),
                    content_hash,
                    review.get("helpful_count"),
                    review.get("legacy_vote_count"),
                    review.get("legacy_vote_sum"),
                    1 if reply_text else 0,
                    reply_hash,
                    review.get("developer_reply_timestamp"),
                ),
            )
            if reply_text:
                connection.execute(
                    """
                    INSERT INTO developer_responses (
                        review_key, response_hash, response_text, response_timestamp,
                        first_seen_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(review_key, response_hash) DO UPDATE SET
                        response_timestamp = excluded.response_timestamp,
                        last_seen_at = excluded.last_seen_at
                    """,
                    (
                        review_key,
                        reply_hash,
                        reply_text,
                        review.get("developer_reply_timestamp"),
                        observed_at,
                        observed_at,
                    ),
                )

        if full_snapshot:
            for source_review_id, prior in previously_visible.items():
                if source_review_id in seen_ids:
                    continue
                connection.execute(
                    """
                    INSERT OR REPLACE INTO review_observations (
                        review_key, observed_at, rating, content_hash, helpful_count,
                        legacy_vote_count, legacy_vote_sum, developer_reply_present,
                        developer_reply_hash, developer_reply_timestamp, currently_visible
                    ) VALUES (?, ?, ?, ?, NULL, NULL, NULL, 0, NULL, NULL, 0)
                    """,
                    (
                        prior["review_key"],
                        observed_at,
                        prior["rating"],
                        prior["content_hash"],
                    ),
                )

        metadata = collection["metadata"]
        histogram = metadata.get("rating_histogram") or {}
        connection.execute(
            """
            INSERT OR REPLACE INTO app_snapshots (
                app_key, observed_at, average_rating, ratings_count,
                written_reviews_count, rating_1_count, rating_2_count,
                rating_3_count, rating_4_count, rating_5_count,
                current_version, store_updated_at, minimum_os,
                install_min, install_max, app_size_bytes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source.app_key,
                observed_at,
                metadata.get("average_rating"),
                metadata.get("ratings_count"),
                metadata.get("written_reviews_count"),
                histogram.get("1"),
                histogram.get("2"),
                histogram.get("3"),
                histogram.get("4"),
                histogram.get("5"),
                metadata.get("current_version"),
                metadata.get("store_updated_at"),
                metadata.get("minimum_os"),
                metadata.get("install_min"),
                metadata.get("install_max"),
                metadata.get("app_size_bytes"),
            ),
        )
        version = metadata.get("current_version")
        if version:
            connection.execute(
                """
                INSERT INTO releases (
                    app_key, version, release_timestamp, release_notes,
                    first_seen_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(app_key, version) DO UPDATE SET
                    release_timestamp = excluded.release_timestamp,
                    release_notes = excluded.release_notes,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    source.app_key,
                    version,
                    metadata.get("store_updated_at"),
                    metadata.get("release_notes"),
                    observed_at,
                    observed_at,
                ),
            )
        connection.execute(
            """
            UPDATE pull_runs
            SET completed_at = ?, status = 'succeeded', raw_snapshot_path = ?,
                records_received = ?, request_parameters = ?
            WHERE run_id = ?
            """,
            (
                observed_at,
                raw_snapshot_path,
                len(reviews),
                json.dumps(collection.get("request", {}), sort_keys=True),
                run_id,
            ),
        )
    return {
        "inserted": inserted,
        "updated": updated,
        "received": len(reviews),
        "no_longer_endpoint_visible": len(set(previously_visible) - seen_ids) if full_snapshot else 0,
    }


def counts_by_source(connection: sqlite3.Connection) -> Iterable[sqlite3.Row]:
    return connection.execute(
        """
        SELECT
            a.app_key,
            a.app_name,
            a.source_platform,
            COUNT(r.review_key) AS review_count,
            MIN(r.review_timestamp) AS oldest_review,
            MAX(r.review_timestamp) AS newest_review,
            SUM(CASE WHEN r.app_version IS NOT NULL AND r.app_version <> '' THEN 1 ELSE 0 END) AS with_version,
            SUM(CASE WHEN dr.review_key IS NOT NULL THEN 1 ELSE 0 END) AS with_reply
        FROM apps AS a
        LEFT JOIN reviews AS r USING (app_key)
        LEFT JOIN (
            SELECT DISTINCT review_key FROM developer_responses
        ) AS dr USING (review_key)
        GROUP BY a.app_key, a.app_name, a.source_platform
        ORDER BY a.app_key
        """
    ).fetchall()
