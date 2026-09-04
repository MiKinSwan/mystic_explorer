"""OpenStreetMap / Overpass tool - the actual "hidden gem" lever.

Google's Places index is popularity/business-registration biased. OSM has
long-tail POIs anyone can map (an abandoned asylum, a witchcraft shop run out
of someone's storefront with no online presence) that Places will never
surface. This queries the public Overpass API directly - no API key needed.
"""

from __future__ import annotations

import json
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

from app.config import OSM_TAG_CATEGORY_MAP

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# (OSM key, OSM value) pairs that map to our niche categories - sourced from
# the single OSM_TAG_CATEGORY_MAP in app/config.py so the query filter and
# the category classification never drift apart.
OSM_TAG_QUERIES: list[tuple[str, str | None]] = list(OSM_TAG_CATEGORY_MAP.keys())

_RETRYABLE = (urllib.error.URLError, TimeoutError)
_retry_policy = retry(
    retry=retry_if_exception_type(_RETRYABLE),
    # 6 attempts, not 4: TLS failures against overpass-api.de have shown up
    # intermittently (transient - direct certificate checks against both of
    # its backend IPs came back valid) and tend to self-heal on retry.
    stop=stop_after_attempt(6),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    reraise=True,
)


def _build_query(bbox: tuple[float, float, float, float], tag_filters: list[tuple[str, str | None]]) -> str:
    south, west, north, east = bbox
    clauses = []
    for key, value in tag_filters:
        tag_expr = f'["{key}"="{value}"]' if value else f'["{key}"]'
        clauses.append(f"  node{tag_expr}({south},{west},{north},{east});")
        clauses.append(f"  way{tag_expr}({south},{west},{north},{east});")
    body = "\n".join(clauses)
    return f"[out:json][timeout:60];\n(\n{body}\n);\nout center tags;"


_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


@_retry_policy
def _fetch(query: str) -> dict:
    data = query.encode("utf-8")
    req = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={
            "User-Agent": "OdditiesExplorer/4.0",
            "Content-Type": "text/plain",
        },
    )
    # Explicit certifi CA bundle, not Python's own default: on this machine
    # Python's bundled cert store fails validation for overpass-api.de's
    # current Let's Encrypt chain ("certificate has expired") even though
    # both the system OpenSSL and certifi's bundle validate it fine -
    # certifi is updated independently and far more often.
    with urllib.request.urlopen(req, timeout=65, context=_SSL_CONTEXT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def overpass_search(
    bbox: tuple[float, float, float, float],
    tag_filters: list[tuple[str, str | None]] | None = None,
) -> list[dict]:
    """Query OSM within (south, west, north, east). Returns raw tagged POIs."""
    query = _build_query(bbox, tag_filters or OSM_TAG_QUERIES)
    data = _fetch(query)

    results = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue  # unnamed nodes are almost always noise, not real venues

        if el.get("type") == "node":
            lat, lon = el.get("lat"), el.get("lon")
        else:
            center = el.get("center", {})
            lat, lon = center.get("lat"), center.get("lon")
        if lat is None or lon is None:
            continue

        addr_parts = [
            tags.get("addr:housenumber", ""),
            tags.get("addr:street", ""),
            tags.get("addr:city", ""),
            tags.get("addr:state", ""),
            tags.get("addr:postcode", ""),
        ]
        address = " ".join(p for p in addr_parts if p).strip()

        results.append(
            {
                "name": name,
                "address": address,
                "latitude": lat,
                "longitude": lon,
                "osm_id": f"{el.get('type')}/{el.get('id')}",
                "osm_tags": tags,
                # Real, present-in-source description text only.
                "description": tags.get("description", ""),
                "wikipedia": tags.get("wikipedia", ""),
                "website": tags.get("website", tags.get("contact:website", "")),
            }
        )
    return results
