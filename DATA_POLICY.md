# Public data policy

## Allowed in this repository

- Aggregate counts with explicit denominators
- Aggregate rates and time comparisons
- Approved theme definitions and claim boundaries
- Approved, redacted evidence excerpts
- Hashed or non-identifying review keys
- Source coverage and freshness metadata
- Taxonomy, methodology, and validation results
- Version and content-hash manifests
- Reproducible code and sanitized test fixtures

## Must remain private

- Raw Apple or Google collector responses
- The populated operational SQLite database
- Reviewer display names
- Bulk verbatim review text
- Unredacted audit and adjudication batches
- Credentials, tokens, secrets, or private storage locations

## Publication rule

Only files written to `public-data/` by the governed exporter may be consumed by the
site. The exporter must run privacy, schema, denominator, and static-release checks.
A failed run cannot replace the last successful public site.

## Evidence excerpts

Published excerpts must be necessary to understand a finding, short enough to reduce
re-identification risk, stripped of reviewer identity and incidental personal
information, and associated with a non-identifying evidence key. Bulk review text is
never a public-site dependency.
