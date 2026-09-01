PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS further_recommendations (
    analysis_run_id TEXT NOT NULL,
    recommendation_id TEXT NOT NULL,
    title TEXT NOT NULL,
    rationale TEXT NOT NULL,
    evidence_status_code TEXT NOT NULL CHECK (
        evidence_status_code IN ('supported_finding', 'new_data_required', 'supported_diagnostic')
    ),
    evidence_status_label TEXT NOT NULL,
    evidence_summary TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    decision_boundary TEXT NOT NULL,
    additional_data_needed TEXT NOT NULL,
    display_order INTEGER NOT NULL CHECK (display_order > 0),
    publication_status TEXT NOT NULL CHECK (
        publication_status IN ('draft', 'approved_for_analysis_section', 'retired')
    ),
    approved_at TEXT,
    PRIMARY KEY (analysis_run_id, recommendation_id),
    FOREIGN KEY (analysis_run_id) REFERENCES reliable_analysis_runs(analysis_run_id)
);

CREATE TABLE IF NOT EXISTS further_recommendation_evidence (
    analysis_run_id TEXT NOT NULL,
    recommendation_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    evidence_class TEXT NOT NULL CHECK (
        evidence_class IN ('governed_metric', 'exploratory_probe', 'collection_limitation')
    ),
    metric_label TEXT NOT NULL,
    metric_value TEXT NOT NULL,
    context TEXT NOT NULL,
    display_order INTEGER NOT NULL CHECK (display_order > 0),
    PRIMARY KEY (analysis_run_id, recommendation_id, evidence_id),
    FOREIGN KEY (analysis_run_id, recommendation_id)
        REFERENCES further_recommendations(analysis_run_id, recommendation_id)
        ON DELETE CASCADE
);

INSERT INTO further_recommendations (
    analysis_run_id,
    recommendation_id,
    title,
    rationale,
    evidence_status_code,
    evidence_status_label,
    evidence_summary,
    recommended_action,
    decision_boundary,
    additional_data_needed,
    display_order,
    publication_status,
    approved_at
) VALUES
(
    'reliable_20260831_v3',
    'public_developer_response_quality',
    'Make public developer responses more helpful and specific',
    'Developer responses are part of the visible customer experience. They show both the reviewer and prospective customers whether Samsara understands the problem, takes ownership, and provides a useful path forward.',
    'supported_finding',
    'Supported finding about response quality; brand effect not yet measured',
    'In the rolling-year Google data, 85 of 90 responses are generic or templated. Only five address the customer issue specifically, two communicate a fix or resolution, and none provide visible case or follow-up language.',
    'Establish a response-quality playbook that preserves empathy while adding issue recognition, relevant guidance, a clear next step, ownership, and closure. Score response quality by customer issue, severity, response time, template reuse, and subsequent customer outcomes.',
    'The data supports an assessment of visible response quality. It does not prove that a customer noticed the repetition or that the responses changed public brand perception. Apple response practices cannot be compared until owner-side response data is available.',
    'Repair five response-timing anomalies, add owner-side Apple response records, and connect responses to later rating edits, reviewer follow-up, or support-resolution signals.',
    1,
    'approved_for_analysis_section',
    '2026-08-31T20:30:00-07:00'
),
(
    'reliable_20260831_v3',
    'multi_market_review_benchmark',
    'Establish a staged multi-market review benchmark',
    'The current analysis describes US storefront feedback. A staged international benchmark would show which themes travel across markets and which may reflect local regulation, language, rollout, or workflow differences.',
    'new_data_required',
    'New data required; Canada is the strongest first collection market',
    'The governed corpus contains 927 US reviews and no governed international comparison set. Earlier Apple probes found 207 Driver and 15 Fleet reviews in Canada, with much smaller samples in the United Kingdom and Mexico.',
    'Extend governed collection to Canada first, then add Mexico and other markets as review volume permits. Compare themes within the same product, platform, language, and time period.',
    'The existing probes establish collection feasibility, not international findings. Storefront territory does not establish reviewer location, and raw country counts are not comparable without product and platform standardization.',
    'Add country-specific sources, English, French, and Spanish language controls, translation validation, minimum sample thresholds, and local regulatory, rollout, and release context.',
    2,
    'approved_for_analysis_section',
    '2026-08-31T20:30:00-07:00'
),
(
    'reliable_20260831_v3',
    'platform_specific_stability_investigations',
    'Open targeted platform-specific stability investigations',
    'Several review patterns differ between Android and iOS after using product-specific denominators. These differences can focus technical investigation on the code paths, devices, versions, and workflows most likely to need attention.',
    'supported_diagnostic',
    'Supported diagnostic recommendation; internal product data required to determine cause',
    'Fleet access and recovery is more Android-concentrated after adjustment. Driver app stability is directionally higher on Android, while Driver HOS integrity is higher on iOS. The large raw Fleet stability gap narrows substantially after controlling for review mix.',
    'Review crash reports, application versions, operating-system versions, device models, release groups, network conditions, and support cases for the platform-skewed workflows.',
    'Public reviews can identify where reported experiences differ. They cannot establish that Android, iOS, or a specific code change caused the problem because reviewers are self-selected and platform populations differ.',
    'Join the review signals to internal crash, performance, release, device, network, incident, and support data before assigning root cause or engineering scope.',
    3,
    'approved_for_analysis_section',
    '2026-08-31T20:30:00-07:00'
)
ON CONFLICT (analysis_run_id, recommendation_id) DO UPDATE SET
    title = excluded.title,
    rationale = excluded.rationale,
    evidence_status_code = excluded.evidence_status_code,
    evidence_status_label = excluded.evidence_status_label,
    evidence_summary = excluded.evidence_summary,
    recommended_action = excluded.recommended_action,
    decision_boundary = excluded.decision_boundary,
    additional_data_needed = excluded.additional_data_needed,
    display_order = excluded.display_order,
    publication_status = excluded.publication_status,
    approved_at = excluded.approved_at;

