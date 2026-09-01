# Samsara Mobile Product Intelligence

An evidence-governed Product Operations case study built from public written reviews of
Samsara Driver and Samsara Fleet on the US Apple App Store and Google Play.

## View the finished project

- **[Open the interactive analysis](https://shawnamjames-ctrl.github.io/samsaratakehome/)**
- [Read the three-page CPO memo](https://shawnamjames-ctrl.github.io/samsaratakehome/downloads/Samsara_CPO_Memo.pdf)
- [Read the one-page methodology note](https://shawnamjames-ctrl.github.io/samsaratakehome/downloads/Samsara_Methodology_Note.pdf)

The interactive analysis is the primary deliverable. Use the navigation to review the
executive recommendation, thematic analysis, monitoring system, and methodology.

The published experience uses two clocks:

- Overview, analysis, recommendations, and methodology are pinned to a human-approved
  analytical release.
- The Monitor may refresh after a successful daily pipeline run; it cannot silently
  rewrite the approved executive narrative.

## Optional: run the site locally

These steps are only for someone who clones the repository and wants to inspect the
built HTML locally, without relying on the published GitHub Pages site.

From this repository directory, run:

```bash
python3 -m http.server 8765 --directory docs
```

Then open `http://127.0.0.1:8765/`. The primary navigation is **Overview**, **Analysis**,
**Monitor**, and **Method**. Stop the server with `Control-C`.

## What to review

- **Overview** - the CPO recommendation, three executive signals, recent movement, and
  the three-page memo.
- **Analysis** - nine challenged themes with product-specific denominators, evidence,
  proposed owners, and Now/Next/Later priorities.
- **Monitor** - latest-30 versus separate-prior-60 movement, source health, review deltas,
  and the residual human-review queue.
- **Method** - the evidence path, judgment moments, AI use, access limits, and the
  production boundary.

## Submission artifacts

The exact interview package is:

1. [`deliverables/Samsara_CPO_Memo.pdf`](deliverables/Samsara_CPO_Memo.pdf) - three-page CPO readout.
2. [`deliverables/Samsara_Methodology_Note.pdf`](deliverables/Samsara_Methodology_Note.pdf) - one-page methodology note.
3. `docs/` - the built interactive site, including privacy-safe governed JSON.
4. This repository - pipeline, schemas, validation tests, workflows, and operating notes.

Open [`deliverables/`](deliverables/) for the two-document review package and suggested
reading order.

Local DOCX working files and the interview-process narrative are preparation materials,
not submission artifacts.

## Implementation status

Working now in the repository:

- Reproducible public-source collection and normalization logic.
- Frozen V3 analysis, nine challenged themes, evidence-linked recommendations, and
  separate-period monitoring rules.
- Privacy-safe JSON contracts, schema checks, hashed manifests, last-good behavior,
  site build, and responsive dashboard.
- Daily and weekly GitHub Actions workflows with a single dashboard-refresh deployment
  path: the daily monitor owns dashboard publication; the static-site workflow excludes
  dashboard-only changes.

Required before production activation:

- A private, versioned state bucket and the GitHub secrets described in `OPERATIONS.md`.
- Apple App Store Connect and Google Play Console owner credentials for complete,
  authenticated review access.
- Internal telemetry, incident, support, account, and release joins to test root cause,
  customer impact, recovery, and release-level attribution.
- Product-owner confirmation of the proposed functional owners and alert thresholds.

Scheduled private monitoring is intentionally inactive at first publication. After the
private state and secrets are configured and tested, set the repository variable
`MONITORING_ENABLED` to `true`; until then, scheduled jobs are safely skipped while the
approved static site remains deployable.

## Automation model

The approved static release is `reliable_20260831_v3`; V2 remains archived under
`public-data/releases/`. The daily workflow collects the four sources, compares them with
the last successfully published state, evaluates the frozen nine-theme rules, updates
separate-period movement and the emerging-signal queue, runs publication gates, deploys
the dashboard, and only then advances the published comparison state. A weekly workflow
reconciles the complete source-visible corpus without publishing a new narrative.

Raw review text, reviewer names, and the populated SQLite database remain in private
state; GitHub contains only aggregate metrics and pseudonymous delta records.

## Walkthrough-ready live change

A safe live demonstration is to change a monitoring threshold in
`config/monitoring_themes.json`, run the monitoring-analysis and site-build checks, and
show how a theme moves between **Limited data**, **Stable**, **Watch**, and **Alert
candidate** without altering the approved executive release. This demonstrates the
separation between operational signals and human-approved conclusions.

## Repository boundary

This repository contains the GitHub Pages site, privacy-safe aggregate data, sanitized
fixtures, reproducible pipeline code, analytical definitions, validation rules, and
release manifests. It does not contain raw collector payloads, the populated operational
database, reviewer display names, bulk verbatim review text, credentials, or unredacted
audit files.

## Independence notice

This is an independent interview case-study project. It is not affiliated with,
endorsed by, or operated by Samsara.
