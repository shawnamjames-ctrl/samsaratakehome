# Repository map

| Path | Purpose | Refresh cadence |
| --- | --- | --- |
| `docs/` | Built GitHub Pages site | After a successful approved or monitoring build |
| `deliverables/` | CPO memo and methodology PDFs for direct review | Approved analytical release only |
| `content/` | Static approved executive and methodological content | Approved analytical release only |
| `public-data/releases/` | Frozen privacy-safe analytical releases | Approved analytical release only |
| `public-data/dashboard/` | Daily privacy-safe monitoring files | Successful daily run |
| `pipeline/` | Collection, normalization, export, and validation code | Version controlled |
| `schemas/` | Machine-readable public-output contracts | Deliberate contract change |
| `tests/fixtures/` | Synthetic or sanitized fixtures | Version controlled |
| `tests/` | Unit and end-to-end checks | Version controlled |
| `.github/workflows/` | Validation, monitoring, and Pages deployment | Version controlled |

The private operational database and raw snapshots live outside this repository.
