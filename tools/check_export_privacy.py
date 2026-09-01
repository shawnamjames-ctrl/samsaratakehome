from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA = ROOT / "public-data"
FORBIDDEN_KEYS = {
    "review_key",
    "source_review_id",
    "reviewer_display_name",
    "reviewer_name",
    "body",
    "title",
    "response_text",
    "raw_payload",
    "database_path",
    "private_storage_location",
}
SENSITIVE_PATTERNS = {
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "phone": re.compile(r"(?<!\d)(?:\+?1[ .-]?)?(?:\(?\d{3}\)?[ .-]?)\d{3}[ .-]?\d{4}(?!\d)"),
}


def walk(value: Any, path: str, failures: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_KEYS:
                failures.append(f"forbidden key {key!r} at {path}")
            walk(child, f"{path}.{key}", failures)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk(child, f"{path}[{index}]", failures)
    elif isinstance(value, str):
        # Cryptographic digests are machine identifiers, not human contact data.
        # Exempt only an explicitly named SHA-256 field with the exact digest shape.
        if path.endswith("sha256") and re.fullmatch(r"[a-f0-9]{64}", value):
            return
        for name, pattern in SENSITIVE_PATTERNS.items():
            if pattern.search(value):
                failures.append(f"possible {name} at {path}")

def scan_directory(public_data: Path, root: Path | None = None) -> tuple[list[Path], list[str]]:
    root = root or public_data.parent
    failures: list[str] = []
    json_files = sorted(public_data.rglob("*.json"))
    for file in json_files:
        walk(json.loads(file.read_text(encoding="utf-8")), file.relative_to(root).as_posix(), failures)
    return json_files, failures


def main() -> None:
    json_files, failures = scan_directory(PUBLIC_DATA, ROOT)
    if failures:
        raise SystemExit("Public export privacy gate FAIL\n- " + "\n- ".join(failures))
    print({"gate": "PASS", "json_files_scanned": len(json_files), "forbidden_keys": 0, "sensitive_patterns": 0})


if __name__ == "__main__":
    main()
