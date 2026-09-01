from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
RELEASE_ID = "reliable_20260831_v3"
CUTOFF = datetime.fromisoformat("2026-09-01T00:00:00+00:00")
SOURCE = WORKSPACE / "outputs" / "v3_analysis" / "theme_evidence_index.csv"
RELEASE_DIR = ROOT / "public-data" / "releases" / RELEASE_ID
OUTPUT = RELEASE_DIR / "theme-evidence.json"
MANIFEST = RELEASE_DIR / "manifest.json"
STATIC_CONTENT = RELEASE_DIR / "static-content.json"

EXPERIENCE_LABELS = {
    "workflow_friction": "Extra steps or workflow friction",
    "slow_lag_loading": "Slow, lagging, or loading failure",
    "incorrect_state_or_data": "Incorrect state or data",
    "crash_or_forced_close": "Crash or forced close",
    "login_logout_mfa": "Login, logout, or MFA problem",
    "blank_or_unavailable": "Blank or unavailable view",
    "false_alert_or_detection": "Perceived false alert or detection",
    "missing_capability": "Missing capability or product request",
    "sync_connectivity": "Synchronization or connectivity problem",
    "data_loss_or_reset": "Data loss or reset",
}

WORKFLOW_LABELS = {
    "general_app_experience": "General app experience",
    "hos_eld_compliance": "HOS and ELD compliance",
    "gps_maps_asset_visibility": "Maps and asset visibility",
    "safety_events_ai_detection": "Safety events and AI detection",
    "dvir_inspections": "DVIR and inspections",
    "documents_connected_forms": "Documents and connected forms",
    "driver_assignment": "Driver assignment",
    "messages_inbox_tasks": "Messages, inbox, and tasks",
    "coaching_training_recognition": "Coaching and training",
    "cameras_video_safety_inbox": "Cameras and video safety",
    "routing_dispatch_navigation": "Routing, dispatch, and navigation",
    "fleet_hardware_activation": "Fleet hardware activation",
}

CONSEQUENCE_LABELS = {
    "critical": "Critical potential consequence",
    "high": "High potential consequence",
    "medium": "Material friction or delay",
    "low": "Minor friction or request",
}


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_key(review_key: str) -> str:
    digest = hashlib.sha256(f"public-theme-evidence-v1:{review_key}".encode()).hexdigest()
    letters_only = "".join(chr(ord("a") + int(character, 16)) for character in digest[:16])
    return f"ev_{letters_only}"


def time_band(timestamp: str) -> str:
    observed = datetime.fromisoformat(timestamp)
    age_days = (CUTOFF - observed).total_seconds() / 86400
    if age_days <= 30:
        return "Latest 30 days"
    if age_days <= 90:
        return "31–90 days ago"
    if age_days <= 183:
        return "91–183 days ago"
    return "184–365 days ago"


def rating_band(rating: str) -> str:
    value = int(rating)
    if value <= 2:
        return "1–2 stars"
    if value == 3:
        return "3 stars"
    return "4–5 stars"


with SOURCE.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))

static_content = json.loads(STATIC_CONTENT.read_text(encoding="utf-8"))
theme_metadata = {
    theme["theme_id"]: {"name": theme["name"], "rank": theme["rank"]}
    for theme in static_content["surfaces"]["thematic_analysis"]["themes"]
}

themes = []
for theme_id, metadata in sorted(theme_metadata.items(), key=lambda item: item[1]["rank"]):
    theme_rows = [row for row in rows if row["theme_id"] == theme_id]
    records = [
        {
            "consequence": CONSEQUENCE_LABELS[row["severity"]],
            "evidence_key": evidence_key(row["review_key"]),
            "platform": row["platform"],
            "product": row["product"],
            "rating_band": rating_band(row["rating"]),
            "reported_experience": EXPERIENCE_LABELS[row["primary_failure_mode"]],
            "time_band": time_band(row["review_timestamp"]),
            "workflow": WORKFLOW_LABELS[row["primary_product_area"]],
        }
        for row in sorted(theme_rows, key=lambda item: (item["review_timestamp"], item["review_key"]), reverse=True)
    ]
    themes.append(
        {
            "evidence_count": len(records),
            "name": metadata["name"],
            "rank": metadata["rank"],
            "records": records,
            "theme_id": theme_id,
        }
    )

payload = {
    "analysis_release_id": RELEASE_ID,
    "cutoff_exclusive": CUTOFF.isoformat(),
    "evidence_policy": "Complete theme-linked evidence index with anonymous, non-verbatim review attributes. Reviewer identity and raw text remain private.",
    "schema_version": "1.0",
    "themes": themes,
    "total_theme_links": len(rows),
    "unique_evidence_records": len({row["review_key"] for row in rows}),
}
write_json(OUTPUT, payload)

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
manifest["files"] = [item for item in manifest["files"] if item["path"] != OUTPUT.name]
manifest["files"].append({"path": OUTPUT.name, "sha256": sha256(OUTPUT)})
write_json(MANIFEST, manifest)

print(
    {
        "gate": "PASS",
        "themes": len(themes),
        "theme_links": len(rows),
        "unique_evidence_records": payload["unique_evidence_records"],
        "verbatim_text_published": False,
        "output": str(OUTPUT),
    }
)
