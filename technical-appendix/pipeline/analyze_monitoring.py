from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "processed" / "monitoring_reviews.sqlite3"
DEFAULT_RULES = ROOT / "config" / "monitoring_themes.json"
SCHEMA = ROOT / "pipeline" / "src" / "review_monitor" / "schema.sql"
STOPWORDS = {"about","after","again","also","and","app","are","because","been","before","but","can","could","does","for","from","have","into","its","just","more","not","now","only","our","out","really","review","samsara","that","the","their","them","then","there","they","this","too","very","was","were","what","when","with","would","you","your"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify monitored reviews against frozen themes and build a residual-signal queue")
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--data-through")
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def product_for(app_key: str) -> str:
    return "Driver" if "driver" in app_key else "Fleet"


def platform_for(app_key: str) -> str:
    return "iOS" if app_key.startswith("apple") else "Android"


def is_request(text: str) -> bool:
    return any(term in text for term in ("please add", "bring back", "should add", "need an option", "wish", "feature request", "let me", "would like"))


def match_themes(text: str, product: str, rules: dict) -> list[dict]:
    normalized = " ".join(text.lower().split())
    matches = []
    for theme in rules["themes"]:
        if theme["product"] != product:
            continue
        if theme.get("request_required") and not is_request(normalized):
            continue
        hits = [term for term in theme["terms"] if term in normalized]
        if hits:
            matches.append({"theme_id": theme["theme_id"], "confidence": min(.95, .68 + .08 * len(hits)), "matched_terms": len(hits)})
    return matches


def residual_signature(text: str) -> str:
    tokens = [token for token in re.findall(r"[a-z]{4,}", text.lower()) if token not in STOPWORDS]
    counts = Counter(tokens)
    return "|".join(token for token, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:2])


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA.read_text(encoding="utf-8"))


def analyze(connection: sqlite3.Connection, rules: dict, data_through: str) -> dict:
    initialize(connection)
    decided_at = utc_now()
    rows = connection.execute(
        """
        SELECT review_key, app_key, title, body, rating, review_timestamp, content_hash
        FROM reviews WHERE currently_visible=1
        ORDER BY review_timestamp, review_key
        """
    ).fetchall()
    processed = matched = residual = 0
    for row in rows:
        existing = connection.execute(
            "SELECT 1 FROM monitoring_review_decisions WHERE review_key=? AND content_hash=?",
            (row["review_key"], row["content_hash"]),
        ).fetchone()
        if existing:
            continue
        processed += 1
        product = product_for(row["app_key"])
        text = f"{row['title'] or ''} {row['body']}"
        theme_matches = match_themes(text, product, rules)
        if theme_matches:
            matched += 1
            confidence = max(item["confidence"] for item in theme_matches)
            connection.execute(
                "INSERT INTO monitoring_review_decisions VALUES (?,?,?,?,?,?,?,?)",
                (row["review_key"], row["content_hash"], "matched_existing", confidence, "frozen_keyword_rules", rules["classifier_version"], 1 if confidence < .85 else 0, decided_at),
            )
            for item in theme_matches:
                connection.execute(
                    "INSERT INTO monitoring_theme_assignments VALUES (?,?,?,?,?,?,?,?)",
                    (row["review_key"], row["content_hash"], item["theme_id"], "provisional_rule", item["confidence"], "frozen_keyword_rules", rules["classifier_version"], decided_at),
                )
        else:
            residual += 1
            connection.execute(
                "INSERT INTO monitoring_review_decisions VALUES (?,?,?,?,?,?,?,?)",
                (row["review_key"], row["content_hash"], "residual", .5, "residual_queue", rules["classifier_version"], 1, decided_at),
            )

    connection.execute("DELETE FROM monitoring_candidate_clusters WHERE status='candidate'")
    cutoff = (datetime.fromisoformat(data_through.replace("Z", "+00:00")) - timedelta(days=30)).isoformat()
    residual_rows = connection.execute(
        """
        SELECT r.review_key, r.app_key, r.title, r.body, r.rating, r.review_timestamp
        FROM reviews r JOIN monitoring_review_decisions d USING(review_key)
        WHERE r.currently_visible=1 AND d.content_hash=r.content_hash
          AND d.decision_status='residual' AND r.review_timestamp>=?
        ORDER BY r.review_timestamp, r.review_key
        """,
        (cutoff,),
    ).fetchall()
    clusters = defaultdict(list)
    for row in residual_rows:
        signature = residual_signature(f"{row['title'] or ''} {row['body']}")
        if signature:
            clusters[(product_for(row["app_key"]), signature)].append(row)
    candidate_count = 0
    for (product, signature), members in clusters.items():
        if len(members) < rules["candidate_minimum_support"]:
            continue
        candidate_count += 1
        platforms = {platform_for(row["app_key"]) for row in members}
        platform = next(iter(platforms)) if len(platforms) == 1 else "All"
        digest = hashlib.sha256(f"{product}|{signature}".encode()).hexdigest()
        connection.execute(
            "INSERT INTO monitoring_candidate_clusters VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("candidate_" + digest[:12], product, platform, hashlib.sha256(signature.encode()).hexdigest(), len(members), min(row["review_timestamp"] for row in members), max(row["review_timestamp"] for row in members), round(sum(row["rating"] for row in members) / len(members), 1), "candidate", 1, decided_at),
        )
    connection.commit()
    return {"processed": processed, "matched_existing": matched, "residual": residual, "candidate_clusters": candidate_count, "data_through": data_through}


def main() -> None:
    args = parse_args()
    rules = json.loads(args.rules.read_text(encoding="utf-8"))
    connection = sqlite3.connect(args.database)
    connection.row_factory = sqlite3.Row
    data_through = args.data_through or connection.execute("SELECT MAX(completed_at) FROM pull_runs WHERE status='succeeded'").fetchone()[0]
    if not data_through:
        raise ValueError("monitoring analysis requires at least one successful pull")
    result = analyze(connection, rules, data_through)
    connection.close()
    print({"gate": "PASS", **result})


if __name__ == "__main__":
    main()
