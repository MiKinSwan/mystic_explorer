"""Offline mining pipeline: scout -> enrich -> dedupe/score -> history research.

Only one step touches an LLM: `research_history`, and only to summarize
*grounded* Google Search results (via ADK's built-in `google_search` tool).
If the search doesn't return real citations, the summary is discarded rather
than kept as ungrounded prose - this is what keeps `history_and_lore` honest.
Everything else (scouting, rating/review-count/review-quotes via Places
Place Details, dedup, scoring) is either a direct API pull or plain Python -
no LLM invention anywhere in this file.

Google Places usage is OFF BY DEFAULT (both `scout_state`'s Text Search and
`enrich_with_place_details`'s Place Details calls require an explicit
`use_google_places=True`). A full 51-state run with it on incurred a real,
unexpectedly large bill - Place Details with the `reviews` field lands in
Google's "Enterprise + Atmosphere" pricing tier, and that call was made once
per Google-sourced candidate, unthrottled. OSM Overpass mining (free) and
Gemini history research (a separate, much cheaper API) are unaffected by
this flag and remain on by default.
"""

from __future__ import annotations

import datetime
import logging
import uuid

from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.runners import InMemoryRunner
from google.adk.tools.google_search_tool import google_search
from google.genai import types
from pydantic import BaseModel
from rapidfuzz import fuzz

from app.config import (
    KEYWORD_CATEGORY_MAP,
    MODEL,
    NICHE_SEARCH_KEYWORDS,
    OSM_TAG_CATEGORY_MAP,
    STATE_BBOXES,
)
from app.geo_utils import get_super_category, haversine_miles
from app.tools.google_places import place_details, text_search
from app.tools.osm import overpass_search

logger = logging.getLogger("oddities_explorer.mining")

DEDUPE_NAME_THRESHOLD = 85  # rapidfuzz token_sort_ratio (0-100)
DEDUPE_DISTANCE_MILES = 0.15  # ~250m


class Candidate(BaseModel):
    """A raw, tool-grounded discovery - nothing here is LLM-invented."""

    name: str
    category: str
    address: str
    state: str
    latitude: float
    longitude: float
    place_id: str | None = None
    osm_id: str | None = None
    source_types: list[str] = []
    google_rating: float | None = None
    review_count: int | None = None
    review_highlights: list[dict] = []
    google_maps_url: str = ""
    description: str = ""
    source_citations: list[dict] = []
    history_and_lore: str = ""


def _osm_category(tags: dict) -> str:
    for (key, value), category in OSM_TAG_CATEGORY_MAP.items():
        if tags.get(key) == value:
            return category
    return "Oddities & Creepy Galleries"


def scout_state(state: str, use_google_places: bool = False) -> list[Candidate]:
    """Discover raw candidates from OSM Overpass, plus Google Places Text
    Search if `use_google_places` is explicitly True.

    Google Places defaults to OFF: a full-run cost incident (Place Details
    "Enterprise + Atmosphere" pricing, called once per Google-sourced
    candidate across all 51 states) burned real money before this default
    was added. Callers must opt in deliberately - see `--enable-google-places`
    in app/pipeline/mine.py.
    """
    candidates: list[Candidate] = []

    if use_google_places:
        for keyword in NICHE_SEARCH_KEYWORDS:
            category = KEYWORD_CATEGORY_MAP.get(keyword, "General Specialty Shops")
            try:
                hits = text_search(f"{keyword} in {state}", region="us")
            except Exception:
                logger.exception("text_search failed for %r in %s", keyword, state)
                continue
            for hit in hits:
                if hit.get("latitude") is None or not hit.get("name"):
                    continue
                candidates.append(
                    Candidate(
                        name=hit["name"],
                        category=category,
                        address=hit.get("address") or "",
                        state=state,
                        latitude=hit["latitude"],
                        longitude=hit["longitude"],
                        place_id=hit.get("place_id"),
                        source_types=["google_places"],
                        google_rating=hit.get("google_rating"),
                        review_count=hit.get("review_count"),
                    )
                )

    bbox = STATE_BBOXES.get(state)
    if bbox:
        try:
            osm_hits = overpass_search(bbox)
        except Exception:
            logger.exception("overpass_search failed for %s", state)
            osm_hits = []
        for hit in osm_hits:
            citations = []
            if hit.get("wikipedia"):
                citations.append(
                    {"url": f"https://en.wikipedia.org/wiki/{hit['wikipedia'].split(':')[-1]}", "source": "osm_wikipedia_tag"}
                )
            if hit.get("website"):
                citations.append({"url": hit["website"], "source": "osm_website_tag"})
            candidates.append(
                Candidate(
                    name=hit["name"],
                    category=_osm_category(hit.get("osm_tags", {})),
                    address=hit.get("address") or "",
                    state=state,
                    latitude=hit["latitude"],
                    longitude=hit["longitude"],
                    osm_id=hit.get("osm_id"),
                    source_types=["osm"],
                    description=hit.get("description", ""),
                    source_citations=citations,
                )
            )

    return candidates


def enrich_with_place_details(candidate: Candidate) -> Candidate:
    """Pulls real rating/review-count/review quotes for a Google-sourced
    candidate. Deterministic API call, not an LLM - nothing invented."""
    if not candidate.place_id:
        return candidate
    try:
        details = place_details(candidate.place_id)
    except Exception:
        logger.exception("place_details failed for place_id=%s", candidate.place_id)
        return candidate
    if not details:
        return candidate

    candidate.google_rating = details.get("google_rating", candidate.google_rating)
    candidate.review_count = details.get("review_count", candidate.review_count)
    candidate.review_highlights = details.get("review_highlights", [])
    candidate.google_maps_url = details.get("google_maps_url", "")
    return candidate


