PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS methodology_phases (
    analysis_run_id TEXT NOT NULL,
    phase_id TEXT NOT NULL,
    display_order INTEGER NOT NULL CHECK (display_order > 0),
    title TEXT NOT NULL,
    objective TEXT NOT NULL,
    work_completed TEXT NOT NULL,
    decision_made TEXT NOT NULL,
    rationale TEXT NOT NULL,
    evidence_produced TEXT NOT NULL,
    boundary_or_gate TEXT NOT NULL,
    PRIMARY KEY (analysis_run_id, phase_id),
    FOREIGN KEY (analysis_run_id) REFERENCES reliable_analysis_runs(analysis_run_id)
);

CREATE TABLE IF NOT EXISTS methodology_layers (
    analysis_run_id TEXT NOT NULL,
    layer_id TEXT NOT NULL,
    display_order INTEGER NOT NULL CHECK (display_order > 0),
    title TEXT NOT NULL,
    short_label TEXT NOT NULL,
    input_summary TEXT NOT NULL,
    decision_summary TEXT NOT NULL,
    output_summary TEXT NOT NULL,
    gate_summary TEXT NOT NULL,
    path_type TEXT NOT NULL CHECK (path_type IN ('analysis', 'monitoring')),
    PRIMARY KEY (analysis_run_id, layer_id),
    FOREIGN KEY (analysis_run_id) REFERENCES reliable_analysis_runs(analysis_run_id)
);

CREATE TABLE IF NOT EXISTS methodology_decisions (
    analysis_run_id TEXT NOT NULL,
    decision_id TEXT NOT NULL,
    display_order INTEGER NOT NULL CHECK (display_order > 0),
    title TEXT NOT NULL,
    situation TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    why_it_matters TEXT NOT NULL,
    PRIMARY KEY (analysis_run_id, decision_id),
    FOREIGN KEY (analysis_run_id) REFERENCES reliable_analysis_runs(analysis_run_id)
);

CREATE TABLE IF NOT EXISTS methodology_operating_model (
    analysis_run_id TEXT NOT NULL,
    responsibility_id TEXT NOT NULL,
    display_order INTEGER NOT NULL CHECK (display_order > 0),
    owner_type TEXT NOT NULL CHECK (owner_type IN ('automated', 'human')),
    responsibility TEXT NOT NULL,
    PRIMARY KEY (analysis_run_id, responsibility_id),
    FOREIGN KEY (analysis_run_id) REFERENCES reliable_analysis_runs(analysis_run_id)
);

DELETE FROM methodology_phases WHERE analysis_run_id = 'reliable_20260831_v3';
DELETE FROM methodology_layers WHERE analysis_run_id = 'reliable_20260831_v3';
DELETE FROM methodology_decisions WHERE analysis_run_id = 'reliable_20260831_v3';
DELETE FROM methodology_operating_model WHERE analysis_run_id = 'reliable_20260831_v3';

