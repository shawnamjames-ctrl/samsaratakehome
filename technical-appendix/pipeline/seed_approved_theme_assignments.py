from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
THEMES = {
    "fleet_access_recovery": ("Fleet", lambda row: row["primary_customer_issue"] == "account_access_session"),
    "fleet_mobile_stability": ("Fleet", lambda row: row["primary_customer_issue"] == "reliability_performance" and row["primary_failure_mode"] in {"crash_or_forced_close", "slow_lag_loading", "blank_or_unavailable"}),
    "fleet_map_stability": ("Fleet", lambda row: row["primary_product_area"] == "gps_maps_asset_visibility" and row["primary_customer_issue"] == "reliability_performance"),
    "driver_hos_state_integrity": ("Driver", lambda row: row["primary_product_area"] == "hos_eld_compliance" and row["primary_failure_mode"] in {"incorrect_state_or_data", "false_alert_or_detection", "data_loss_or_reset", "sync_connectivity"}),
    "driver_workflow_friction": ("Driver", lambda row: row["primary_failure_mode"] == "workflow_friction"),
    "driver_app_stability": ("Driver", lambda row: row["primary_customer_issue"] == "reliability_performance" and row["primary_failure_mode"] in {"crash_or_forced_close", "slow_lag_loading", "blank_or_unavailable"}),
    "driver_safety_false_detection": ("Driver", lambda row: row["primary_product_area"] == "safety_events_ai_detection" and row["primary_failure_mode"] == "false_alert_or_detection"),
    "driver_control_and_simplification_requests": ("Driver", lambda row: row["primary_experience_signal"] == "feature_request" and bool(set(filter(None, (row["evidence_review_request_patterns"] or "").split("|"))) & {"restore_previous_behavior", "workflow_simplification", "customization_or_control", "visibility_or_status"})),
    "fleet_product_requests": ("Fleet", lambda row: row["primary_experience_signal"] == "feature_request" and bool(set(filter(None, (row["evidence_review_request_patterns"] or "").split("|"))))),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed a private monitoring database with the approved V3 theme assignments")
    parser.add_argument("--analysis-database", type=Path, default=ROOT.parent / "data" / "processed" / "reviews_v3.sqlite3")
    parser.add_argument("--monitoring-database", type=Path, default=ROOT / "data" / "processed" / "monitoring_reviews.sqlite3")
    return parser.parse_args()


def seed(analysis: sqlite3.Connection, monitoring: sqlite3.Connection) -> dict:
    monitoring.executescript((ROOT / "pipeline" / "src" / "review_monitor" / "schema.sql").read_text(encoding="utf-8"))
    analysis.row_factory = sqlite3.Row
    monitoring.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    monitoring_by_source = {(row["app_key"], row["source_review_id"]): row for row in monitoring.execute("SELECT review_key, app_key, source_review_id, content_hash FROM reviews")}
    seeded_reviews = seeded_links = missing = 0
    for row in analysis.execute("SELECT * FROM reliable_v3_analysis_base WHERE in_rolling_365d=1 ORDER BY review_key"):
        target = monitoring_by_source.get((row["app_key"], row["source_review_id"]))
        if not target:
            missing += 1
            continue
        matched = [theme_id for theme_id, (product, rule) in THEMES.items() if row["product"] == product and rule(row)]
        monitoring.execute(
            "INSERT OR REPLACE INTO monitoring_review_decisions VALUES (?,?,?,?,?,?,?,?)",
            (target["review_key"], target["content_hash"], "matched_existing" if matched else "confirmed_no_theme", 1.0, "approved_v3_seed", "evidence_checked_v3", 0, now),
        )
        seeded_reviews += 1
        for theme_id in matched:
            monitoring.execute(
                "INSERT OR REPLACE INTO monitoring_theme_assignments VALUES (?,?,?,?,?,?,?,?)",
                (target["review_key"], target["content_hash"], theme_id, "approved_seed", 1.0, "approved_v3_seed", "evidence_checked_v3", now),
            )
            seeded_links += 1
    monitoring.commit()
    return {"seeded_reviews": seeded_reviews, "seeded_theme_links": seeded_links, "analysis_reviews_missing_from_monitor": missing}


def main() -> None:
    args = parse_args()
    analysis = sqlite3.connect(args.analysis_database)
    monitoring = sqlite3.connect(args.monitoring_database)
    result = seed(analysis, monitoring)
    analysis.close(); monitoring.close()
    print({"gate": "PASS", **result})


if __name__ == "__main__":
    main()
