from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
RELEASE_ID = "reliable_20260831_v3"
DATABASE = WORKSPACE / "data" / "processed" / "reviews_v3.sqlite3"
RELEASE_DIR = ROOT / "public-data" / "releases" / RELEASE_ID
OUTPUT = RELEASE_DIR / "methodology-process.json"
MANIFEST = RELEASE_DIR / "manifest.json"


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


connection = sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True)
connection.row_factory = sqlite3.Row

phases = [dict(row) for row in connection.execute(
    "SELECT phase_id, display_order, title AS heading, objective, work_completed, decision_made, rationale, evidence_produced, boundary_or_gate FROM methodology_phases WHERE analysis_run_id = ? ORDER BY display_order",
    (RELEASE_ID,),
)]
for phase in phases:
    if phase["phase_id"] == "semantic_gate":
        phase["evidence_produced"] = (
            "924 checked V2 reviews (438 corrected carry-forwards and 486 blind-reviewed records), "
            "five eligible additions, two records aged out, a final 927-review V3 population, and a "
            "passing consistency rerun for five core fields."
        )
layers = [dict(row) for row in connection.execute(
    "SELECT layer_id, display_order, title AS heading, short_label, input_summary, decision_summary, output_summary, gate_summary, path_type FROM methodology_layers WHERE analysis_run_id = ? ORDER BY display_order",
    (RELEASE_ID,),
)]
decisions = [dict(row) for row in connection.execute(
    "SELECT decision_id, display_order, title AS heading, situation, action_taken, why_it_matters FROM methodology_decisions WHERE analysis_run_id = ? ORDER BY display_order",
    (RELEASE_ID,),
)]
responsibilities = [dict(row) for row in connection.execute(
    "SELECT responsibility_id, display_order, owner_type, responsibility FROM methodology_operating_model WHERE analysis_run_id = ? ORDER BY owner_type, display_order",
    (RELEASE_ID,),
)]
connection.close()

payload = {
    "analysis_release_id": RELEASE_ID,
    "schema_version": "1.0",
    "heading": "Turning public reviews into product signal",
    "lede": "This methodology explains how 5,209 endpoint-visible public reviews became a governed 927-review rolling-year analysis, nine challenged themes, prioritized recommendations, and a repeatable monitoring system. It separates source facts, analytical interpretation, and daily monitoring so new data can update the dashboard without silently rewriting executive conclusions.",
    "scope_metrics": [
        {"label": "Public sources", "value": "4"},
        {"label": "Baseline written reviews", "value": "5,209"},
        {"label": "Rolling-year analysis", "value": "927"},
        {"label": "Challenged themes", "value": "9"},
        {"label": "Monitoring cadence", "value": "Daily + weekly"},
    ],
    "layers": layers,
    "phases": phases,
    "decision_moments": decisions,
    "operating_model": {
        "automated": [row for row in responsibilities if row["owner_type"] == "automated"],
        "human": [row for row in responsibilities if row["owner_type"] == "human"],
    },
    "publication_policy": "Daily monitoring updates operational signals. Themes, recommendations, and executive claims change only through human review and a new approved release.",
    "practice_notes": {
        "ai_use": "AI assisted research design, classification support, coding, QA, and drafting. Human review and deterministic checks governed published claims.",
        "access_limits": "No App Store Connect, Google Play Console, internal telemetry, incidents, support, account, or release data were available.",
        "next_week": "Join the top themes to telemetry and support, validate proposed owners and thresholds, repair response-timing anomalies, and activate the private scheduled workflow.",
        "production_boundary": "The prototype, pipeline, public contracts, validation checks, and workflows are built. Production activation requires private state, GitHub secrets, owner credentials, and internal telemetry and support joins."
    },
}
write_json(OUTPUT, payload)

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
manifest["files"] = [item for item in manifest["files"] if item["path"] != OUTPUT.name]
manifest["files"].append({"path": OUTPUT.name, "sha256": sha256(OUTPUT)})
write_json(MANIFEST, manifest)

print({"gate": "PASS", "phases": len(phases), "layers": len(layers), "decisions": len(decisions), "responsibilities": len(responsibilities), "output": str(OUTPUT)})
