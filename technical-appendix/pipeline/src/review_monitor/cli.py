from __future__ import annotations

import argparse
import json
import sys
import traceback
import uuid
from pathlib import Path

from . import __version__
from .apple import collect as collect_apple
from .config import ProjectConfig, SourceConfig, load_config
from .database import connect, counts_by_source, fail_pull, initialize, start_pull, store_collection
from .google import collect as collect_google
from .util import utc_now, write_json_atomic
from .validation import validate


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Ingest and monitor public Samsara app reviews")
    result.add_argument(
        "--config",
        type=Path,
        default=Path("config/sources.json"),
        help="Path to source configuration",
    )
    subparsers = result.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init", help="Initialize the database schema")
    for command in ("backfill", "daily", "reconcile"):
        child = subparsers.add_parser(command, help=f"Run {command} extraction")
        child.add_argument("--app-key", action="append", help="Limit extraction to an app key")
    subparsers.add_parser("validate", help="Run automated data-quality checks")
    subparsers.add_parser("status", help="Show source counts and coverage")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    config = load_config(args.config)
    connection = connect(config.database_path)
    initialize(connection, config)

    if args.command == "init":
        print(f"Initialized {config.database_path}")
        return 0
    if args.command == "status":
        print_status(connection)
        return 0
    if args.command == "validate":
        result = validate(connection)
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1
    if args.command in {"backfill", "daily", "reconcile"}:
        selected = set(args.app_key or [])
        sources = [source for source in config.sources if not selected or source.app_key in selected]
        unknown = selected - {source.app_key for source in config.sources}
        if unknown:
            raise ValueError(f"Unknown app keys: {sorted(unknown)}")
        failures = run_extraction(connection, config, sources, args.command)
        print_status(connection)
        return 1 if failures else 0
    return 2


def run_extraction(
    connection,
    config: ProjectConfig,
    sources: list[SourceConfig],
    mode: str,
) -> int:
    failures = 0
    effective_mode = "reconcile" if mode == "reconcile" else mode
    for source in sources:
        started_at = utc_now()
        run_id = str(uuid.uuid4())
        start_pull(
            connection,
            run_id,
            source,
            effective_mode,
            started_at,
            {"source": source.source_platform, "mode": effective_mode},
            __version__,
        )
        raw_path_relative = None
        try:
            collector = collect_apple if source.source_platform == "apple_app_store" else collect_google
            collection = collector(source, "backfill" if effective_mode == "reconcile" else effective_mode)
            timestamp_slug = started_at.replace(":", "-")
            raw_path = (
                config.raw_directory
                / source.source_platform
                / source.app_key
                / f"{timestamp_slug}_{effective_mode}.json"
            )
            raw_payload = {
                "run_id": run_id,
                "app_key": source.app_key,
                "source_platform": source.source_platform,
                "store_app_id": source.store_app_id,
                "territory": source.territory,
                "requested_language": source.requested_language,
                "extracted_at": started_at,
                "parser_version": __version__,
                "collector_payload": collection["raw"],
            }
            write_json_atomic(raw_path, raw_payload)
            raw_path_relative = str(raw_path.relative_to(config.project_root))
            assert_collection_sane(source, effective_mode, collection)
            completed_at = utc_now()
            result = store_collection(
                connection,
                run_id,
                source,
                completed_at,
                raw_path_relative,
                collection,
                full_snapshot=effective_mode in {"backfill", "reconcile"},
            )
            print(f"{source.app_key}: {result}")
        except Exception as error:
            failures += 1
            fail_pull(
                connection,
                run_id,
                utc_now(),
                f"{type(error).__name__}: {error}",
                raw_path_relative,
            )
            print(f"{source.app_key}: FAILED: {error}", file=sys.stderr)
            traceback.print_exc()
    return failures


def assert_collection_sane(
    source: SourceConfig,
    mode: str,
    collection: dict,
) -> None:
    count = len(collection.get("reviews", []))
    if count == 0:
        raise ValueError("Collector returned zero reviews; refusing to replace last good state")
    if mode in {"backfill", "reconcile"}:
        minimum = int(source.options.get("minimum_full_reviews", 1))
        if count < minimum:
            raise ValueError(
                f"Collector returned {count} reviews, below configured full-pull minimum {minimum}"
            )


def print_status(connection) -> None:
    print("app_key\tplatform\treviews\twith_version\twith_reply\toldest\tnewest")
    for row in counts_by_source(connection):
        print(
            "\t".join(
                str(row[key] if row[key] is not None else "")
                for key in (
                    "app_key",
                    "source_platform",
                    "review_count",
                    "with_version",
                    "with_reply",
                    "oldest_review",
                    "newest_review",
                )
            )
        )
