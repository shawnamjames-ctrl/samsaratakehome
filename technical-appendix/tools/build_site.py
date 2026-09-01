from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site-src"
DOCS = ROOT / "docs"
PUBLIC_DATA = ROOT / "public-data"
DELIVERABLES = ROOT.parent / "deliverables"

DOCS.mkdir(parents=True, exist_ok=True)
for name in ("index.html", "styles.css", "app.js"):
    shutil.copy2(SOURCE / name, DOCS / name)
(DOCS / ".nojekyll").write_text("", encoding="utf-8")

for source_path in sorted(PUBLIC_DATA.rglob("*.json")):
    relative = source_path.relative_to(PUBLIC_DATA)
    destination = DOCS / "data" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination)

for source_path in sorted(DELIVERABLES.glob("*.pdf")):
    destination = DOCS / "downloads" / source_path.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination)

print({
    "gate": "PASS",
    "site_files": 4,
    "data_files": len(list(PUBLIC_DATA.rglob("*.json"))),
    "download_files": len(list(DELIVERABLES.glob("*.pdf"))),
    "output": str(DOCS),
})
