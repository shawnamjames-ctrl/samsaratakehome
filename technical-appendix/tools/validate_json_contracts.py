from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
FIXTURES = ROOT / "tests" / "fixtures" / "contracts"

PAIRS = {
    "static-content": (SCHEMAS / "static-content.schema.json", FIXTURES / "static-content.json"),
    "dashboard-summary": (SCHEMAS / "dashboard-summary.schema.json", FIXTURES / "dashboard-summary.json"),
    "dashboard-themes": (SCHEMAS / "dashboard-themes.schema.json", FIXTURES / "dashboard-themes.json"),
    "dashboard-deltas": (SCHEMAS / "dashboard-deltas.schema.json", FIXTURES / "dashboard-deltas.json"),
    "pipeline-status": (SCHEMAS / "pipeline-status.schema.json", FIXTURES / "pipeline-status.json"),
    "release-manifest": (SCHEMAS / "release-manifest.schema.json", FIXTURES / "release-manifest.json"),
    "theme-evidence": (SCHEMAS / "theme-evidence.schema.json", FIXTURES / "theme-evidence.json"),
    "further-recommendations": (SCHEMAS / "further-recommendations.schema.json", FIXTURES / "further-recommendations.json"),
    "methodology-process": (SCHEMAS / "methodology-process.schema.json", FIXTURES / "methodology-process.json"),
}


def matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    raise ValueError(f"unsupported schema type: {expected}")


def validate(value: Any, schema: dict[str, Any], path: str, failures: list[str]) -> None:
    expected = schema.get("type")
    if expected:
        expected_types = expected if isinstance(expected, list) else [expected]
        if not any(matches_type(value, item) for item in expected_types):
            failures.append(f"{path}: expected {expected_types}, received {type(value).__name__}")
            return
    if "const" in schema and value != schema["const"]:
        failures.append(f"{path}: expected constant {schema['const']!r}, received {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        failures.append(f"{path}: {value!r} not in {schema['enum']}")
    if isinstance(value, (int, float)) and "minimum" in schema and value < schema["minimum"]:
        failures.append(f"{path}: {value} below minimum {schema['minimum']}")
    if isinstance(value, str) and "pattern" in schema and not re.fullmatch(schema["pattern"], value):
        failures.append(f"{path}: value does not match {schema['pattern']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            failures.append(f"{path}: has {len(value)} items; minimum is {schema['minItems']}")
        if "items" in schema:
            for index, item in enumerate(value):
                validate(item, schema["items"], f"{path}[{index}]", failures)
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            if required not in value:
                failures.append(f"{path}: missing required property {required}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    failures.append(f"{path}: unexpected property {key}")
        for key, child_schema in properties.items():
            if key in value:
                validate(value[key], child_schema, f"{path}.{key}", failures)


failures: list[str] = []
for name, (schema_path, fixture_path) in PAIRS.items():
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    validate(fixture, schema, name, failures)

if failures:
    raise SystemExit("JSON contract validation FAIL\n- " + "\n- ".join(failures))

print({"gate": "PASS", "schemas": len(PAIRS), "fixtures": len(PAIRS), "validation_errors": 0})
