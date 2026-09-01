from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
failures: list[str] = []

required_files = [
    DOCS / "index.html",
    DOCS / "styles.css",
    DOCS / "app.js",
    DOCS / ".nojekyll",
    DOCS / "data" / "dashboard" / "dashboard-summary.json",
    DOCS / "data" / "dashboard" / "dashboard-deltas.json",
    DOCS / "data" / "dashboard" / "dashboard-themes.json",
    DOCS / "data" / "dashboard" / "pipeline-status.json",
    DOCS / "data" / "releases" / "reliable_20260831_v3" / "platform-comparison.json",
    DOCS / "data" / "releases" / "reliable_20260831_v3" / "theme-evidence.json",
    DOCS / "data" / "releases" / "reliable_20260831_v3" / "further-recommendations.json",
    DOCS / "data" / "releases" / "reliable_20260831_v3" / "methodology-process.json",
    DOCS / "downloads" / "Samsara_CPO_Memo.pdf",
    DOCS / "downloads" / "Samsara_Methodology_Note.pdf",
]
for path in required_files:
    if not path.exists():
        failures.append(f"missing built site file: {path.relative_to(ROOT)}")

html = (DOCS / "index.html").read_text(encoding="utf-8")
js = (DOCS / "app.js").read_text(encoding="utf-8")
css = (DOCS / "styles.css").read_text(encoding="utf-8")
for path in (candidate for candidate in DOCS.rglob("*") if candidate.suffix in {".html", ".css", ".js", ".json", ".md"}):
    if "—" in path.read_text(encoding="utf-8"):
        failures.append(f"dashboard contains an em dash: {path.relative_to(ROOT)}")
for required in (
    "What changed, and what deserves attention?",
    "themes need attention",
    "new reviews found",
    "awaiting analyst review",
    "Which established customer problems are changing?",
    "What does not fit the existing themes?",
    'id="monitor-theme-table"',
    'id="monitor-theme-detail"',
    'id="emerging-signal-grid"',
    "Change ledger",
    "Source freshness",
    "EXECUTIVE OVERVIEW",
    "THE EXECUTIVE SIGNAL",
    "Stabilize Fleet. Protect Driver HOS integrity. Tighten release quality.",
    "Fleet reliability has the clearest concentration of customer pain",
    'class="memo-invitation"',
    "Three pages on what to fund, what to diagnose, and where the evidence stops.",
    "THEMATIC DEEP DIVE",
    "The nine customer problems and needs that matter most",
    'class="analysis-intro"',
    "ANALYSIS WINDOW · ROLLING 365 DAYS",
    "September 1, 2025 through August 31, 2026",
    "<strong>927</strong><small>US public written reviews</small>",
    "<span>Driver</span><strong>800</strong>",
    "<span>Fleet</span><strong>127</strong>",
    'id="evidence-dialog"',
    "What a theme must pass before it becomes a finding",
    "Check the denominator",
    "Compare separate time periods",
    "Compare platforms",
    "Challenge the pattern",
    "Set the decision boundary",
    "SELECTABLE DATA LAYERS",
    'id="method-layer-buttons"',
    'id="method-phase-list"',
    'id="method-decision-grid"',
    "Automation moves the data; people approve the meaning",
    "METHODOLOGY",
    "DATA + REPRODUCIBILITY",
    "Six decisions separate source data from executive action",
    "Explore the complete layers and seven phases",
    "Pipeline details",
    'id="monitor-attention-list"',
    "Next Questions Worth Investigating",
    'id="further-recommendations-grid"',
    "id=\"evidence-table\"",
):
    if required not in html:
        failures.append(f"dashboard slice missing content: {required}")
if 'id="release-change"' in html:
    failures.append("overview still exposes release-refresh detail")
for tab_name in ("overview", "analysis", "method", "monitor"):
    if f'data-tab="{tab_name}"' not in html or f'data-tab-panel="{tab_name}"' not in html:
        failures.append(f"site is missing interactive tab or panel: {tab_name}")
tab_positions = [html.index(f'data-tab="{name}"') for name in ("overview", "analysis", "monitor", "method")]
if tab_positions != sorted(tab_positions):
    failures.append("primary tabs are not ordered Overview, Analysis, Monitor, Method")