INSERT INTO methodology_phases VALUES
('reliable_20260831_v3','scope_sources',1,'Define the question and source boundaries','Turn public app-store feedback into useful product signal without claiming that reviews represent every customer.','Identified the US Apple App Store and Google Play listings for Driver and Fleet, tested the public endpoints, and documented what each source exposes.','Use all unique written reviews available from the four public sources, while treating storefront feedback as directional evidence.','This created a reproducible public-data boundary and avoided implying access to internal customer or product data.','Four source definitions and 5,209 endpoint-visible written reviews in the baseline extraction.','Apple Driver exposes a capped feed and Google listing totals do not always match exhausted pagination. Unique extracted review IDs are the count of record.'),
('reliable_20260831_v3','extract_store',2,'Build a trustworthy extraction and storage foundation','Preserve what the sources returned and make every later transformation traceable.','Saved immutable raw snapshots, normalized reviews and developer responses into SQLite, assigned stable IDs, and retained observation history across pulls.','Separate raw evidence, normalized facts, and analytical labels instead of overwriting source data.','This makes reruns, corrections, and source-state changes auditable.','Source snapshots, normalized review records, response records, stable identifiers, hashes, and pull-run logs.','A failed pull cannot replace the last good state, and raw reviewer data remains private.'),
('reliable_20260831_v3','profile_window',3,'Profile the data and choose comparable windows','Create a fair analysis population before interpreting themes.','Profiled dates, products, platforms, ratings, missingness, duplicates, and source coverage, then selected a common rolling-year window.','Use September 1, 2025 through August 31, 2026 for the approved analysis and use separate earlier periods for recent-trend comparisons.','A common window makes product and platform comparisons easier to interpret, while separate comparison periods prevent the same review from appearing on both sides.','927 eligible US written reviews: 800 Driver and 127 Fleet.','Google Driver dominates the natural sample, so rates use the relevant product or platform denominator rather than the combined total.'),
('reliable_20260831_v3','taxonomy',4,'Discover, align, and calibrate the taxonomy','Build labels from the customer language while keeping them relevant to Samsara product decisions.','Reviewed a 96-review discovery sample, aligned emerging concepts to Samsara product areas, and calibrated definitions on 24 collaborative plus 40 independent reviews.','Use a structured taxonomy for product area, issue, customer signal, failure mode, and potential consequence.','The shared definitions reduce interpretation drift and make disagreement visible before scaling.','A codebook, inclusion and exclusion rules, calibration notes, and 64 checked calibration records.','An out-of-window 2022 review was removed before coding so calibration matched the approved population.'),
('reliable_20260831_v3','semantic_gate',5,'Reopen and correct the semantic classification gate','Verify that structurally valid labels also mean the right thing.','Audited early classifications against the review text and found that 354 of 439 checked records changed on at least one field. Downstream work paused, 486 remaining reviews were blind reviewed, and an 80-review consistency rerun tested five core fields.','Rebuild the reliable analysis base instead of accepting technically valid but semantically weak labels.','A data pipeline can pass format checks while still producing unreliable meaning. The semantic gate protects the analysis from that failure.','924 checked V2 reviews, 438 corrected carry-forwards, 486 blind-reviewed records, and a passing consistency rerun for five core fields.','The manual feedback-strength label did not meet the reproducibility threshold, so it was narrowed to a conservative confirmation flag rather than weakening the gate.'),
('reliable_20260831_v3','challenge_findings',6,'Synthesize, challenge, and approve findings','Turn repeated review patterns into decision-ready findings with explicit limits.','Calculated product and platform rates, compared separate time periods, reviewed counterevidence and alternative explanations, tested sensitivity, and examined supporting review records.','Publish only themes that survive the five-part evidence review and receive human approval.','Counts alone do not explain whether a pattern is stable, concentrated, consequential, or actionable.','Nine challenged themes supported by 373 theme links across 353 unique review records.','Public reviews support where to investigate and improve. They do not establish prevalence across all customers or prove root cause.'),
('reliable_20260831_v3','share_repeat',7,'Lift the analysis into a shareable, repeatable system','Make the work easy to inspect, share, and refresh without silently changing executive conclusions.','Separated approved static outputs from the live monitor, exported privacy-safe JSON contracts, added validation and last-good behavior, and prepared daily plus weekly reconciliation.','Run two clocks: human-approved analytical releases for executive content and automated monitoring for newly observed signals.','This combines a stable interview deliverable with a maintainable operating process.','A local GitHub Pages build, governed public contracts, hashed release manifest, automated checks, and daily monitor state.','New reviews can update the monitor automatically, but themes, recommendations, and executive claims change only through review and a new approved release.');

