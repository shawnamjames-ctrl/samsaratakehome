from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipeline" / "src"))

from pipeline.state_store import local_copy
from review_monitor.cli import assert_collection_sane
from review_monitor.config import SourceConfig
from tools.check_export_privacy import scan_directory
from tools.mark_publishable import mark_publishable
from pipeline.analyze_monitoring import analyze


class FailureBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="samsara-pipeline-test-")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def source(self, minimum: int = 2) -> SourceConfig:
        return SourceConfig(
            app_key="test_app",
            app_name="Test",
            source_platform="apple_app_store",
            store_app_id="1",
            territory="us",
            requested_language="en",
            source_url="https://example.invalid",
            options={"minimum_full_reviews": minimum},
        )

    def test_empty_collection_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "zero reviews"):
            assert_collection_sane(self.source(), "daily", {"reviews": []})

    def test_truncated_reconciliation_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "below configured full-pull minimum"):
            assert_collection_sane(self.source(minimum=3), "reconcile", {"reviews": [{}, {}]})

    def test_missing_private_seed_fails_closed(self) -> None:
        with self.assertRaises(FileNotFoundError):
            local_copy("pull-db", self.root / "database.sqlite3", self.root / "raw", self.root / "state")

    def test_local_private_state_round_trip_is_exact(self) -> None:
        source = self.root / "source.sqlite3"
        source.write_bytes(b"deterministic-private-state")
        state = self.root / "state"
        restored = self.root / "restored.sqlite3"
        local_copy("push-db", source, self.root / "raw", state)
        local_copy("pull-db", restored, self.root / "raw", state)
        self.assertEqual(source.read_bytes(), restored.read_bytes())

    def test_operational_and_published_state_are_independent(self) -> None:
        state = self.root / "state"
        operational = self.root / "operational.sqlite3"
        published = self.root / "published.sqlite3"
        operational.write_bytes(b"weekly-reconciled-state")
        published.write_bytes(b"last-public-state")
        local_copy("push-db", operational, self.root / "raw", state)
        local_copy("push-published-db", published, self.root / "raw", state)
        restored_operational = self.root / "restored-operational.sqlite3"
        restored_published = self.root / "restored-published.sqlite3"
        local_copy("pull-db", restored_operational, self.root / "raw", state)
        local_copy("pull-published-db", restored_published, self.root / "raw", state)
        self.assertEqual(restored_operational.read_bytes(), b"weekly-reconciled-state")
        self.assertEqual(restored_published.read_bytes(), b"last-public-state")

    def test_failed_gate_cannot_be_marked_publishable(self) -> None:
        status = self.root / "pipeline-status.json"
        status.write_text(json.dumps({
            "monitoring_run_id": "test-run",
            "status": "withheld",
            "published_at": None,
            "last_good_monitoring_run_id": None,
            "gate_results": [
                {"gate": "source_integrity", "passed": False},
                {"gate": "site_build", "passed": False},
            ],
        }), encoding="utf-8")
        before = status.read_bytes()
        with self.assertRaisesRegex(ValueError, "gate is failing"):
            mark_publishable(status)
        self.assertEqual(before, status.read_bytes(), "failed publication must not rewrite status")

    def test_successful_gates_can_be_marked_publishable(self) -> None:
        status = self.root / "pipeline-status.json"
        status.write_text(json.dumps({
            "monitoring_run_id": "test-run",
            "status": "withheld",
            "published_at": None,
            "last_good_monitoring_run_id": None,
            "gate_results": [
                {"gate": "source_integrity", "passed": True},
                {"gate": "site_build", "passed": False},
            ],
        }), encoding="utf-8")
        result = mark_publishable(status)
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["last_good_monitoring_run_id"], "test-run")
        self.assertTrue(all(gate["passed"] for gate in result["gate_results"]))

    def test_privacy_gate_detects_identity_and_contact_data(self) -> None:
        public = self.root / "public-data"
        public.mkdir()
        (public / "bad.json").write_text(json.dumps({
            "reviewer_display_name": "Person",
            "note": "contact test@example.com",
        }), encoding="utf-8")
        _, failures = scan_directory(public, self.root)
        self.assertTrue(any("forbidden key" in failure for failure in failures))
        self.assertTrue(any("possible email" in failure for failure in failures))

    def test_privacy_gate_does_not_treat_sha256_as_a_phone(self) -> None:
        public = self.root / "public-data"
        public.mkdir()
        (public / "manifest.json").write_text(json.dumps({
            "sha256": "123456789012345678901234567890abcdefabcdefabcdefabcdefabcdefabcd",
        }), encoding="utf-8")
        _, failures = scan_directory(public, self.root)
        self.assertEqual(failures, [])

    def test_current_public_export_stays_privacy_clean(self) -> None:
        _, failures = scan_directory(ROOT / "public-data", ROOT)
        self.assertEqual(failures, [])

    def test_monitoring_analysis_routes_existing_and_residual_signals(self) -> None:
        database = self.root / "monitor.sqlite3"
        connection = __import__("sqlite3").connect(database)
        connection.row_factory = __import__("sqlite3").Row
        connection.executescript((ROOT / "pipeline" / "src" / "review_monitor" / "schema.sql").read_text(encoding="utf-8"))
        connection.execute("INSERT INTO apps(app_key,app_name,source_platform,store_app_id,territory,requested_language,source_url) VALUES ('google_driver_us','Driver','google_play','driver','us','en','https://example.invalid')")
        reviews = [
            ("r1", "The app crashes and freezes during my route", 1),
            ("r2", "Bluetooth scanner pairing, bluetooth scanner disconnects", 2),
            ("r3", "Bluetooth scanner pairing, bluetooth scanner fails", 1),
        ]
        for key, body, rating in reviews:
            connection.execute("INSERT INTO reviews(review_key,app_key,source_platform,store_app_id,territory,requested_language,source_review_id,body,rating,review_timestamp,first_seen_at,last_seen_at,content_hash,currently_visible) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1)", (key,"google_driver_us","google_play","driver","us","en",key,body,rating,"2026-08-30T12:00:00+00:00","2026-08-30T12:00:00+00:00","2026-08-30T12:00:00+00:00","hash-"+key))
        rules = json.loads((ROOT / "config" / "monitoring_themes.json").read_text(encoding="utf-8"))
        result = analyze(connection, rules, "2026-08-31T23:40:07+00:00")
        self.assertEqual(result["matched_existing"], 1)
        self.assertEqual(result["residual"], 2)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM monitoring_theme_assignments WHERE theme_id='driver_app_stability'").fetchone()[0], 1)
        self.assertEqual(connection.execute("SELECT COUNT(*) FROM monitoring_candidate_clusters").fetchone()[0], 1)
        connection.close()


if __name__ == "__main__":
    unittest.main()
