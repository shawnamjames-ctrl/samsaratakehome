from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceConfig:
    app_key: str
    app_name: str
    source_platform: str
    store_app_id: str
    territory: str
    requested_language: str
    source_url: str
    options: dict[str, Any]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SourceConfig":
        required = {
            "app_key",
            "app_name",
            "source_platform",
            "store_app_id",
            "territory",
            "requested_language",
            "source_url",
        }
        missing = required - value.keys()
        if missing:
            raise ValueError(f"Source is missing required fields: {sorted(missing)}")
        if value["source_platform"] not in {"apple_app_store", "google_play"}:
            raise ValueError(f"Unsupported source platform: {value['source_platform']}")
        return cls(
            app_key=value["app_key"],
            app_name=value["app_name"],
            source_platform=value["source_platform"],
            store_app_id=str(value["store_app_id"]),
            territory=value["territory"].lower(),
            requested_language=value["requested_language"].lower(),
            source_url=value["source_url"],
            options={key: item for key, item in value.items() if key not in required},
        )


@dataclass(frozen=True)
class ProjectConfig:
    project_root: Path
    database_path: Path
    raw_directory: Path
    sources: tuple[SourceConfig, ...]


def load_config(path: Path) -> ProjectConfig:
    path = path.resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    project_root = path.parent.parent
    sources = tuple(SourceConfig.from_dict(item) for item in payload["sources"])
    app_keys = [source.app_key for source in sources]
    if len(app_keys) != len(set(app_keys)):
        raise ValueError("Each app_key must be unique")
    return ProjectConfig(
        project_root=project_root,
        database_path=project_root / payload["database_path"],
        raw_directory=project_root / payload["raw_directory"],
        sources=sources,
    )