DELETE FROM further_recommendation_evidence
WHERE analysis_run_id = 'reliable_20260831_v3';

INSERT INTO further_recommendation_evidence (
    analysis_run_id,
    recommendation_id,
    evidence_id,
    evidence_class,
    metric_label,
    metric_value,
    context,
    display_order
) VALUES
('reliable_20260831_v3', 'public_developer_response_quality', 'response_generic', 'governed_metric', 'Generic or templated', '85 of 90', 'Rolling-year Google developer responses', 1),
('reliable_20260831_v3', 'public_developer_response_quality', 'response_specific', 'governed_metric', 'Issue-specific', '5 of 90', 'Responses with specific product context, explanation, instruction, or resolution', 2),
('reliable_20260831_v3', 'public_developer_response_quality', 'response_resolution', 'governed_metric', 'Fix or resolution stated', '2 of 90', 'Responses that publicly communicate a fix or resolution', 3),
('reliable_20260831_v3', 'public_developer_response_quality', 'response_median_time', 'governed_metric', 'Median valid response time', '4.4 days', 'Based on 85 nonnegative response-timing records; five anomalies excluded', 4),
('reliable_20260831_v3', 'multi_market_review_benchmark', 'governed_us', 'governed_metric', 'Governed US corpus', '927 reviews', 'Rolling 365-day approved analysis population', 1),
('reliable_20260831_v3', 'multi_market_review_benchmark', 'canada_probe', 'exploratory_probe', 'Canada Apple probe', '222 reviews', '207 Driver and 15 Fleet; feasibility signal only', 2),
('reliable_20260831_v3', 'multi_market_review_benchmark', 'mexico_probe', 'exploratory_probe', 'Mexico Apple probe', '12 reviews', '4 Driver and 8 Fleet; insufficient for stable comparison', 3),
('reliable_20260831_v3', 'multi_market_review_benchmark', 'territory_limit', 'collection_limitation', 'Location boundary', 'Storefront only', 'Territory does not prove reviewer location', 4),
('reliable_20260831_v3', 'platform_specific_stability_investigations', 'fleet_access', 'governed_metric', 'Fleet access, Android vs iOS', '35.2% vs 20.0%', 'Share of improvement-signal reviews; 25 Android and 4 iOS records', 1),
('reliable_20260831_v3', 'platform_specific_stability_investigations', 'driver_stability', 'governed_metric', 'Driver stability, Android vs iOS', '22.6% vs 17.4%', 'Share of improvement-signal reviews; 74 Android and 19 iOS records', 2),
('reliable_20260831_v3', 'platform_specific_stability_investigations', 'driver_hos', 'governed_metric', 'Driver HOS, iOS vs Android', '19.3% vs 14.0%', 'Share of improvement-signal reviews; 21 iOS and 46 Android records', 3),
('reliable_20260831_v3', 'platform_specific_stability_investigations', 'fleet_stability_mix', 'governed_metric', 'Fleet stability after mix adjustment', '49.3% vs 45.0%', 'Android versus iOS share of improvement-signal reviews; raw all-review rates are 42.7% versus 20.0%', 4);

PRAGMA integrity_check;
