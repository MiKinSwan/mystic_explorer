# Mystic Shadow

Find real haunted hotels, witchcraft/occult shops, crystal & apothecary stores, oddity
galleries, castles, ruins, asylums, and ghost tours — sorted into three simple categories:
**🛌 Stay, 🛍️ Shop, 🏰 Explore.**

## Purpose

Most "haunted places" content online is either a generic top-10 listicle of the same famous
spots, or AI-generated content that invents ghost stories for real businesses. This project
does neither. It **mines real venues from real sources**, computes a **hidden-gem score** so
genuinely obscure/undiscovered places surface ahead of tourist traps, and never presents
invented content as fact — if no real history or review exists for a place, the app shows
nothing rather than making something up.

That last point isn't a minor detail — it's the whole reason this project looks the way it
does. An earlier version of this app used an LLM to freely generate "customer reviews" and
"historical lore" for real, named businesses. That's fabrication with someone's real business
name attached to it, and it's the thing this rewrite specifically exists to not do.

## How the mining works

Nothing in the app talks to an LLM at request time. A **batch pipeline**
(`app/pipeline/mine.py`) runs ahead of time, mines real data, and writes it to Postgres. The
web app then just *reads* that stored data — instant, and nothing it shows was invented on
the spot.

Per state, the pipeline runs four stages:

1. **Scout** (`app/agents/mining.py::scout_state`, no LLM) — discovers candidate venues from
   the **OpenStreetMap Overpass API** (free, always on) by map tag (`shop=esoteric`,
   `historic=ruins`, `building=asylum`, etc.). This is what surfaces places that don't have
   any online business presence at all — an abandoned asylum, a shop with 1 review — because
   OSM tags a physical *location*, not a business listing.
2. **Dedupe & score** (`dedupe_and_score`, `compute_scores` — pure Python, no LLM) — merges
   the same venue found by multiple sources (fuzzy name + distance matching), then computes:
   - `hidden_gem_score` — higher for lower review counts and for venues only OSM knows about
   - `confidence_score` — higher when multiple independent sources agree it's real
3. **History research** (`research_history` — an *optional* LLM step, off by default) — uses
   Gemini's built-in Google Search grounding tool to look for real, citable history/lore for a
   venue. If the search doesn't return real source URLs, the field is left **empty** — a
   summary is never kept without a citation behind it.

The **9,945 places currently in the live database were mined this way**: OSM only, history
research capped at 0 — a fully free run, no paid API calls.

### Google Places (New) — available, but not used for the current dataset

`app/tools/google_places.py` can additionally pull real Google ratings, review counts, and
attributed review quotes via Places API (New). It's real, working code, but both the scout
step's Text Search and the Place Details enrichment step require an explicit
`--enable-google-places` flag — **it is off by default and was not used to build the dataset
this app currently serves.** Reason: a full 51-state run with it enabled once cost **$194** in
a single go — Place Details with the `reviews` field is priced at Google's "Enterprise +
Atmosphere" tier, called once per Google-sourced candidate, unthrottled. Turn it on only if
you understand that cost model.

### Data quality: known gaps

- **No address for ~40% of venues.** Many OSM-only finds (military ruins, historic markers)
  are just GPS points that never had a street address to begin with — not a bug, just what
  the free data has. The app shows real coordinates and a working map link either way.
- **Keyword-matched mislabeling.** Early Google-sourced data included mainstream venues that
  matched a search keyword by text only (e.g. "The Shops at Crystals," a Las Vegas luxury
  mall, matched a "crystal shop" search purely because of its name). A cleanup pass removed
  ~61 of these; more may exist. `hidden_gem_score` naturally deprioritizes them either way.

## Project Structure

```
oddities-explorer/
├── fast_api_app.py              # The whole app: /api/search reads the mined DB, / serves the UI
├── app/
│   ├── config.py                 # Categories, state bounding boxes, search keywords,
│   │                              #   OSM tag map, per-category "what to do here" notes
│   ├── geo_utils.py               # Shared category/distance/state-matching helpers
│   ├── rendering.py               # Markdown dossier renderer used by /api/search
│   ├── db/
│   │   ├── models.py               # POI + MiningRun tables (Postgres/PostGIS)
│   │   ├── session.py              # Postgres engine/session (DATABASE_URL - Supabase or any
│   │   │                          #   standard host)
│   │   └── queries.py              # Read-side query used by /api/search
│   ├── tools/
│   │   ├── osm.py                  # OpenStreetMap Overpass tool (free, always on)
│   │   └── google_places.py        # Places API (New) tools (paid, opt-in only - see above)
│   ├── agents/
│   │   └── mining.py               # scout / dedupe+score / optional history-research
│   └── pipeline/
│       ├── mine.py                 # Batch mining CLI - the entrypoint you actually run
│       └── seed_candidates.py      # Manually-added known venues (guaranteed inclusion)
├── alembic/                       # DB migrations (`alembic upgrade head`)
├── tests/
│   └── unit/                       # Pure-Python logic tests (dedupe, scoring, category
│                                  #   mapping) - no network/DB needed
├── Dockerfile                      # Production container image
└── pyproject.toml                 # Dependencies
```

## One-time setup: Supabase + first mining run

1. Create a free [Supabase](https://supabase.com) project. In the SQL editor, run
   `create extension if not exists postgis;`. Grab the connection string from
   Project Settings > Database (psycopg, `sslmode=require`) and set it as
   `DATABASE_URL` in `.env` (see `.env.example`).
2. `uv run python -m alembic upgrade head` — creates the `pois` and `mining_runs` tables.
3. `uv run python -m app.pipeline.mine --states PA --dry-run` — sanity-check the pipeline
   without writing to the DB.
4. `uv run python -m app.pipeline.mine --states all --max-history-lookups-per-state 0` —
   mine all 50 states + DC for free (OSM only, no LLM cost). Resumable: re-running skips
   states already mined successfully (add `--force` to re-mine).
5. `uv run python -m uvicorn fast_api_app:fastapi_app --host 127.0.0.1 --port 8000` —
   run the web app, then open `http://127.0.0.1:8000`.

> **Tip:** on this machine, prefer `uv run python -m <tool>` over `uv run <tool>` (e.g.
> `uv run python -m pytest`, `uv run python -m alembic`) — the bare console-script form hangs
> for minutes here, likely due to OneDrive sync overhead on this project's folder.

## Requirements

- **uv**: Python package manager — [Install](https://docs.astral.sh/uv/getting-started/installation/)
- **A Postgres database with PostGIS** (e.g. a free Supabase project) — see setup above
- **`GOOGLE_MAPS_API_KEY`** with Places API (New) enabled — only needed if you opt into
  `--enable-google-places` (off by default, see above)
- **`GEMINI_API_KEY`** (or Vertex AI credentials) — only needed if you run mining with
  `--max-history-lookups-per-state` above 0 (the history-research step)

## Tests

```bash
uv run python -m pytest tests/unit
```

Pure-Python logic tests for the dedupe, scoring, and category-mapping logic — no network or
database required.

## Deploying

The `Dockerfile` builds a production image that runs `fast_api_app.py` directly
(`uvicorn fast_api_app:fastapi_app`). Any host that can run a Dockerfile and give you a place
to set the env vars from `.env.example` works - e.g. Render's free web service tier.
