"""Read-side queries against the mined POI dataset - what `/api/search`
calls instead of running the live LLM pipeline per request."""

from __future__ import annotations

from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID
from sqlalchemy.orm import Session

from app.db.models import POI
from app.geo_utils import haversine_miles

MILES_TO_METERS = 1609.34
GPS_RADIUS_MILES = 50.0
DEFAULT_LIMIT = 200


def query_pois(
    session: Session,
    *,
    state: str = "",
    category_filter: str = "All Categories",
    use_gps: bool = False,
    latitude: float | None = None,
    longitude: float | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[dict]:
    q = session.query(POI)

    if use_gps and latitude is not None and longitude is not None:
        point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        q = q.filter(ST_DWithin(POI.location, point, GPS_RADIUS_MILES * MILES_TO_METERS))
    elif state:
        q = q.filter(POI.state == state.upper())

    cf = (category_filter or "All Categories").strip().lower()
    if cf and cf != "all categories":
        q = q.filter(POI.super_category.ilike(cf))

    if not (use_gps and latitude is not None and longitude is not None):
        # Hidden gems first for browse-by-state mode - GPS mode sorts by
        # distance instead (below), which matters more when you're standing
        # right next to something.
        q = q.order_by(POI.hidden_gem_score.desc())

    rows = q.limit(limit).all()

    results: list[dict] = []
    for row in rows:
        d = {
            "name": row.name,
            "category": row.category,
            "super_category": row.super_category,
            "address": row.address,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "google_rating": row.google_rating,
            "review_count": row.review_count,
            "review_highlights": row.review_highlights,
            "history_and_lore": row.history_and_lore,
            "specialties": row.specialties,
            "is_hidden_gem": row.is_hidden_gem,
            "google_maps_url": row.google_maps_url,
            "is_publicly_accessible": row.is_publicly_accessible,
            "distance_miles": None,
        }
        if use_gps and latitude is not None and longitude is not None:
            d["distance_miles"] = haversine_miles(latitude, longitude, row.latitude, row.longitude)
        results.append(d)

    if use_gps and latitude is not None and longitude is not None:
        results.sort(
            key=lambda x: x["distance_miles"] if x["distance_miles"] is not None else 9999.0
        )

    return results
