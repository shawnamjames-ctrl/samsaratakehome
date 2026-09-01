from __future__ import annotations

import json
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
namespace = runpy.run_path(str(ROOT / "tools" / "validate_json_contracts.py"))
validate = namespace["validate"]

release_id = "reliable_20260831_v3"
release_dir = ROOT / "public-data" / "releases" / release_id
dashboard_dir = ROOT / "public-data" / "dashboard"
pairs = {
    "static-content": (ROOT / "schemas" / "static-content.schema.json", release_dir / "static-content.json"),
    "release-manifest": (ROOT / "schemas" / "release-manifest.schema.json", release_dir / "manifest.json"),
    "dashboard-summary": (ROOT / "schemas" / "dashboard-summary.schema.json", dashboard_dir / "dashboard-summary.json"),
    "dashboard-themes": (ROOT / "schemas" / "dashboard-themes.schema.json", dashboard_dir / "dashboard-themes.json"),
    "dashboard-deltas": (ROOT / "schemas" / "dashboard-deltas.schema.json", dashboard_dir / "dashboard-deltas.json"),
    "pipeline-status": (ROOT / "schemas" / "pipeline-status.schema.json", dashboard_dir / "pipeline-status.json"),
    "theme-evidence": (ROOT / "schemas" / "theme-evidence.schema.json", release_dir / "theme-evidence.json"),
    "further-recommendations": (ROOT / "schemas" / "further-recommendations.schema.json", release_dir / "further-recommendations.json"),
    "methodology-process": (ROOT / "schemas" / "methodology-process.schema.json", release_dir / "methodology-process.json"),
}

failures: list[str] = []
for name, (schema_path, output_path) in pairs.items():
    if not output_path.exists():
        failures.append(f"{name}: missing output {output_path}")
        continue
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    output = json.loads(output_path.read_text(encoding="utf-8"))
    validate(output, schema, name, failures)

if failures:
    raise SystemExit("Public output validation FAIL\n- " + "\n- ".join(failures))

print({"gate": "PASS", "public_outputs": len(pairs), "validation_errors": 0})
