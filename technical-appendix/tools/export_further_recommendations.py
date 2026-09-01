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
OUTPUT = RELEASE_DIR / "further-recommendations.json"
MANIFEST = RELEASE_DIR / "manifest.json"


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


connection = sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True)
connection.row_factory = sqlite3.Row

recommendation_rows = connection.execute(
    """
    SELECT *
    FROM further_recommendations
    WHERE analysis_run_id = ?
      AND publication_status = 'approved_for_analysis_section'
    ORDER BY display_order, recommendation_id
    """,
    (RELEASE_ID,),
).fetchall()

recommendations = []
for row in recommendation_rows:
    evidence_rows = connection.execute(
        """
        SELECT evidence_id, evidence_class, metric_label, metric_value, context, display_order
        FROM further_recommendation_evidence
        WHERE analysis_run_id = ? AND recommendation_id = ?
        ORDER BY display_order, evidence_id
        """,
        (RELEASE_ID, row["recommendation_id"]),
    ).fetchall()
    recommendations.append(
        {
            "additional_data_needed": row["additional_data_needed"],
            "decision_boundary": row["decision_boundary"],
            "display_order": row["display_order"],
            "evidence": [dict(item) for item in evidence_rows],
            "evidence_status": {
                "code": row["evidence_status_code"],
                "label": row["evidence_status_label"],
            },
            "evidence_summary": row["evidence_summary"],
            "rationale": row["rationale"],
            "recommendation_id": row["recommendation_id"],
            "recommended_action": row["recommended_action"],
            "recommendation_name": row["title"],
        }
    )

connection.close()

payload = {
    "analysis_release_id": RELEASE_ID,
    "publication_policy": "Human-approved recommendations linked to the analytical release. Daily monitoring does not rewrite this file.",
    "recommendation_count": len(recommendations),
    "recommendations": recommendations,
    "schema_version": "1.0",
}
write_json(OUTPUT, payload)

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
manifest["files"] = [item for item in manifest["files"] if item["path"] != OUTPUT.name]
manifest["files"].append({"path": OUTPUT.name, "sha256": sha256(OUTPUT)})
write_json(MANIFEST, manifest)

print(
    {
        "gate": "PASS",
        "analysis_release_id": RELEASE_ID,
        "recommendations": len(recommendations),
        "evidence_records": sum(len(item["evidence"]) for item in recommendations),
        "output": str(OUTPUT),
    }
)
