from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = {
    "data/raw",
    "data/processed",
    "data/exports",
    "private-data",
    "audit-private",
    "review-text-private",
}
FORBIDDEN_SUFFIXES = {".sqlite", ".sqlite3", ".db", ".env"}
SECRET_PATTERNS = {
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "generic secret assignment": re.compile(
        r"(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*['\"][^'\"]{8,}"
    ),
}


def candidate_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line]


failures: list[str] = []
files = candidate_files()
for path in files:
    relative = path.relative_to(ROOT).as_posix()
    lowered = relative.lower()
    if any(part in lowered for part in FORBIDDEN_PARTS):
        failures.append(f"forbidden private path: {relative}")
    if path.suffix.lower() in FORBIDDEN_SUFFIXES or path.name.startswith(".env") and path.name != ".env.example":
        failures.append(f"forbidden private file type: {relative}")
    if not path.is_file() or path.stat().st_size > 2_000_000:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            failures.append(f"possible {name} in {relative}")

if failures:
    raise SystemExit("Public repository boundary FAIL\n- " + "\n- ".join(sorted(set(failures))))

print({"gate": "PASS", "candidate_files_scanned": len(files), "private_paths_found": 0, "secret_patterns_found": 0})
