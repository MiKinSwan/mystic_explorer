"""Batch mining pipeline CLI.

    uv run python -m app.pipeline.mine --states all
    uv run python -m app.pipeline.mine --states PA,MA --dry-run
    uv run python -m app.pipeline.mine --states all --max-history-lookups-per-state 15

Resumable: a state already recorded as `status="success"` in `mining_runs` is
skipped on the next invocation unless --force is passed. A failure in one
state is logged to `mining_runs.error_message` and the loop continues to the
next state, so a 50-state run survives a bad state or a rate limit.

Google Places (Text Search + Place Details) is OFF by default - pass
--enable-google-places to turn it back on. It's off because a full-run bill
came in far higher than expected (Place Details with `reviews` is priced at
Google's "Enterprise + Atmosphere" tier, called once per Google-sourced
candidate, unthrottled, across all 51 states). OSM mining (free) and Gemini
history research still run normally either way.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import logging

from dotenv import load_dotenv
from rapidfuzz import fuzz

from app.agents.mining import (
    Candidate,
    dedupe_and_score,
    enrich_with_place_details,
    research_history,
    scout_state,
    to_poi_row,
)
from app.config import US_STATES
from app.db.models import POI, MiningRun
from app.db.session import get_session
from app.geo_utils import haversine_miles
from app.pipeline.seed_candidates import SEED_CANDIDATES

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("oddities_explorer.pipeline")

DEFAULT_MAX_HISTORY_LOOKUPS_PER_STATE = 30
MATCH_DISTANCE_MILES = 0.15
MATCH_NAME_THRESHOLD = 85

# Fields worth overwriting on an existing row when a fresh mining pass finds
# a non-empty value. google_rating/review_count are always refreshed (a
# rating going to None on a since-delisted place is meaningful).
_MERGE_FIELDS = (
    "name",
    "category",
    "super_category",
    "address",
    "city",
    "latitude",
    "longitude",
    "description",
    "history_and_lore",
    "source_citations",
    "review_highlights",
    "google_rating",
    "review_count",
    "is_hidden_gem",
    "hidden_gem_score",
    "confidence_score",
    "google_place_id",
    "google_maps_url",
    "last_verified",
)


def _seed_candidates_for(state: str) -> list[Candidate]:
    return [
        Candidate(
            name=s["name"],
            category=s["category"],
            address=s["address"],
            state=state,
            latitude=s["latitude"],
            longitude=s["longitude"],
            source_types=["manual_seed"],
        )
        for s in SEED_CANDIDATES
        if s["state"] == state
    ]


def _find_existing_match(session, state: str, cand: Candidate) -> POI | None:
    for row in session.query(POI).filter(POI.state == state).all():
        dist = haversine_miles(row.latitude, row.longitude, cand.latitude, cand.longitude)
        if dist > MATCH_DISTANCE_MILES:
            continue
        if fuzz.token_set_ratio(row.name.lower(), cand.name.lower()) >= MATCH_NAME_THRESHOLD:
            return row
    return None


def persist_candidates(session, state: str, candidates: list[Candidate]) -> int:
    upserted = 0
    for cand in candidates:
        row_data = to_poi_row(cand)

        existing = None
        if cand.place_id:
            existing = (
                session.query(POI)
                .filter(POI.google_place_id == cand.place_id)
                .one_or_none()
            )
        if existing is None:
            existing = _find_existing_match(session, state, cand)

        if existing is not None:
            for field in _MERGE_FIELDS:
                value = row_data[field]
                if value not in (None, "", []) or field in ("google_rating", "review_count"):
                    setattr(existing, field, value)
            existing.location = row_data["location"]
        else:
            session.add(POI(**row_data))
        upserted += 1

    session.commit()
    return upserted


async def mine_state(
    session,
    state: str,
    max_history_lookups: int,
    dry_run: bool,
    use_google_places: bool = False,
) -> tuple[int, int]:
    candidates = scout_state(state, use_google_places=use_google_places) + _seed_candidates_for(
        state
    )
    logger.info("[%s] scouted %d raw candidates", state, len(candidates))

    if use_google_places:
        candidates = [enrich_with_place_details(c) for c in candidates]
    merged = dedupe_and_score(candidates)
    logger.info("[%s] %d candidates after dedupe", state, len(merged))

    # History research is the one LLM+API-cost step - cap it per state and
    # prioritize candidates with fewer Google reviews (most likely to be
    # genuine hidden gems worth writing up; also the ones Google won't have
    # already told the user much about).
    merged.sort(key=lambda c: (c.review_count or 0))
    researched = 0
    for cand in merged:
        if researched >= max_history_lookups:
            break
        try:
            await research_history(cand)
        except Exception:
            logger.exception("[%s] history research failed for %r", state, cand.name)
        researched += 1

    if dry_run:
        for cand in merged[:5]:
            logger.info(
                "[%s] DRY RUN sample: %s | rating=%s reviews=%s citations=%d",
                state,
                cand.name,
                cand.google_rating,
                cand.review_count,
                len(cand.source_citations),
            )
        return len(candidates), 0

    upserted = persist_candidates(session, state, merged)
    return len(candidates), upserted


async def run(
    states: list[str],
    max_history_lookups: int,
    dry_run: bool,
    force: bool,
    use_google_places: bool = False,
) -> None:
    if dry_run:
        # No DB touched at all in dry-run mode, so it works before Phase 0
        # (Cloud SQL) is even set up.
        for state in states:
            await mine_state(
                None, state, max_history_lookups, dry_run=True, use_google_places=use_google_places
            )
        return

    session = get_session()
    try:
        for state in states:
            run_row = session.query(MiningRun).filter(MiningRun.state == state).one_or_none()
            if run_row is None:
                run_row = MiningRun(
                    state=state, status="pending", venues_found=0, venues_upserted=0
                )
                session.add(run_row)
                session.commit()

            if run_row.status == "success" and not force:
                logger.info(
                    "[%s] already mined successfully, skipping (use --force to re-run)",
                    state,
                )
                continue

            run_row.status = "running"
            run_row.started_at = datetime.datetime.now(datetime.UTC)
            run_row.error_message = None
            session.commit()

            try:
                found, upserted = await mine_state(
                    session,
                    state,
                    max_history_lookups,
                    dry_run,
                    use_google_places=use_google_places,
                )
                run_row.status = "success"
                run_row.venues_found = found
                run_row.venues_upserted = upserted
                run_row.completed_at = datetime.datetime.now(datetime.UTC)
                session.commit()
                logger.info("[%s] done: found=%d upserted=%d", state, found, upserted)
            except Exception as e:
                session.rollback()
                logger.exception("[%s] mining failed", state)
                run_row.status = "failed"
                run_row.error_message = str(e)[:2000]
                session.commit()
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Mine oddities/paranormal venues into Postgres.")
    parser.add_argument(
        "--states", default="all", help="Comma-separated state abbreviations, or 'all'"
    )
    parser.add_argument(
        "--max-history-lookups-per-state",
        type=int,
        default=DEFAULT_MAX_HISTORY_LOOKUPS_PER_STATE,
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Scout/enrich/score but don't write to the DB"
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-mine states already marked successful"
    )
    parser.add_argument(
        "--enable-google-places",
        action="store_true",
        help=(
            "Turn on Google Places Text Search + Place Details (off by default - "
            "these are the paid calls responsible for a real, unexpectedly large "
            "bill in a prior run; Place Details with the reviews field is priced "
            "at Google's 'Enterprise + Atmosphere' tier). OSM mining and Gemini "
            "history research are unaffected and run either way."
        ),
    )
    args = parser.parse_args()

    if args.states.lower() == "all":
        states = [abbr for abbr, _ in US_STATES]
    else:
        states = [s.strip().upper() for s in args.states.split(",") if s.strip()]

    if args.enable_google_places:
        logger.warning(
            "Google Places is ENABLED for this run - Place Details (reviews field) "
            "is a paid, per-call cost at Google's 'Enterprise + Atmosphere' tier. "
            "Make sure you actually intend this before it runs across many states."
        )

    asyncio.run(
        run(
            states,
            args.max_history_lookups_per_state,
            args.dry_run,
            args.force,
            use_google_places=args.enable_google_places,
        )
    )


if __name__ == "__main__":
    main()
