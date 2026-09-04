"""Seed candidate list, migrated from the old app/database.py.

Only name/address/category/state survive the migration - the original
PRESEEDED_DATABASE also had fabricated `history_and_lore` and
`review_highlights` for these (real) businesses, which is exactly the
problem this refactor fixes. These names are fed into the mining pipeline
as extra scout candidates so `enrich_candidate` (real Places Place Details)
and `research_history` (real, grounded web search) can re-source them for
real, or leave the field empty if nothing real is found.
"""

from __future__ import annotations

SEED_CANDIDATES: list[dict] = [
    {
        "name": "Earth & Sky Crystal Sanctuary (Chalfont)",
        "category": "Crystal & Metaphysical Shops",
        "address": "4275 County Line Rd, Chalfont, PA 18914",
        "state": "PA",
        "latitude": 40.2882,
        "longitude": -75.2091,
    },
    {
        # User-reported favorite, missing from OSM coverage - added directly
        # 2026-09-02.
        "name": "Crystal Visions",
        "category": "Crystal & Metaphysical Shops",
        "address": "4275 County Line Rd Ste 16, Chalfont, PA 18914",
        "state": "PA",
        "latitude": 40.2882,
        "longitude": -75.2091,
    },
    {
        "name": "The Logan Inn (1727)",
        "category": "Haunted Hotels & Motels",
        "address": "10 W Ferry St, New Hope, PA 18938",
        "state": "PA",
        "latitude": 40.3633,
        "longitude": -74.9508,
    },
    {
        "name": "The Creeper Gallery & Oddities",
        "category": "Oddities & Creepy Galleries",
        "address": "129 S Main St, New Hope, PA 18938",
        "state": "PA",
        "latitude": 40.3625,
        "longitude": -74.9502,
    },
    {
        "name": "Fonthill Castle & Mercer Museum",
        "category": "Castles & Historic Houses",
        "address": "525 E Court St, Doylestown, PA 18901",
        "state": "PA",
        "latitude": 40.3101,
        "longitude": -75.1299,
    },
    {
        "name": "Pennhurst Asylum & Sanatorium Ruins",
        "category": "Asylums, Sanatoriums & Ruins",
        "address": "Church St, Spring City, PA 19475",
        "state": "PA",
        "latitude": 40.1788,
        "longitude": -75.5721,
    },
    {
        "name": "Eastern State Penitentiary Ruins",
        "category": "Asylums, Sanatoriums & Ruins",
        "address": "2027 Fairmount Ave, Philadelphia, PA 19130",
        "state": "PA",
        "latitude": 39.9683,
        "longitude": -75.1727,
    },
    {
        "name": "Mütter Museum of Medical History",
        "category": "Oddities & Creepy Galleries",
        "address": "19 S 22nd St, Philadelphia, PA 19103",
        "state": "PA",
        "latitude": 39.9533,
        "longitude": -75.1764,
    },
    {
        "name": "Jennie Wade House & Gettysburg Battlefield",
        "category": "Ghost Tours & Haunted Sites",
        "address": "548 Baltimore St, Gettysburg, PA 17325",
        "state": "PA",
        "latitude": 39.8242,
        "longitude": -77.2312,
    },
    {
        "name": "The Inn at Jim Thorpe (1849)",
        "category": "Haunted Hotels & Motels",
        "address": "24 Broadway, Jim Thorpe, PA 18229",
        "state": "PA",
        "latitude": 40.8631,
        "longitude": -75.7381,
    },
    {
        "name": "The Joshua Ward House",
        "category": "Haunted Hotels & Motels",
        "address": "148 Washington St, Salem, MA 01970",
        "state": "MA",
        "latitude": 42.5201,
        "longitude": -70.8931,
    },
    {
        "name": "Lizzie Borden Bed & Breakfast Museum",
        "category": "Haunted Hotels & Motels",
        "address": "230 2nd St, Fall River, MA 02721",
        "state": "MA",
        "latitude": 41.6986,
        "longitude": -71.1564,
    },
]
