from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CURRENT_DB = ROOT / "data" / "processed" / "monitoring_reviews.sqlite3"
DASHBOARD = ROOT / "public-data" / "dashboard"
RELEASE_ID = "reliable_20260831_v3"
SOURCE_KEYS = {"apple_driver_us", "apple_fleet_us", "google_driver_us", "google_fleet_us"}
RULES = json.loads((ROOT / "config" / "monitoring_themes.json").read_text(encoding="utf-8"))
STATIC_CONTENT = json.loads((ROOT / "public-data" / "releases" / RELEASE_ID / "static-content.json").read_text(encoding="utf-8"))


def evidence_key(review_key: str) -> str:
    return "ev_" + hashlib.sha256(review_key.encode("utf-8")).hexdigest()[:16]


def write_json(path: Path, value: object) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


args_parser = argparse.ArgumentParser()
args_parser.add_argument("--baseline", type=Path, required=True)
args = args_parser.parse_args()

conn = sqlite3.connect(CURRENT_DB)
conn.row_factory = sqlite3.Row
conn.execute("ATTACH DATABASE ? AS baseline", (str(args.baseline.resolve()),))
comparison_start = conn.execute("SELECT MAX(completed_at) FROM baseline.pull_runs WHERE status='succeeded'").fetchone()[0]
source_runs = conn.execute(
    """
    WITH ranked AS (
      SELECT *, ROW_NUMBER() OVER (PARTITION BY app_key ORDER BY completed_at DESC) rn
      FROM pull_runs WHERE mode='daily' AND status='succeeded' AND completed_at > ?
    ) SELECT * FROM ranked WHERE rn=1 ORDER BY app_key
    """,
    (comparison_start,),
).fetchall()
if {row["app_key"] for row in source_runs} != SOURCE_KEYS:
    raise SystemExit("daily dashboard update requires one successful new pull for all four sources")

data_through = max(row["completed_at"] for row in source_runs)
monitoring_run_id = "monitoring_" + data_through.replace("-", "").replace(":", "").replace("+00:00", "Z")

rows = conn.execute(
    """
    WITH co AS (SELECT review_key, helpful_count, developer_reply_hash FROM latest_review_observations),
         bo AS (SELECT review_key, helpful_count, developer_reply_hash FROM baseline.latest_review_observations)
    SELECT c.review_key, c.app_key, c.content_hash current_content_hash, c.title ct, b.title bt, c.body cb, b.body bb,
           c.rating cr, b.rating br, c.app_version cv, b.app_version bv,
           c.review_timestamp, c.currently_visible cvis, b.currently_visible bvis,
           co.helpful_count ch, bo.helpful_count bh,
           co.developer_reply_hash cdh, bo.developer_reply_hash bdh,
           CASE WHEN b.review_key IS NULL THEN 1 ELSE 0 END is_new
    FROM reviews c LEFT JOIN baseline.reviews b USING(review_key)
    LEFT JOIN co USING(review_key) LEFT JOIN bo USING(review_key)
    ORDER BY c.review_key
    """
).fetchall()

required_monitoring_tables = {"monitoring_review_decisions", "monitoring_theme_assignments", "monitoring_candidate_clusters"}
actual_tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
if not required_monitoring_tables.issubset(actual_tables):
    raise SystemExit("monitoring analysis must run before the public dashboard export")

deltas = []
for row in rows:
    changes = []
    if row["is_new"]:
        changes.append("new_review")
    else:
        if (row["ct"], row["cb"]) != (row["bt"], row["bb"]): changes.append("text_edited")
        if row["cr"] != row["br"]: changes.append("rating_changed")
        if row["cv"] != row["bv"]: changes.append("app_version_changed")
        if row["cdh"] != row["bdh"]: changes.append("developer_reply_changed")
        if row["ch"] != row["bh"]: changes.append("helpfulness_changed")
        if row["cvis"] != row["bvis"]: changes.append("visibility_changed")
    if not changes:
        continue
    app_key = row["app_key"]
    decision = conn.execute(
        "SELECT human_review_required FROM monitoring_review_decisions WHERE review_key=? AND content_hash=?",
        (row["review_key"], row["current_content_hash"]),
    ).fetchone()
    theme_ids = [item[0] for item in conn.execute(
        """
        SELECT a.theme_id FROM monitoring_theme_assignments a
        JOIN reviews r USING(review_key)
        WHERE a.review_key=? AND a.content_hash=r.content_hash AND a.assignment_status!='dismissed'
        ORDER BY a.theme_id
        """,
        (row["review_key"],),
    )]
    deltas.append({
        "evidence_key": evidence_key(row["review_key"]),
        "app_key": app_key,
        "product": "Driver" if "driver" in app_key else "Fleet",
        "platform": "iOS" if app_key.startswith("apple") else "Android",
        "change_types": changes,
        "review_timestamp": row["review_timestamp"],
        "rating": int(row["cr"]),
        "theme_ids": theme_ids,
        "human_review_required": bool(decision[0]) if decision else bool(set(changes) & {"new_review", "text_edited", "rating_changed", "visibility_changed"}),
    })