for required in ('role="tablist"', 'id="memo-dialog"', 'id="evidence-dialog"', 'id="open-memo"', 'Samsara_CPO_Memo.pdf#view=FitH'):
    if required not in html:
        failures.append(f"site is missing interactive website control: {required}")
for required in ('data-theme-filter="All"', 'data-theme-filter="Fleet"', 'data-theme-filter="Driver"', 'id="theme-filter-summary"'):
    if required not in html:
        failures.append(f"site is missing thematic product filter: {required}")
for required in (
    "dashboard/dashboard-summary.json",
    "dashboard/dashboard-deltas.json",
    "priority-strip",
    "theme-grid",
    "theme-priority-grid",
    "additional-themes",
    "activateTab",
    "showModal",
    "ArrowRight",
    "history.pushState",
    "renderThemeCards",
    "Most urgent",
    "Highest consequence",
    "Shared control point",
    "127 Fleet reviews",
    "800 Driver reviews",
    "Recommended action",
    "executive_action",
    "proposed_owner",
    "priority",
    "recommendationByTheme",
    "themeSummaries",
    "What this means",
    "crashes, slow loading, blank screens",
    "duty-status, synchronization, or warning behavior",
    "The signal is too small for roadmap priority",
    "theme-evidence.json",
    "data-evidence-theme",
    "renderEvidence",
    "Critical/high potential consequence",
    "further-recommendations.json",
    "renderFurtherRecommendations",
    "methodology-process.json",
    "renderMethodologyProcess",
    "renderExistingThemeMonitor",
    "renderEmergingSignals",
    "one_review_sensitivity_pp",
    "provisional assignments",
    "data-layer-id",
    "method-phase-body",
    "method-practice-grid",
    "Boundaries and data needed",
    'window.location.protocol === "file:"',
    "http://127.0.0.1:8765/",
):
    if required not in js:
        failures.append(f"dashboard slice missing data binding: {required}")
for required in (
    'font-family: "FK Grotesk"',
    'font-family: "Samsara Sans"',
    "#1c1917",
    "#feae0f",
    "#eae8e3",
):
    if required not in css:
        failures.append(f"site is missing Samsara design-system token: {required}")

summary = json.loads((DOCS / "data" / "dashboard" / "dashboard-summary.json").read_text(encoding="utf-8"))
platform = json.loads((DOCS / "data" / "releases" / "reliable_20260831_v3" / "platform-comparison.json").read_text(encoding="utf-8"))
evidence = json.loads((DOCS / "data" / "releases" / "reliable_20260831_v3" / "theme-evidence.json").read_text(encoding="utf-8"))
further = json.loads((DOCS / "data" / "releases" / "reliable_20260831_v3" / "further-recommendations.json").read_text(encoding="utf-8"))
methodology = json.loads((DOCS / "data" / "releases" / "reliable_20260831_v3" / "methodology-process.json").read_text(encoding="utf-8"))
static_content = json.loads((DOCS / "data" / "releases" / "reliable_20260831_v3" / "static-content.json").read_text(encoding="utf-8"))
monitor_themes = json.loads((DOCS / "data" / "dashboard" / "dashboard-themes.json").read_text(encoding="utf-8"))
fleet = [row for row in platform if row["theme_id"] == "fleet_mobile_stability"]
if summary["new_reviews_since_prior_success"] != 6 or summary["changed_reviews_since_prior_success"] != 4:
    failures.append("dashboard summary does not carry the reconciled 6/4 delta")
if summary["analysis_release_id"] != "reliable_20260831_v3" or summary["human_review_queue_count"] != 0:
    failures.append("dashboard does not show the reviewed V3 release state")
if monitor_themes["schema_version"] != "2.0" or len(monitor_themes["existing_theme_metrics"]) != 9:
    failures.append("monitor does not expose all nine existing themes through the v2 contract")
if "emerging_signals" not in monitor_themes or "classified_no_theme_count" not in monitor_themes:
    failures.append("monitor contract is missing the governed emerging-signal fields")
if {(row["platform"], row["all_review_rate_pct"], row["share_of_improvement_signals_pct"]) for row in fleet} != {
    ("Android", 42.7, 49.3),
    ("iOS", 20.0, 45.0),
}:
    failures.append("Fleet platform-composition data does not match the governed comparison")