INSERT INTO methodology_layers VALUES
('reliable_20260831_v3','public_sources',1,'Public app-store sources','Sources','Apple App Store and Google Play listings for Driver and Fleet in the US storefront.','Use written public reviews from the four tested endpoints and document source limits.','5,209 endpoint-visible baseline reviews and source metadata.','Confirm endpoint availability, fields, dates, and pagination behavior before accepting a pull.','analysis'),
('reliable_20260831_v3','raw_evidence',2,'Immutable raw evidence','Raw evidence','Returned payloads and pull metadata.','Preserve the original response before cleaning or interpretation.','Timestamped source snapshots that can be replayed and audited.','A failed or incomplete pull cannot replace the last good snapshot.','analysis'),
('reliable_20260831_v3','normalized_facts',3,'Normalized facts and history','Normalized data','Raw review and developer-response records.','Create stable review IDs, standard fields, hashes, and observation history.','A private SQLite evidence base with source changes separated from analytical labels.','Uniqueness, integrity, date, and source-reconciliation checks must pass.','analysis'),
('reliable_20260831_v3','analytical_frame',4,'Comparable analytical frame','Analysis frame','Profiled dates, products, platforms, ratings, and source coverage.','Use a rolling 365-day US population and relevant denominators; compare recent periods with earlier separate periods.','927 eligible reviews and comparable product, platform, and time cuts.','Exclude out-of-window records and disclose uneven source coverage.','analysis'),
('reliable_20260831_v3','checked_interpretation',5,'Checked taxonomy and labels','Interpretation','Customer language, calibrated codebook, and normalized review facts.','Require reproducible meaning across five core analytical fields.','Human-checked classifications linked to the source records.','Pause if semantic agreement fails, even when structural validation passes.','analysis'),
('reliable_20260831_v3','challenged_findings',6,'Challenged themes','Findings','Rates, time comparisons, platform cuts, evidence records, and counterevidence.','Approve only findings that survive denominator, time, platform, challenge, and decision-boundary checks.','Nine themes with confidence, response posture, evidence, and claim boundaries.','A human reviewer must approve the interpretation.','analysis'),
('reliable_20260831_v3','approved_release',7,'Approved shareable release','Approved release','Challenged findings, recommendations, and executive narrative.','Freeze a versioned, privacy-safe release with hashed public files.','Stable executive pages and inspectable public data contracts.','Privacy, contract, hash, boundary, and site checks must all pass.','analysis'),
('reliable_20260831_v3','repeatable_monitor',8,'Repeatable monitoring layer','Daily monitor','Fresh source observations compared with the last successful run.','Update daily operational signals without rewriting the approved analytical release.','Freshness, new and changed review counts, alerts, and a human review queue.','Withhold failed runs, preserve the last good output, and reconcile the rolling year weekly.','monitoring');

INSERT INTO methodology_decisions VALUES
('reliable_20260831_v3','source_totals',1,'Do not force the source totals to match','Google listing totals and exhausted pagination did not always agree, and Apple Driver exposed a capped public feed.','Count unique review IDs actually extracted and disclose endpoint limits.','It keeps the evidence reproducible instead of manufacturing completeness.'),
('reliable_20260831_v3','sample_correction',2,'Correct the sample before coding','A 2022 review appeared in the intended common-window sample.','Remove it and rebuild the sample before taxonomy work continued.','Correcting the population early prevents a known eligibility error from entering the codebook.'),
('reliable_20260831_v3','semantic_reopen',3,'Reopen a gate that passed technically','The first process audit changed 354 of 439 checked records on at least one field.','Pause downstream analysis, correct carried records, blind-review the rest, and rerun consistency testing.','Format-valid data is not useful if the meaning is unreliable.'),
('reliable_20260831_v3','platform_mix',4,'Narrow the Fleet Android interpretation','Fleet stability appeared much higher on Android in all reviews, but Android also had a far more problem-heavy review population.','Compare the theme among reviews that already signal a problem. The gap narrowed from 42.7% versus 20.0% of all reviews to 49.3% versus 45.0% of problem-signal reviews.','The defensible finding is a concentration in negative Android feedback, not proof of a fundamentally different Android product problem.');

INSERT INTO methodology_operating_model VALUES
('reliable_20260831_v3','auto_collect',1,'automated','Collect, normalize, deduplicate, and compare new source observations.'),
('reliable_20260831_v3','auto_validate',2,'automated','Run integrity, freshness, privacy, contract, and publication checks.'),
('reliable_20260831_v3','auto_monitor',3,'automated','Refresh daily monitor metrics and preserve the last good state on failure.'),
('reliable_20260831_v3','human_taxonomy',1,'human','Approve taxonomy changes and decide whether a new pattern becomes a theme.'),
('reliable_20260831_v3','human_interpret',2,'human','Review counterevidence, platform mix, claim boundaries, and recommendations.'),
('reliable_20260831_v3','human_release',3,'human','Approve a new static analytical release before executive content changes.');

PRAGMA integrity_check;
