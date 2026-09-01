from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import SourceConfig
from .util import normalize_iso_timestamp


USER_AGENT = "SamsaraTakeHomeReviewMonitor/0.1 (+public research prototype)"


def _label(value: Any, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get("label", default)
    return default


def _fetch_json(url: str, attempts: int = 3) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError):
            if attempt + 1 == attempts:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("unreachable")


def collect(source: SourceConfig, mode: str) -> dict[str, Any]:
    lookup_url = (
        f"https://itunes.apple.com/lookup?id={source.store_app_id}"
        f"&country={source.territory}"
    )
    metadata_payload = _fetch_json(lookup_url)
    results = metadata_payload.get("results", [])
    if len(results) != 1:
        raise ValueError(f"Apple lookup expected one result, received {len(results)}")
    metadata_raw = results[0]

    page_limit_key = "daily_page_limit" if mode == "daily" else "backfill_page_limit"
    page_limit = int(source.options.get(page_limit_key, 10))
    page_payloads: list[dict[str, Any]] = []
    normalized_reviews: list[dict[str, Any]] = []

    for page in range(1, page_limit + 1):
        url = (
            f"https://itunes.apple.com/{source.territory}/rss/customerreviews/"
            f"page={page}/id={source.store_app_id}/sortby=mostrecent/json"
        )
        payload = _fetch_json(url)
        page_payloads.append({"page": page, "url": url, "payload": payload})
        entries = payload.get("feed", {}).get("entry", [])
        if isinstance(entries, dict):
            entries = [entries]
        reviews = [entry for entry in entries if isinstance(entry, dict) and "im:rating" in entry]
        if not reviews:
            break
        for entry in reviews:
            author = entry.get("author", {})
            link = entry.get("link", {}).get("attributes", {})
            normalized_reviews.append(
                {
                    "source_review_id": str(_label(entry.get("id"), "")),
                    "source_url": link.get("href"),
                    "reviewer_display_name": _label(author.get("name")),
                    "title": _label(entry.get("title")),
                    "body": _label(entry.get("content"), ""),
                    "rating": int(_label(entry.get("im:rating"))),
                    "review_timestamp": normalize_iso_timestamp(_label(entry.get("updated"))),
                    "app_version": _label(entry.get("im:version")),
                    "helpful_count": None,
                    "legacy_vote_count": int(_label(entry.get("im:voteCount"), 0) or 0),
                    "legacy_vote_sum": int(_label(entry.get("im:voteSum"), 0) or 0),
                    "developer_reply_text": None,
                    "developer_reply_timestamp": None,
                }
            )

    metadata = {
        "average_rating": metadata_raw.get("averageUserRating"),
        "ratings_count": metadata_raw.get("userRatingCount"),
        "written_reviews_count": None,
        "rating_histogram": {},
        "current_version": metadata_raw.get("version"),
        "store_updated_at": normalize_iso_timestamp(metadata_raw.get("currentVersionReleaseDate")),
        "minimum_os": metadata_raw.get("minimumOsVersion"),
        "install_min": None,
        "install_max": None,
        "app_size_bytes": _optional_int(metadata_raw.get("fileSizeBytes")),
        "release_notes": metadata_raw.get("releaseNotes"),
    }
    return {
        "request": {"lookup_url": lookup_url, "page_limit": page_limit, "mode": mode},
        "raw": {"metadata": metadata_payload, "review_pages": page_payloads},
        "metadata": metadata,
        "reviews": normalized_reviews,
    }


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)
