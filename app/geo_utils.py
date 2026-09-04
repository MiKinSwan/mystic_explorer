"""Shared geo/category helpers used by the live agent, the mining pipeline,
and the DB-backed read API - kept dependency-free of all three so none of
them have to import each other."""

from __future__ import annotations

import math
import re

from app.config import SUPER_CATEGORY_MAP


def get_super_category(sub_cat: str) -> str:
    sub_lower = sub_cat.lower()
    if (
        "hotel" in sub_lower
        or "motel" in sub_lower
        or "inn" in sub_lower
        or "stay" in sub_lower
        or "bed" in sub_lower
    ):
        return "Stay"
    elif (
        "shop" in sub_lower
        or "apothecary" in sub_lower
        or "crystal" in sub_lower
        or "oddity" in sub_lower
        or "gallery" in sub_lower
        or "store" in sub_lower
        or "specialty" in sub_lower
    ):
        return "Shop"
    elif (
        "castle" in sub_lower
        or "asylum" in sub_lower
        or "ruin" in sub_lower
        or "tour" in sub_lower
        or "cafe" in sub_lower
        or "coffee" in sub_lower
        or "house" in sub_lower
        or "explore" in sub_lower
    ):
        return "Explore"
    return SUPER_CATEGORY_MAP.get(sub_cat, "Explore")


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1 = max(-90.0, min(90.0, lat1))
    lat2 = max(-90.0, min(90.0, lat2))
    lon1 = max(-180.0, min(180.0, lon1))
    lon2 = max(-180.0, min(180.0, lon2))

    r = 3958.8  # Earth radius in miles
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(r * c, 2)


STATE_NAME_MAP: dict[str, str] = {
    "al": "alabama",
    "ak": "alaska",
    "az": "arizona",
    "ar": "arkansas",
    "ca": "california",
    "co": "colorado",
    "ct": "connecticut",
    "de": "delaware",
    "fl": "florida",
    "ga": "georgia",
    "hi": "hawaii",
    "id": "idaho",
    "il": "illinois",
    "in": "indiana",
    "ia": "iowa",
    "ks": "kansas",
    "ky": "kentucky",
    "la": "louisiana",
    "me": "maine",
    "md": "maryland",
    "ma": "massachusetts",
    "mi": "michigan",
    "mn": "minnesota",
    "ms": "mississippi",
    "mo": "missouri",
    "mt": "montana",
    "ne": "nebraska",
    "nv": "nevada",
    "nh": "new hampshire",
    "nj": "new jersey",
    "nm": "new mexico",
    "ny": "new york",
    "nc": "north carolina",
    "nd": "north dakota",  # codespell:ignore
    "oh": "ohio",
    "ok": "oklahoma",
    "or": "oregon",
    "pa": "pennsylvania",
    "ri": "rhode island",
    "sc": "south carolina",
    "sd": "south dakota",
    "tn": "tennessee",
    "tx": "texas",
    "ut": "utah",
    "vt": "vermont",
    "va": "virginia",
    "wa": "washington",
    "wv": "west virginia",
    "wi": "wisconsin",
    "wy": "wyoming",
    "dc": "district of columbia",
}


def matches_target_state(address: str, target_state: str) -> bool:
    if not target_state or not target_state.strip():
        return True

    ts = target_state.strip().lower()
    addr = address.strip().lower()

    full_state_name = STATE_NAME_MAP.get(ts, ts)
    pattern = rf"\b({ts}|{full_state_name})\b"
    return bool(re.search(pattern, addr, re.IGNORECASE))
