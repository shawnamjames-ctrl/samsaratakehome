from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Move private monitoring state without exposing it to Git")
    result.add_argument("action", choices=("pull-db", "push-db", "pull-published-db", "push-published-db", "push-raw"))
    result.add_argument("--database", type=Path, default=Path("data/processed/monitoring_reviews.sqlite3"))
    result.add_argument("--raw-directory", type=Path, default=Path("data/monitoring/raw"))
    return result


def local_copy(action: str, database: Path, raw_directory: Path, state_root: Path) -> None:
    state_db = state_root / ("published_monitoring_reviews.sqlite3" if "published" in action else "monitoring_reviews.sqlite3")
    if action in {"pull-db", "pull-published-db"}:
        if not state_db.exists():
            raise FileNotFoundError(f"private monitoring seed is missing: {state_db}")
        database.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(state_db, database)
    elif action in {"push-db", "push-published-db"}:
        state_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(database, state_db)
    else:
        destination_root = state_root / "raw"
        for source in raw_directory.rglob("*.json"):
            destination = destination_root / source.relative_to(raw_directory)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copy2(source, destination)


def s3_copy(action: str, database: Path, raw_directory: Path, bucket: str, prefix: str) -> None:
    import boto3

    client = boto3.client("s3", endpoint_url=os.environ.get("AWS_ENDPOINT_URL") or None)
    state_name = "published_monitoring_reviews.sqlite3" if "published" in action else "monitoring_reviews.sqlite3"
    db_key = f"{prefix.rstrip('/')}/{state_name}"
    if action in {"pull-db", "pull-published-db"}:
        database.parent.mkdir(parents=True, exist_ok=True)
        client.download_file(bucket, db_key, str(database))
    elif action in {"push-db", "push-published-db"}:
        client.upload_file(str(database), bucket, db_key)
    else:
        for source in raw_directory.rglob("*.json"):
            key = f"{prefix.rstrip('/')}/raw/{source.relative_to(raw_directory).as_posix()}"
            client.upload_file(str(source), bucket, key)


def main() -> None:
    args = parser().parse_args()
    backend = os.environ.get("STATE_BACKEND", "local")
    if backend == "local":
        state_root = Path(os.environ.get("LOCAL_STATE_DIR", ".private-state"))
        local_copy(args.action, args.database, args.raw_directory, state_root)
    elif backend == "s3":
        bucket = os.environ["PRIVATE_STATE_BUCKET"]
        prefix = os.environ.get("PRIVATE_STATE_PREFIX", "samsara-review-monitor")
        s3_copy(args.action, args.database, args.raw_directory, bucket, prefix)
    else:
        raise ValueError(f"unsupported STATE_BACKEND: {backend}")
    print({"gate": "PASS", "action": args.action, "backend": backend})


if __name__ == "__main__":
    main()
