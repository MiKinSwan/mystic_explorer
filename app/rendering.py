"""Shared markdown dossier renderer.

Used by both the live-chat agent surface (app/agent.py, tool-grounded name/
address/rating only) and the production DB-backed `/api/search` endpoint
(fast_api_app.py, real mined history/reviews/hidden-gem scoring). Rich
fields are rendered only when actually present on the venue dict - never
filled in with a placeholder - so the live-chat surface (which has none of
them) degrades gracefully instead of showing invented content.
"""

from __future__ import annotations

from typing import Any

from app.config import CATEGORY_ACTIVITY_NOTES
from app.geo_utils import get_super_category

SUPER_BADGES = {
    "Stay": "**STAY** (Hotel / Inn)",
    "Shop": "**SHOP** (Crystals / Herbs / Oddities)",
    "Explore": "**EXPLORE** (Castle / Asylum / Ruins / Tour)",
}


def render_dossier_markdown(
    *,
    location_name: str,
    target_state: str,
    use_gps: bool,
    category_filter: str,
    venues: list[dict[str, Any]],
) -> str:
    mode_label = (
        "Real-Time GPS Override"
        if use_gps
        else f"State: {target_state.upper() if target_state else 'All'}"
    )

    lines = [
        f"# ❖ Dossier of the Strange: {location_name}",
        f"**Search Mode:** `{mode_label}` | **Category:** `{category_filter}` | **Super Categories:** `STAY | SHOP | EXPLORE`",
    ]

    if not venues:
        lines.extend(
            [
                "",
                f"> **No records found matching '{category_filter}' in {target_state.upper() if target_state else 'this location'}.**",
                "> *Try selecting 'All Categories' or clicking 'Use Current Location'!*",
            ]
        )
        return "\n".join(lines)

    intro_text = (
        f"*Discovered **{len(venues)}** places, ranked strictly from **NEAREST STREET DISTANCE FIRST** (from your current GPS location).*"
        if use_gps
        else f"*Discovered **{len(venues)}** places in **{target_state.upper() if target_state else 'the requested state'}**.*"
    )
    lines.extend([intro_text, "", "---", ""])

    for idx, v in enumerate(venues, 1):
        name = v.get("name", "Unknown Venue")
        category = v.get("category", "Oddity")
        super_cat = v.get("super_category") or get_super_category(category)
        # Both empty-string and missing count as "no address" - common for
        # OSM-only ruins/markers that are real GPS points but never had a
        # street address to begin with (nothing to fix; just don't show a
        # blank line for it).
        address = v.get("address") or "No street address on file (see map link below)"
        dist = v.get("distance_miles")
        lat, lon = v.get("latitude"), v.get("longitude")
        maps_url = v.get("google_maps_url") or (
            f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            if lat is not None and lon is not None
            else "#"
        )

        super_badge = SUPER_BADGES.get(super_cat, SUPER_BADGES["Explore"])

        dist_badge = (
            f" — **{dist:.1f} miles away**"
            if (use_gps and dist is not None)
            else ""
        )

        lines.append(f"### {idx}. {name}{dist_badge}")
        lines.append(f"- **Action:** {super_badge}")

        is_gem = v.get("is_hidden_gem")
        if is_gem is True:
            lines.append("- **Tag:** ✦ **Hidden Gem**")
        elif is_gem is False:
            lines.append("- **Tag:** ☆ **Popular Landmark**")

        lines.append(f"- **Category:** {category}")
        lines.append(f"- **Address:** {address}")

        rating = v.get("google_rating")
        if rating is not None:
            review_count = v.get("review_count")
            count_txt = f" ({review_count} Google reviews)" if review_count else ""
            lines.append(f"- **Rating:** {rating}/5{count_txt}")

        # Real OSM description when we have one, else a short generic note
        # for the category - free either way, never LLM-generated.
        activity_note = v.get("description") or CATEGORY_ACTIVITY_NOTES.get(category, "")
        if activity_note:
            lines.append(f"- **What you can do here:** {activity_note}")

        history = v.get("history_and_lore")
        if history:
            lines.append("")
            lines.append(f"**[ ❦ History & Lore ]**\n{history}\n")

        reviews = v.get("review_highlights") or []
        real_quotes = [r.get("quote") for r in reviews if r.get("quote")]
        if real_quotes:
            lines.append("**Accounts on Record:**")
            for quote in real_quotes[:3]:
                lines.append(f'- *"{quote}"*')
            lines.append("")

        specialties = v.get("specialties") or []
        if specialties:
            lines.append(f"**Specialties:** {', '.join(specialties)}\n")

        lines.append(f"**[ Get Directions on Google Maps ]({maps_url})**")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