def dedupe_and_score(candidates: list[Candidate]) -> list[Candidate]:
    """Merges same-venue records across sources; computes hidden-gem/confidence
    scores. Pure Python - no LLM call."""
    merged: list[Candidate] = []

    for cand in candidates:
        match = None
        for existing in merged:
            if existing.state != cand.state:
                continue
            dist = haversine_miles(
                existing.latitude, existing.longitude, cand.latitude, cand.longitude
            )
            if dist > DEDUPE_DISTANCE_MILES:
                continue
            name_score = fuzz.token_set_ratio(existing.name.lower(), cand.name.lower())
            if name_score >= DEDUPE_NAME_THRESHOLD:
                match = existing
                break

        if match is None:
            merged.append(cand)
            continue

        # Merge: keep richer fields, union sources/citations.
        match.source_types = list(set(match.source_types + cand.source_types))
        match.source_citations = match.source_citations + [
            c for c in cand.source_citations if c not in match.source_citations
        ]
        if not match.google_rating and cand.google_rating:
            match.google_rating = cand.google_rating
            match.review_count = cand.review_count
            match.review_highlights = cand.review_highlights
            match.google_maps_url = cand.google_maps_url or match.google_maps_url
        if not match.description and cand.description:
            match.description = cand.description

    return merged


def compute_scores(candidate: Candidate) -> tuple[float, float, bool]:
    """hidden_gem_score, confidence_score, is_hidden_gem - all derived from
    real signals (review_count, source diversity), never an LLM guess."""
    review_count = candidate.review_count or 0
    # Fewer Google reviews (or none, i.e. Google doesn't even list it) = more
    # of a hidden gem. Capped so a 0-review OSM-only find scores highest.
    hidden_gem_score = 1.0 / (1.0 + review_count / 25.0)
    if "osm" in candidate.source_types and "google_places" not in candidate.source_types:
        hidden_gem_score = min(1.0, hidden_gem_score + 0.2)

    confidence_score = min(1.0, 0.4 * len(set(candidate.source_types)) + 0.15 * len(candidate.source_citations))
    if candidate.place_id:
        confidence_score = min(1.0, confidence_score + 0.3)

    is_hidden_gem = hidden_gem_score >= 0.5
    return hidden_gem_score, confidence_score, is_hidden_gem


# --- History research: the one LLM step, grounded-only ---------------------

_history_agent = LlmAgent(
    name="history_research_agent",
    model=MODEL,
    instruction=(
        "You research the real, documented history or paranormal lore of a specific "
        "named venue using Google Search. Search for the venue by name and address. "
        "If you find real, citable information (news articles, Wikipedia, local history "
        "sites, ghost-tour operator pages, etc.), summarize it in 2-3 sentences. "
        "If your search returns nothing substantive and specific to this exact venue, "
        "reply with exactly: NO_SOURCE_FOUND. Never guess, invent, or generalize from "
        "similar-sounding places - only report what your search actually surfaced."
    ),
    tools=[google_search],
)
_history_runner = InMemoryRunner(app=App(root_agent=_history_agent, name="history_research"))


async def research_history(candidate: Candidate) -> Candidate:
    """The only LLM call in the pipeline. Keeps history_and_lore empty unless
    Google Search grounding actually returned citable source URLs."""
    query = f"{candidate.name}, {candidate.address} - history OR haunted OR paranormal lore"
    session = await _history_runner.session_service.create_session(
        app_name="history_research", user_id="miner"
    )

    text_parts: list[str] = []
    citation_urls: set[str] = set()

    async for event in _history_runner.run_async(
        user_id="miner",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part.from_text(text=query)]),
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    text_parts.append(part.text)
        grounding = getattr(event, "grounding_metadata", None)
        if grounding and grounding.grounding_chunks:
            for chunk in grounding.grounding_chunks:
                if chunk.web and chunk.web.uri:
                    citation_urls.add(chunk.web.uri)

    summary = "".join(text_parts).strip()

    # Fail closed: no real citations => don't keep the text, however
    # plausible-sounding it is.
    if not citation_urls or "NO_SOURCE_FOUND" in summary:
        return candidate

    candidate.history_and_lore = summary
    candidate.source_citations = candidate.source_citations + [
        {"url": url, "source": "google_search_grounding"} for url in citation_urls
    ]
    return candidate


def to_poi_row(candidate: Candidate) -> dict:
    """Shapes a Candidate into the dict app/db/models.POI expects."""
    hidden_gem_score, confidence_score, is_hidden_gem = compute_scores(candidate)
    now = datetime.datetime.now(datetime.UTC)

    return {
        "id": uuid.uuid4(),
        "name": candidate.name,
        "category": candidate.category,
        "super_category": get_super_category(candidate.category),
        "vibe_tags": [],
        "address": candidate.address,
        "city": None,
        "state": candidate.state,
        "latitude": candidate.latitude,
        "longitude": candidate.longitude,
        "location": f"POINT({candidate.longitude} {candidate.latitude})",
        "description": candidate.description or None,
        "history_and_lore": candidate.history_and_lore or None,
        "source_citations": candidate.source_citations,
        "review_highlights": candidate.review_highlights,
        "google_rating": candidate.google_rating,
        "review_count": candidate.review_count,
        "specialties": [],
        "is_hidden_gem": is_hidden_gem,
        "hidden_gem_score": hidden_gem_score,
        "confidence_score": confidence_score,
        "google_place_id": candidate.place_id,
        "google_maps_url": candidate.google_maps_url,
        "is_publicly_accessible": True,
        "last_verified": now,
    }