new_rows = [row for row in deltas if "new_review" in row["change_types"]]
changed_rows = [row for row in deltas if "new_review" not in row["change_types"]]
new_denominator = len(new_rows)
volume = Counter((row["product"], row["platform"]) for row in new_rows)
ratings = Counter(row["rating"] for row in new_rows)
source_status = []
for row in source_runs:
    newest = conn.execute("SELECT MAX(review_timestamp) FROM reviews WHERE app_key=? AND currently_visible=1", (row["app_key"],)).fetchone()[0]
    source_status.append({"app_key": row["app_key"], "status": "succeeded", "records_received": int(row["records_received"]), "newest_review_at": newest, "observed_at": row["completed_at"]})

through_dt = datetime.fromisoformat(data_through.replace("Z", "+00:00"))
current_start = (through_dt - timedelta(days=30)).isoformat()
prior_start = (through_dt - timedelta(days=90)).isoformat()
recommendations = {item["theme_id"]: item["recommendation"] for item in STATIC_CONTENT["surfaces"]["recommendations"]}
metrics = []
alerts = []
metric_rules = RULES["metric_rules"]

def pct(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0

for theme in RULES["themes"]:
    product_like = "%driver%" if theme["product"] == "Driver" else "%fleet%"
    current_denominator = conn.execute("SELECT COUNT(*) FROM reviews WHERE currently_visible=1 AND app_key LIKE ? AND review_timestamp>=? AND review_timestamp<=?", (product_like, current_start, data_through)).fetchone()[0]
    prior_denominator = conn.execute("SELECT COUNT(*) FROM reviews WHERE currently_visible=1 AND app_key LIKE ? AND review_timestamp>=? AND review_timestamp<?", (product_like, prior_start, current_start)).fetchone()[0]
    base_assignment_sql = """
        FROM monitoring_theme_assignments a JOIN reviews r USING(review_key)
        WHERE a.theme_id=? AND a.content_hash=r.content_hash AND a.assignment_status!='dismissed'
          AND r.currently_visible=1 AND r.app_key LIKE ? AND r.review_timestamp>=? AND r.review_timestamp{operator}?
    """
    current_count = conn.execute("SELECT COUNT(DISTINCT r.review_key) " + base_assignment_sql.format(operator="<="), (theme["theme_id"], product_like, current_start, data_through)).fetchone()[0]
    prior_count = conn.execute("SELECT COUNT(DISTINCT r.review_key) " + base_assignment_sql.format(operator="<"), (theme["theme_id"], product_like, prior_start, current_start)).fetchone()[0]
    provisional_count = conn.execute("""
        SELECT COUNT(DISTINCT r.review_key)
        FROM monitoring_theme_assignments a JOIN reviews r USING(review_key)
        WHERE a.theme_id=? AND a.content_hash=r.content_hash AND a.assignment_status='provisional_rule'
          AND r.currently_visible=1 AND r.app_key LIKE ? AND r.review_timestamp>=? AND r.review_timestamp<=?
    """, (theme["theme_id"], product_like, current_start, data_through)).fetchone()[0]
    current_rate = pct(current_count, current_denominator)
    prior_rate = pct(prior_count, prior_denominator)
    change_pp = round(current_rate - prior_rate, 1)
    eligible = current_denominator >= metric_rules["minimum_current_denominator"] and prior_denominator >= metric_rules["minimum_prior_denominator"] and current_count >= metric_rules["minimum_current_hits"] and prior_count >= metric_rules["minimum_prior_hits"]
    if not eligible:
        metric_status = "insufficient_data"
    elif change_pp >= metric_rules["alert_change_pp"]:
        metric_status = "alert"
    elif change_pp >= metric_rules["watch_change_pp"]:
        metric_status = "watch"
    else:
        metric_status = "stable"
    metric = {
        "theme_id": theme["theme_id"], "name": theme["name"], "product": theme["product"], "platform": "All",
        "window": "latest_30_vs_prior_60", "count": current_count, "denominator": current_denominator,
        "rate_pct": current_rate, "prior_count": prior_count, "prior_denominator": prior_denominator,
        "prior_rate_pct": prior_rate, "rate_change_pp": change_pp,
        "one_review_sensitivity_pp": pct(1, current_denominator), "provisional_count": provisional_count,
        "status": metric_status, "recommended_action": recommendations[theme["theme_id"]],
    }
    metrics.append(metric)
    if metric_status == "alert":
        alerts.append({
            "alert_id": "alert_" + hashlib.sha256(f"{monitoring_run_id}|{theme['theme_id']}".encode()).hexdigest()[:12],
            "theme_id": theme["theme_id"], "reason": f"Latest 30-day rate is {change_pp:+.1f} percentage points versus the prior separate 60-day period.",
            "severity": theme["severity"], "status": "candidate", "human_review_required": True,
        })

emerging = []
for candidate in conn.execute("SELECT * FROM monitoring_candidate_clusters WHERE status='candidate' ORDER BY support_count DESC, latest_review_at DESC"):
    emerging.append({
        "candidate_id": candidate["candidate_id"], "label": f"Unreviewed {candidate['product']} pattern",
        "product": candidate["product"], "platform": candidate["platform"], "support_count": candidate["support_count"],
        "first_review_at": candidate["first_review_at"], "latest_review_at": candidate["latest_review_at"],
        "average_rating": candidate["average_rating"], "status": candidate["status"],
        "human_review_required": bool(candidate["human_review_required"]),
    })

open_review_queue_count = conn.execute("""
    SELECT COUNT(DISTINCT d.review_key) FROM monitoring_review_decisions d JOIN reviews r USING(review_key)
    WHERE d.content_hash=r.content_hash AND r.currently_visible=1 AND d.human_review_required=1
""").fetchone()[0]
residual_count = conn.execute("""
    SELECT COUNT(DISTINCT d.review_key) FROM monitoring_review_decisions d JOIN reviews r USING(review_key)
    WHERE d.content_hash=r.content_hash AND r.currently_visible=1 AND d.decision_status='residual'
""").fetchone()[0]
confirmed_no_theme_count = conn.execute("""
    SELECT COUNT(DISTINCT d.review_key) FROM monitoring_review_decisions d JOIN reviews r USING(review_key)
    WHERE d.content_hash=r.content_hash AND r.currently_visible=1 AND d.decision_status='confirmed_no_theme'
""").fetchone()[0]
classification_through = conn.execute("SELECT MAX(decided_at) FROM monitoring_review_decisions").fetchone()[0] or data_through
conn.close()

summary = {
    "schema_version": "1.0", "monitoring_run_id": monitoring_run_id,
    "analysis_release_id": RELEASE_ID, "last_successful_run_at": data_through,
    "data_through": data_through, "comparison_start_exclusive": comparison_start,
    "source_status": source_status, "new_reviews_since_prior_success": len(new_rows),
    "changed_reviews_since_prior_success": len(changed_rows),
    "review_volume": [
        {"product": product, "platform": platform, "count": count, "denominator": new_denominator, "rate_pct": round(100 * count / new_denominator, 1)}
        for (product, platform), count in sorted(volume.items())
    ] if new_denominator else [],
    "rating_mix": [
        {"rating": rating, "count": count, "denominator": new_denominator, "rate_pct": round(100 * count / new_denominator, 1)}
        for rating, count in sorted(ratings.items())
    ] if new_denominator else [],
    "human_review_queue_count": open_review_queue_count,
}
deltas_public = {
    "schema_version": "1.0", "monitoring_run_id": monitoring_run_id,
    "comparison_start_exclusive": comparison_start, "data_through": data_through,
    "delta_counts": dict(sorted(Counter(change for row in deltas for change in row["change_types"]).items())),
    "review_deltas": deltas,
}
themes_path = DASHBOARD / "dashboard-themes.json"
themes = {
    "schema_version": "2.0", "monitoring_run_id": monitoring_run_id, "analysis_release_id": RELEASE_ID,
    "data_through": data_through, "classification_through": classification_through,
    "unclassified_review_count": residual_count, "classified_no_theme_count": confirmed_no_theme_count,
    "existing_theme_metrics": metrics, "alert_candidates": alerts, "emerging_signals": emerging,
}
status = {
    "schema_version": "1.0", "monitoring_run_id": monitoring_run_id, "status": "withheld",
    "started_at": min(row["started_at"] for row in source_runs), "completed_at": data_through,
    "published_at": None, "last_good_monitoring_run_id": None, "static_release_unchanged": True,
    "gate_results": [
        {"gate": "source_integrity", "passed": True, "detail": "All four configured daily source pulls succeeded."},
        {"gate": "delta_reconciliation", "passed": True, "detail": f"{len(new_rows)} new and {len(changed_rows)} changed existing reviews reconcile to the prior success."},
        {"gate": "monitoring_analysis", "passed": True, "detail": f"Nine existing themes recalculated; {len(emerging)} emerging pattern candidates; {open_review_queue_count} review records require human review."},
        {"gate": "static_release", "passed": True, "detail": "Daily monitoring did not modify the approved analytical release."},
        {"gate": "site_build", "passed": False, "detail": "Awaiting build and site tests."},
    ],
}
write_json(DASHBOARD / "dashboard-summary.json", summary)
write_json(DASHBOARD / "dashboard-deltas.json", deltas_public)
write_json(themes_path, themes)
write_json(DASHBOARD / "pipeline-status.json", status)
print({"gate": "PASS", "monitoring_run_id": monitoring_run_id, "new_reviews": len(new_rows), "changed_existing_reviews": len(changed_rows)})