expected_evidence_counts = {
    "fleet_mobile_stability": 44,
    "fleet_access_recovery": 29,
    "driver_hos_state_integrity": 67,
    "driver_workflow_friction": 74,
    "driver_app_stability": 93,
    "fleet_map_stability": 12,
    "driver_safety_false_detection": 20,
    "driver_control_and_simplification_requests": 31,
    "fleet_product_requests": 3,
}
if evidence["total_theme_links"] != 373 or evidence["unique_evidence_records"] != 353:
    failures.append("theme evidence does not preserve the complete 373-link / 353-record index")
if {theme["theme_id"]: theme["evidence_count"] for theme in evidence["themes"]} != expected_evidence_counts:
    failures.append("theme evidence counts do not reconcile to governed theme counts")
expected_recommendations = {
    "public_developer_response_quality": "supported_finding",
    "multi_market_review_benchmark": "new_data_required",
    "platform_specific_stability_investigations": "supported_diagnostic",
}
if further["recommendation_count"] != 3 or len(further["recommendations"]) != 3:
    failures.append("further recommendations do not contain the three approved records")
if {item["recommendation_id"]: item["evidence_status"]["code"] for item in further["recommendations"]} != expected_recommendations:
    failures.append("further recommendation evidence statuses do not match the approved decisions")
if sum(len(item["evidence"]) for item in further["recommendations"]) != 12:
    failures.append("further recommendations do not preserve all 12 evidence records")
if len(methodology["phases"]) != 7 or len(methodology["layers"]) != 8 or len(methodology["decision_moments"]) != 4:
    failures.append("methodology process does not preserve the approved 7-phase, 8-layer, 4-decision structure")
if methodology["heading"] != "Turning public reviews into product signal":
    failures.append("methodology heading does not match the approved plain-language title")
if "No review appears on both sides" not in html:
    failures.append("methodology does not explain separate time comparisons in plain language")
for removed in (
    'id="recommendations"',
    "Move from public signal to internal diagnosis",
    "All themes shown here passed the evidence review.",
    "this is a combined decision-priority view",
):
    if removed in html or removed in js:
        failures.append(f"superseded dense analysis content remains: {removed}")
for name in (
    "Make public developer responses more helpful and specific",
    "Establish a staged multi-market review benchmark",
    "Open targeted platform-specific stability investigations",
):
    if name in html:
        failures.append(f"further recommendation was hardcoded into HTML: {name}")
if "Finding status" in js or "themeDecisionLabels" in js or "Validated finding" in js:
    failures.append("theme cards still expose the redundant finding-status treatment")
if "themeResponseLabels" in js or "What to do next" in js:
    failures.append("theme cards still use generic response-posture labels instead of approved actions")
approved_theme_actions = {item["theme_id"]: item["recommendation"] for item in static_content["surfaces"]["recommendations"]}
if len(approved_theme_actions) != 9 or not all(len(action) >= 45 for action in approved_theme_actions.values()):
    failures.append("theme cards do not have nine sufficiently specific approved actions")
if approved_theme_actions.get("fleet_mobile_stability") != "Open a cross-platform reliability workstream covering crash, load, blank-state, and map paths.":
    failures.append("Fleet stability card is not bound to the approved executive action")
if not all(item.get("priority") and item.get("proposed_owner") for item in static_content["surfaces"]["recommendations"]):
    failures.append("approved recommendations must include a priority and proposed functional owner")
if "did not find enough evidence to claim that any theme is improving" not in static_content["surfaces"]["executive_overview"].get("recent_signal", ""):
    failures.append("executive overview must state the bounded recent-movement conclusion")
practice_notes = methodology.get("practice_notes", {})
if set(practice_notes) != {"ai_use", "access_limits", "next_week", "production_boundary"}:
    failures.append("methodology must expose AI use, access limits, next-week work, and the production boundary")
if "Extend the evidence without overstating it" in html or "NEXT QUESTIONS WORTH INVESTIGATING" in html:
    failures.append("further recommendations still contains the superseded two-part heading")
for name in ("Turning public reviews into product signal", "Do not force the source totals to match", "Lift the analysis into a shareable, repeatable system"):
    if name in html:
        failures.append(f"methodology content was hardcoded into HTML: {name}")

if failures:
    raise SystemExit("Dashboard slice FAIL\n- " + "\n- ".join(failures))

print({
    "gate": "PASS",
    "required_files": len(required_files),
    "new_reviews": 6,
    "changed_reviews": 4,
    "human_review_queue": 0,
    "fleet_platform_composition_reconciled": True,
})
