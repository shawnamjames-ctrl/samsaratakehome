# Operations runbook

## What changes automatically

The daily workflow updates only the four files in `public-data/dashboard/` and their
built copies under `docs/data/dashboard/`. The executive overview, CPO memo, thematic
analysis, recommendations, and methodology stay pinned to the approved static release
until a person approves a new release.

The weekly workflow performs a full source reconciliation for drift detection. It
updates private operational state but does not publish a new analytical narrative.

## Private state prerequisites

Create a private, versioned S3-compatible bucket and seed this object before enabling
the scheduled workflow:

`<PRIVATE_STATE_PREFIX>/monitoring_reviews.sqlite3`

Seed a second copy for the last successfully published comparison state:

`<PRIVATE_STATE_PREFIX>/published_monitoring_reviews.sqlite3`

Before uploading either seed, initialize the source-visible review database and transfer
the approved V3 assignments into it:

```bash
python review_monitor.py --config config/monitoring_sources.json reconcile
python pipeline/seed_approved_theme_assignments.py
```

Inspect the seed report. Missing analysis reviews must be explained before automation is
enabled. Upload the seeded database as both the operational and published starting state.

Configure these GitHub Actions secrets:

- `PRIVATE_STATE_BUCKET`
- `PRIVATE_STATE_PREFIX`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION`
- `AWS_ENDPOINT_URL` only when the store is not AWS S3

Keep the repository variable `MONITORING_ENABLED` unset or set to `false` while the
private state is being prepared. Scheduled daily and weekly jobs will be skipped rather
than fail against missing credentials. After both database objects and all required
secrets are in place, set `MONITORING_ENABLED` to `true` and complete the activation
sequence below.

Use a dedicated service identity scoped to read and write only this bucket and prefix.
Enable bucket versioning and encryption. Raw snapshots are written below
`<PRIVATE_STATE_PREFIX>/raw/`; neither raw snapshots nor the populated database belong
in GitHub.

## Publication gates

A daily release is deployed only when all four sources produce a successful pull, the
database validates, delta reconciliation succeeds, the static release is unchanged,
public JSON matches its schemas, the privacy and repository-boundary scans pass, and
the built site passes its integrity checks.

The monitoring-analysis gate must also complete. It applies only the versioned frozen-theme
rules in `config/monitoring_themes.json`. Rule matches are provisional, low-confidence
matches and residual reviews enter human review, and repeated residuals may form an emerging
candidate. Automation cannot approve a new theme, change the taxonomy, or alter the static
executive release.

## Daily analytical outputs

Every successful daily run recalculates all nine themes using the latest 30 days and an
earlier, separate 60-day comparison. Quantitative statuses require the configured minimum
denominators and theme hits. `Limited data` is a valid result and cannot be promoted to an
alert. Watch and alert candidates are investigation triggers, not root-cause claims.

Emerging candidates expose only aggregate metadata publicly. Review text, repeated terms,
and clustering signatures remain in the private database. A person must inspect the private
records and either dismiss the pattern, confirm that it fits an existing theme, mark it as
no theme, or move it into the governed taxonomy-change process for the next analytical
release.

If a gate fails, the Pages deployment is skipped and the prior public dashboard stays
live. Raw snapshots from the attempted run are retained for diagnosis. The operational
and published private-state pointers advance only after Pages deployment and the
privacy-safe dashboard commit both succeed.

Dashboard refreshes use one deployment path: **Daily private review monitoring** builds
and deploys the dashboard itself. **Deploy approved site to GitHub Pages** handles static
site, approved-release, and deliverable changes; dashboard-only commits are intentionally
excluded from its path trigger so one refresh cannot launch a second deployment.

## GitHub Pages setup

1. Create the repository and push the `main` branch.
2. In repository settings, choose **GitHub Actions** as the Pages source.
3. Run **Deploy approved site to GitHub Pages** manually once.
4. Add the private-state secrets above and seed both private database objects.
5. Set the repository variable `MONITORING_ENABLED` to `true`.
6. Run **Daily private review monitoring** manually and confirm its four source cards,
   timestamps, and publication gates before relying on the schedule.

The daily job runs at 06:17 America/Los_Angeles and the weekly reconciliation at 07:23
Sunday. The non-round-minute schedules reduce peak-time queue risk. GitHub schedules
are best-effort, so the dashboard prominently reports its last successful run and data
freshness rather than assuming a run happened.

## Recovery

- Source or validation failure: inspect the workflow logs and retained raw snapshot;
  do not publish manually around the failed gate.
- Bad private state: restore the previous object version, then rerun the daily workflow.
- Bad public release: redeploy the last known-good commit through the Pages workflow.
- Missed schedule: use `workflow_dispatch`; the next run compares against the last
successful database, so reviews since that run are still included.

The operational and published states are intentionally separate. Weekly reconciliation
advances only `monitoring_reviews.sqlite3`. Daily change detection compares against
`published_monitoring_reviews.sqlite3`, and that object advances only after a successful
Pages deployment and repository commit. Reviews first discovered by a weekly reconciliation therefore still
appear in the next public change ledger.
