from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from .config import SourceConfig


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        # google-play-scraper currently returns naive datetimes created in the
        # host timezone. astimezone() interprets them correctly before UTC conversion.
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def collect(source: SourceConfig, mode: str) -> dict[str, Any]:
    try:
        from google_play_scraper import Sort, app, reviews
    except ImportError as error:
        raise RuntimeError(
            "google-play-scraper is required. Install dependencies from requirements.txt."
        ) from error

    metadata_raw = app(
        source.store_app_id,
        lang=source.requested_language,
        country=source.territory,
    )
    limit_key = "daily_review_limit" if mode == "daily" else "backfill_review_limit"
    review_limit = int(source.options.get(limit_key, 50000))
    token = None
    review_payloads: list[dict[str, Any]] = []
    unique: dict[str, dict[str, Any]] = {}

    while len(unique) < review_limit:
        requested = min(4500, review_limit - len(unique))
        batch, token = reviews(
            source.store_app_id,
            lang=source.requested_language,
            country=source.territory,
            sort=Sort.NEWEST,
            count=requested,
            continuation_token=token,
        )
        review_payloads.append(
            {
                "batch_number": len(review_payloads) + 1,
                "records": batch,
                "has_continuation_token": bool(getattr(token, "token", None)),
            }
        )
        for item in batch:
            review_id = str(item.get("reviewId", ""))
            if review_id:
                unique[review_id] = item
        if not getattr(token, "token", None) or not batch:
            break

    normalized_reviews: list[dict[str, Any]] = []
    for item in unique.values():
        review_id = str(item.get("reviewId"))
        normalized_reviews.append(
            {
                "source_review_id": review_id,
                "source_url": (
                    f"https://play.google.com/store/apps/details?id={source.store_app_id}"
                    f"&reviewId={quote(review_id, safe='')}"
                ),
                "reviewer_display_name": item.get("userName"),
                "title": None,
                "body": item.get("content") or "",
                "rating": int(item.get("score")),
                "review_timestamp": _iso(item.get("at")),
                "app_version": item.get("reviewCreatedVersion") or item.get("appVersion"),
                "helpful_count": _optional_int(item.get("thumbsUpCount")),
                "legacy_vote_count": None,
                "legacy_vote_sum": None,
                "developer_reply_text": item.get("replyContent"),
                "developer_reply_timestamp": _iso(item.get("repliedAt")),
            }
        )

    histogram_raw = metadata_raw.get("histogram") or []
    if isinstance(histogram_raw, list):
        histogram = {
            str(index): value for index, value in enumerate(histogram_raw, start=1)
        }
    else:
        histogram = {str(key): value for key, value in histogram_raw.items()}
    metadata = {
        "average_rating": metadata_raw.get("score"),
        "ratings_count": metadata_raw.get("ratings"),
        "written_reviews_count": metadata_raw.get("reviews"),
        "rating_histogram": histogram,
        "current_version": metadata_raw.get("version"),
        "store_updated_at": _epoch_ms_iso(metadata_raw.get("updated")),
        "minimum_os": metadata_raw.get("androidVersionText"),
        "install_min": _optional_int(metadata_raw.get("minInstalls")),
        "install_max": _optional_int(metadata_raw.get("maxInstalls")),
        "app_size_bytes": None,
        "release_notes": metadata_raw.get("recentChanges"),
    }
    return {
        "request": {
            "mode": mode,
            "review_limit": review_limit,
            "sort": "newest",
            "batches": len(review_payloads),
            "pagination_exhausted": not bool(getattr(token, "token", None)),
        },
        "raw": {"metadata": metadata_raw, "review_batches": review_payloads},
        "metadata": metadata,
        "reviews": normalized_reviews,
    }


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _epoch_ms_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _iso(value)
    numeric = int(value)
    # google-play-scraper currently exposes this field in epoch seconds, while
    # older variants exposed milliseconds. Accept both to prevent 1970 dates.
    seconds = numeric / 1000 if numeric > 10_000_000_000 else numeric
    return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()
