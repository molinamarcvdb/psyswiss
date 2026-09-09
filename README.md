# PsySwiss — Swiss psychology jobs + EU licensing guide

Info-only tracker: scrape psychology/psychotherapy openings on **jobup.ch**
(structured schema.org `JobPosting` data), snapshot them in SQLite, and read the
**licensing guide** for the EU bachelor + master → Swiss psychotherapist path.

## 1. Setup (one command)

Requires Python ≥ 3.11 (`uv` auto-installs if missing).

```bash
./setup.sh        # or: make setup
make dev          # → http://127.0.0.1:8001 (guide is the landing tab)
```

## 2. Use

- **📖 Licensing guide** (landing page): 6-step path — PsyKo Master's recognition →
  clinical-psychology credits check → accredited postgraduate training (or foreign title
  recognition) → federal title + PsyReg → cantonal licence → insurance billing.
  Every section links the BAG/PsyKo source. Informational only, not legal advice.
- **💼 Jobs**: saved keyword searches over jobup.ch (defaults: `psychotherapie`,
  `psychology`), scrape with the blocking overlay, filter by text/contract, open any
  posting for the full description + source link + sighting history.
- **🔔 Changes**: new (first-seen) / back / gone (2 runs) / watching.

### Make targets

| Command | What it does |
|---|---|
| `make setup` / `./setup.sh` | uv sync + DB init |
| `make dev` (`PORT=8001`) | app with reload, scheduler off |
| `make run` | app, scheduler on |
| `make scrape` / `make scrape FORCE=--force` | scrape (30-min cooldown unless forced) |
| `make searches` | list saved searches |
| `make clean` | remove venv, caches, DB |

## 3. Portal coverage (verified 2026-09-09)

| Portal | Status |
|---|---|
| jobup.ch (~217 psychology ads) | ✅ tracked — list + `JobPosting` JSON-LD details |
| jobs.ch (~368 therapy ads, same operator) | list pages readable, details not yet wired |
| PsychJOB.ch (~36 ads) | ⛔ bot-challenge on Fetcher — check manually |
| therapie-jobs.ch (~134 ads) | ⛔ HTTP 403 — check manually |
| SBAP / fhjobs.ch | association board, manual |

## 4. Scheduling

One scheduler per DB — in-app (`SCRAPE_INTERVAL_HOURS`, default 12) or cron:

```bash
0 */6 * * * cd /opt/psyswiss && DATA_DIR=/opt/psyswiss/data uv run python -m app.cli scrape --force
```

Env: `DATA_DIR`, `DB_FILE`, `SCRAPE_INTERVAL_HOURS`, `SCRAPE_COOLDOWN_SECS`, `RUN_ON_STARTUP`.

## 5. API

- `GET /api/guide` — steps, sections, sources, portals
- Searches: `GET/POST /api/searches`, `PATCH/DELETE /api/searches/{id}`
- `POST /api/scrape[?search_id=N][&force=true]`, `GET /api/runs`
- `GET /api/stats|changes|listings|facets?search_id=N` (listings: `q, type, sort, limit, count_only`)
- `GET /api/job/{ext_id}?search_id=N`

Scraper: [Scrapling](https://github.com/d4vinci/Scrapling) `Fetcher` (Chrome fingerprint).
Detail pages are polite (1.5s gaps); keep `pages ≤ 3`, interval ≥ 6h.
