# Public pipeline

This directory contains the reproducible collection interfaces, privacy-safe daily
export logic, and private state adapter. Operational state and raw evidence remain
external to Git and are stored in a private S3-compatible object store in production.

`update_dashboard.py` compares the current database with the prior successful state.
It exports counts, source health, and pseudonymous evidence keys, never review text,
reviewer names, source review identifiers, or developer-response text.

`state_store.py` supports `local` for testing and `s3` for GitHub Actions. It advances
the operational database only after all publication gates pass. A separate published
comparison database advances only after deployment gates pass, so weekly reconciliation
cannot absorb reviews before they appear in the public change ledger. Raw snapshots are
retained even when a later gate fails, so failures can be diagnosed without replacing
the last known-good dashboard.

`analyze_monitoring.py` is the private analytical layer between collection and export. It
uses versioned frozen-theme rules, content-hash idempotency, provisional assignments, and a
residual candidate queue. `seed_approved_theme_assignments.py` initializes that layer from
the human-approved V3 analysis before the private state is uploaded. `update_dashboard.py`
then recalculates the nine theme comparisons and exports only aggregate, privacy-safe
monitoring data.
