"""Google Places (New) tools for the offline mining pipeline.

Uses Places API (New) - the legacy Text Search/Place Details JSON API
(maps.googleapis.com/maps/api/place/...) returns REQUEST_DENIED on API keys
provisioned after Google's cutover and is being phased out; `places.googleapis.com/v1`
is what a freshly-created Maps Platform key actually has enabled.

Two calls, two different jobs:
- `text_search` discovers candidate venues (name/address/coords/place_id).
- `place_details` is the *only* source of real review quotes/rating for a
  venue - never invented by an LLM. Per Google's Places API terms, this
  content must not be cached indefinitely; callers should track
  `retrieved_at` and re-fetch periodically (see `POI.last_verified`).
"""

from __future__ import annotations

import datetime
import json
import os
import ssl
import urllib.error
import urllib.request

import certifi
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

_RETRYABLE = (urllib.error.URLError, TimeoutError)
_retry_policy = retry(
    retry=retry_if_exception_type(_RETRYABLE),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    reraise=True,
)

_BASE_URL = "https://places.googleapis.com/v1"

# certifi's CA bundle, not Python's own default: on at least one dev machine,
# Python's bundled cert store failed validation for a legitimate Let's
# Encrypt chain ("certificate has expired") that both the system OpenSSL and
# certifi validated fine - certifi is updated independently and more often.
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def _get_api_key() -> str:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is not configured.")
    return api_key


@_retry_policy
def _post_json(url: str, body: dict, field_mask: str) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": _get_api_key(),
            "X-Goog-FieldMask": field_mask,
            "User-Agent": "OdditiesExplorer/4.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CONTEXT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Places API (New) HTTP {e.code}: {detail}") from e


@_retry_policy
def _get_json(url: str, field_mask: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "X-Goog-Api-Key": _get_api_key(),
            "X-Goog-FieldMask": field_mask,
            "User-Agent": "OdditiesExplorer/4.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CONTEXT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Places API (New) HTTP {e.code}: {detail}") from e


def text_search(query: str, region: str = "us") -> list[dict]:
    """Discover candidate venues. Returns only what the API actually returned."""
    field_mask = "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount"
    body: dict = {"textQuery": query}
    if region:
        body["regionCode"] = region.upper()

    data = _post_json(f"{_BASE_URL}/places:searchText", body, field_mask)

    candidates = []
    for place in data.get("places", []):
        loc = place.get("location", {})
        name = (place.get("displayName") or {}).get("text")
        if not name:
            continue
        candidates.append(
            {
                "name": name,
                "address": place.get("formattedAddress"),
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
                "google_rating": place.get("rating"),
                "review_count": place.get("userRatingCount"),
                "place_id": place.get("id"),
            }
        )
    return candidates


def place_details(place_id: str) -> dict | None:
    """Real rating/review-count/review quotes for one venue. None if not found."""
    field_mask = "id,displayName,formattedAddress,location,rating,userRatingCount,reviews,googleMapsUri"
    try:
        result = _get_json(f"{_BASE_URL}/places/{place_id}", field_mask)
    except RuntimeError:
        return None

    if not result or "displayName" not in result:
        return None

    loc = result.get("location", {})
    retrieved_at = datetime.datetime.now(datetime.UTC).isoformat()

    reviews = [
        {
            "quote": (r.get("text") or {}).get("text", "").strip(),
            "rating": r.get("rating"),
            "source": "google_places",
            "retrieved_at": retrieved_at,
        }
        for r in result.get("reviews", [])
        if (r.get("text") or {}).get("text", "").strip()
    ]

    return {
        "name": (result.get("displayName") or {}).get("text"),
        "address": result.get("formattedAddress"),
        "latitude": loc.get("latitude"),
        "longitude": loc.get("longitude"),
        "google_rating": result.get("rating"),
        "review_count": result.get("userRatingCount"),
        "review_highlights": reviews,
        "google_maps_url": result.get("googleMapsUri", ""),
        "retrieved_at": retrieved_at,
    }
