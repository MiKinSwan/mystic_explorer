"""Unit tests for the pure-Python parts of the mining pipeline: no network,
no DB, no LLM. These are the pieces that must stay deterministic and honest -
dedup shouldn't drop real venues, and scoring shouldn't be gameable by an
LLM (it isn't LLM-derived at all)."""

from app.agents.mining import Candidate, compute_scores, dedupe_and_score
from app.geo_utils import get_super_category, matches_target_state


def test_dedupe_merges_same_venue_across_sources() -> None:
    google_hit = Candidate(
        name="The Veiled Crow",
        category="Witchcraft & Occult Shops",
        address="1862 Broad St, Cranston, RI 02905",
        state="RI",
        latitude=41.7749573,
        longitude=-71.3983136,
        place_id="abc123",
        source_types=["google_places"],
        google_rating=4.8,
        review_count=96,
    )
    osm_hit = Candidate(
        name="Veiled Crow",  # near-duplicate name, same coordinates
        category="Witchcraft & Occult Shops",
        address="1862 Broad St, Cranston, RI",
        state="RI",
        latitude=41.77496,
        longitude=-71.39833,
        source_types=["osm"],
        description="A local witchcraft and metaphysical shop.",
    )

    merged = dedupe_and_score([google_hit, osm_hit])

    assert len(merged) == 1
    result = merged[0]
    assert set(result.source_types) == {"google_places", "osm"}
    assert result.google_rating == 4.8
    assert result.description == "A local witchcraft and metaphysical shop."


def test_dedupe_keeps_distinct_venues_separate() -> None:
    a = Candidate(
        name="The Veiled Crow", category="Witchcraft & Occult Shops",
        address="1862 Broad St, Cranston, RI", state="RI",
        latitude=41.7749573, longitude=-71.3983136, source_types=["osm"],
    )
    b = Candidate(
        name="Mystic Moon", category="Witchcraft & Occult Shops",
        address="436 Main Rd, Tiverton, RI", state="RI",
        latitude=41.6616809, longitude=-71.1898423, source_types=["osm"],
    )

    merged = dedupe_and_score([a, b])

    assert len(merged) == 2


def test_hidden_gem_score_favors_fewer_reviews() -> None:
    obscure = Candidate(
        name="Obscure Shop", category="Witchcraft & Occult Shops", address="",
        state="RI", latitude=0, longitude=0, source_types=["osm"], review_count=None,
    )
    popular = Candidate(
        name="Popular Shop", category="Witchcraft & Occult Shops", address="",
        state="RI", latitude=0, longitude=0, source_types=["google_places"],
        place_id="x", review_count=500,
    )

    obscure_gem_score, _, obscure_is_gem = compute_scores(obscure)
    popular_gem_score, _, popular_is_gem = compute_scores(popular)

    assert obscure_gem_score > popular_gem_score
    assert obscure_is_gem is True
    assert popular_is_gem is False


def test_confidence_score_rewards_multiple_sources_and_place_id() -> None:
    single_source = Candidate(
        name="A", category="Witchcraft & Occult Shops", address="", state="RI",
        latitude=0, longitude=0, source_types=["osm"],
    )
    multi_source = Candidate(
        name="B", category="Witchcraft & Occult Shops", address="", state="RI",
        latitude=0, longitude=0, source_types=["osm", "google_places"], place_id="x",
    )

    _, single_confidence, _ = compute_scores(single_source)
    _, multi_confidence, _ = compute_scores(multi_source)

    assert multi_confidence > single_confidence


def test_get_super_category_maps_granular_categories() -> None:
    assert get_super_category("Haunted Hotels & Motels") == "Stay"
    assert get_super_category("Witchcraft & Occult Shops") == "Shop"
    assert get_super_category("Asylums, Sanatoriums & Ruins") == "Explore"


def test_matches_target_state_accepts_abbreviation_or_full_name() -> None:
    assert matches_target_state("10 W Ferry St, New Hope, PA 18938", "PA") is True
    assert matches_target_state("10 W Ferry St, New Hope, Pennsylvania", "pa") is True
    assert matches_target_state("10 W Ferry St, New Hope, NY 10001", "PA") is False
