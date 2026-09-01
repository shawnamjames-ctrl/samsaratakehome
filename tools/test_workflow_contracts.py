from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def require(text: str, pattern: str, message: str) -> None:
    if re.search(pattern, text, flags=re.MULTILINE) is None:
        raise AssertionError(message)


daily = (WORKFLOWS / "daily-monitor.yml").read_text(encoding="utf-8")
weekly = (WORKFLOWS / "weekly-reconcile.yml").read_text(encoding="utf-8")
deploy = (WORKFLOWS / "deploy-pages.yml").read_text(encoding="utf-8")
validate = (WORKFLOWS / "validate.yml").read_text(encoding="utf-8")

require(daily, r'^\s*workflow_dispatch:', "daily workflow must support a manual run")
require(daily, r'cron: "17 6 \* \* \*"', "daily schedule must avoid the top of the hour")
require(daily, r"if: \$\{\{ vars\.MONITORING_ENABLED == 'true' \}\}", "daily monitoring must remain disabled until private state is configured")
require(weekly, r"if: \$\{\{ vars\.MONITORING_ENABLED == 'true' \}\}", "weekly reconciliation must remain disabled until private state is configured")
require(daily, r'actions/deploy-pages@v4', "daily success must deploy Pages directly")
if daily.count("actions/deploy-pages@v4") != 1:
    raise AssertionError("daily dashboard refresh must use exactly one Pages deployment")
require(daily, r'if: \$\{\{ always\(\)', "raw evidence must be retained after a failed gate")
require(daily, r'python pipeline/state_store.py push-db', "successful run must persist state")
require(daily, r'pull-published-db --database data/processed/prior_monitoring_reviews.sqlite3', "daily deltas must compare against the last publicly reported state")
require(daily, r'python pipeline/state_store.py push-published-db', "a successful publication must advance the published comparison state")
if daily.index("actions/deploy-pages@v4") > daily.index("python pipeline/state_store.py push-published-db"):
    raise AssertionError("published comparison state must advance only after Pages deployment succeeds")
if daily.index("actions/deploy-pages@v4") > daily.index("git push"):
    raise AssertionError("dashboard commit must occur only after Pages deployment succeeds")
if "push-published-db" in weekly:
    raise AssertionError("weekly reconciliation must not advance the publicly reported comparison state")
require(daily, r'python pipeline/analyze_monitoring.py', "daily workflow must analyze existing and emerging themes before export")
if daily.index("python pipeline/analyze_monitoring.py") > daily.index("python pipeline/update_dashboard.py"):
    raise AssertionError("monitoring analysis must run before the public dashboard export")
require(weekly, r'python review_monitor.py .* reconcile', "weekly workflow must fully reconcile")
require(deploy, r'actions/upload-pages-artifact@v4', "Pages workflow must upload the built site")
require(deploy, r'public-data/releases/\*\*', "static Pages workflow must deploy approved release changes")
if "public-data/**" in deploy or "public-data/dashboard" in deploy:
    raise AssertionError("dashboard-only changes must not trigger a second Pages deployment")
require(validate, r'python -m unittest discover', "validation workflow must run failure tests")

for workflow in (daily, weekly, deploy, validate):
    for script in re.findall(r'python(?: -m \S+)? ([\w./-]+\.py)', workflow):
        if not (ROOT / script).is_file():
            raise AssertionError(f"workflow references missing script: {script}")

if "data/processed" not in (ROOT / ".gitignore").read_text(encoding="utf-8"):
    raise AssertionError("private operational database directory must be ignored")

print({"gate": "PASS", "workflows": 4, "daily_deploy": True, "single_dashboard_deploy_path": True, "private_state_after_deploy": True})
