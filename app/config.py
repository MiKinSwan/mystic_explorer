"""Central configuration file for Mystic Shadow."""

MODEL = "gemini-3.1-flash-lite"

# 3 Super-Categories (Simplified User Interface)
SUPER_CATEGORIES = [
    "All Categories",
    "Stay",
    "Shop",
    "Explore",
]

# Mapping of Granular Categories to 3 Super-Categories
SUPER_CATEGORY_MAP = {
    # 🛌 STAY
    "Haunted Hotels & Motels": "Stay",
    "Stay": "Stay",
    # 🛍️ SHOP
    "Witchcraft & Occult Shops": "Shop",
    "Herb & Botanical Apothecaries": "Shop",
    "Crystal & Metaphysical Shops": "Shop",
    "Oddities & Creepy Galleries": "Shop",
    "General Specialty Shops": "Shop",
    "Shop": "Shop",
    # 🏰 EXPLORE
    "Castles & Historic Houses": "Explore",
    "Asylums, Sanatoriums & Ruins": "Explore",
    "Ghost Tours & Haunted Sites": "Explore",
    "Spooky Coffee Shops & Cafes": "Explore",
    "Explore": "Explore",
}

# 10 Granular Sub-Categories (Internal Metadata)
CATEGORIES = [
    "Haunted Hotels & Motels",
    "Castles & Historic Houses",
    "Witchcraft & Occult Shops",
    "Herb & Botanical Apothecaries",
    "Crystal & Metaphysical Shops",
    "Oddities & Creepy Galleries",
    "Spooky Coffee Shops & Cafes",
    "General Specialty Shops",
    "Ghost Tours & Haunted Sites",
    "Asylums, Sanatoriums & Ruins",
]

# Short, free (no API call) "what can you do here" note per granular
# category - shown as a fallback when a venue has no real OSM description.
# Deliberately generic/factual about the category itself, not a claim about
# any specific venue - keeps it honest without costing anything to generate.
CATEGORY_ACTIVITY_NOTES: dict[str, str] = {
    "Haunted Hotels & Motels": "Book a stay overnight and see what you notice.",
    "Castles & Historic Houses": "Tour the grounds and historic architecture.",
    "Witchcraft & Occult Shops": "Browse crystals, herbs, tarot decks, and occult supplies; some offer readings.",
    "Herb & Botanical Apothecaries": "Browse herbal remedies, teas, and apothecary goods.",
    "Crystal & Metaphysical Shops": "Shop for crystals, stones, and metaphysical tools.",
    "Oddities & Creepy Galleries": "Browse curated oddities, taxidermy, or macabre art and artifacts.",
    "Spooky Coffee Shops & Cafes": "Grab a coffee or bite in a spooky-themed setting.",
    "General Specialty Shops": "Browse a curated selection of unusual or niche items.",
    "Ghost Tours & Haunted Sites": "Join a guided tour or walk the site independently.",
    "Asylums, Sanatoriums & Ruins": "Explore the grounds - check current accessibility/tour info first.",
}

NICHE_SEARCH_KEYWORDS = [
    "haunted hotel",
    "paranormal inn",
    "historic castle",
    "witchcraft shop",
    "occult bookshop",
    "herbal apothecary",
    "crystal shop",
    "oddity gallery",
    "macabre art",
    "spooky cafe",
    "ghost tour",
    "asylum ruins",
    "sanatorium ruins",
]

# Maps each Google Places search keyword to one of the 10 granular CATEGORIES.
KEYWORD_CATEGORY_MAP: dict[str, str] = {
    "haunted hotel": "Haunted Hotels & Motels",
    "paranormal inn": "Haunted Hotels & Motels",
    "historic castle": "Castles & Historic Houses",
    "witchcraft shop": "Witchcraft & Occult Shops",
    "occult bookshop": "Witchcraft & Occult Shops",
    "herbal apothecary": "Herb & Botanical Apothecaries",
    "crystal shop": "Crystal & Metaphysical Shops",
    "oddity gallery": "Oddities & Creepy Galleries",
    "macabre art": "Oddities & Creepy Galleries",
    "spooky cafe": "Spooky Coffee Shops & Cafes",
    "ghost tour": "Ghost Tours & Haunted Sites",
    "asylum ruins": "Asylums, Sanatoriums & Ruins",
    "sanatorium ruins": "Asylums, Sanatoriums & Ruins",
}

# Maps an OSM (key, value) tag pair to a granular CATEGORY. Also doubles as
# the tag filter list the Overpass query mines (see app/tools/osm.py).
#
# Deliberately narrow: an earlier version included ("tourism", "attraction")
# and ("tourism", "gallery"), which are so broadly applied in OSM that a
# Rhode Island test run pulled in a tennis hall of fame and a public park
# alongside actual oddities. Every tag here should be specific enough that a
# match is genuinely on-theme without needing an LLM to filter it after the
# fact.
OSM_TAG_CATEGORY_MAP: dict[tuple[str, str], str] = {
    ("shop", "esoteric"): "Witchcraft & Occult Shops",
    ("shop", "occult"): "Witchcraft & Occult Shops",
    ("shop", "herbalist"): "Herb & Botanical Apothecaries",
    ("historic", "ruins"): "Asylums, Sanatoriums & Ruins",
    ("historic", "castle"): "Castles & Historic Houses",
    ("amenity", "psychic"): "Witchcraft & Occult Shops",
    ("building", "asylum"): "Asylums, Sanatoriums & Ruins",
    ("tourism", "haunted_house"): "Ghost Tours & Haunted Sites",
}

KNOWN_COORDINATES = {
    "PA": (40.2882, -75.2091),
    "MA": (42.5218, -70.8925),
    "LA": (29.9511, -90.0715),
    "MS": (31.5621, -91.4022),
    "NE": (41.2597, -95.9348),
}

# Approximate state bounding boxes as (south, west, north, east), used to
# scope the OSM Overpass mining query per state. Precision to the mile
# doesn't matter here - this just keeps each state's query geographically
# bounded instead of hitting the whole country.
STATE_BBOXES: dict[str, tuple[float, float, float, float]] = {
    "AL": (30.2, -88.5, 35.0, -84.9),
    "AK": (51.0, -179.0, 71.5, -129.9),
    "AZ": (31.3, -114.9, 37.0, -109.0),
    "AR": (33.0, -94.7, 36.5, -89.6),
    "CA": (32.5, -124.5, 42.0, -114.1),
    "CO": (37.0, -109.1, 41.0, -102.0),
    "CT": (40.95, -73.75, 42.05, -71.78),
    "DE": (38.45, -75.79, 39.84, -75.05),
    "FL": (24.5, -87.6, 31.0, -80.0),
    "GA": (30.4, -85.6, 35.0, -80.8),
    "HI": (18.9, -160.3, 22.3, -154.8),
    "ID": (42.0, -117.3, 49.0, -111.0),
    "IL": (36.97, -91.5, 42.5, -87.0),
    "IN": (37.77, -88.1, 41.76, -84.78),
    "IA": (40.37, -96.64, 43.5, -90.14),
    "KS": (36.99, -102.05, 40.0, -94.6),
    "KY": (36.5, -89.57, 39.15, -81.96),
    "LA": (28.9, -94.05, 33.02, -88.75),
    "ME": (43.06, -71.08, 47.46, -66.95),
    "MD": (37.9, -79.49, 39.72, -75.0),
    "MA": (41.24, -73.5, 42.89, -69.86),
    "MI": (41.7, -90.42, 48.2, -82.41),
    "MN": (43.5, -97.24, 49.38, -89.49),
    "MS": (30.17, -91.66, 35.0, -88.1),
    "MO": (35.99, -95.77, 40.61, -89.1),
    "MT": (44.36, -116.05, 49.0, -104.04),
    "NE": (40.0, -104.05, 43.0, -95.31),
    "NV": (35.0, -120.0, 42.0, -114.04),
    "NH": (42.7, -72.56, 45.31, -70.61),
    "NJ": (38.93, -75.56, 41.36, -73.89),
    "NM": (31.33, -109.05, 37.0, -103.0),
    "NY": (40.5, -79.76, 45.02, -71.85),
    "NC": (33.84, -84.32, 36.59, -75.46),
    "ND": (45.94, -104.05, 49.0, -96.55),  # codespell:ignore
    "OH": (38.4, -84.82, 42.32, -80.52),
    "OK": (33.62, -103.0, 37.0, -94.43),
    "OR": (41.99, -124.57, 46.29, -116.46),
    "PA": (39.72, -80.52, 42.27, -74.69),
    "RI": (41.15, -71.86, 42.02, -71.12),
    "SC": (32.03, -83.35, 35.22, -78.54),
    "SD": (42.48, -104.06, 45.94, -96.44),
    "TN": (34.98, -90.31, 36.68, -81.65),
    "TX": (25.84, -106.65, 36.5, -93.51),
    "UT": (36.99, -114.05, 42.0, -109.04),
    "VT": (42.73, -73.44, 45.02, -71.5),
    "VA": (36.54, -83.68, 39.47, -75.24),
    "WA": (45.54, -124.85, 49.0, -116.92),
    "WV": (37.2, -82.65, 40.64, -77.72),
    "WI": (42.49, -92.89, 47.31, -86.25),
    "WY": (40.99, -111.06, 45.0, -104.05),
    "DC": (38.79, -77.12, 38.995, -76.91),
}

US_STATES = [
    ("AL", "Alabama"),
    ("AK", "Alaska"),
    ("AZ", "Arizona"),
    ("AR", "Arkansas"),
    ("CA", "California"),
    ("CO", "Colorado"),
    ("CT", "Connecticut"),
    ("DE", "Delaware"),
    ("FL", "Florida"),
    ("GA", "Georgia"),
    ("HI", "Hawaii"),
    ("ID", "Idaho"),
    ("IL", "Illinois"),
    ("IN", "Indiana"),
    ("IA", "Iowa"),
    ("KS", "Kansas"),
    ("KY", "Kentucky"),
    ("LA", "Louisiana"),
    ("ME", "Maine"),
    ("MD", "Maryland"),
    ("MA", "Massachusetts"),
    ("MI", "Michigan"),
    ("MN", "Minnesota"),
    ("MS", "Mississippi"),
    ("MO", "Missouri"),
    ("MT", "Montana"),
    ("NE", "Nebraska"),
    ("NV", "Nevada"),
    ("NH", "New Hampshire"),
    ("NJ", "New Jersey"),
    ("NM", "New Mexico"),
    ("NY", "New York"),
    ("NC", "North Carolina"),
    ("ND", "North Dakota"),  # codespell:ignore
    ("OH", "Ohio"),
    ("OK", "Oklahoma"),
    ("OR", "Oregon"),
    ("PA", "Pennsylvania"),
    ("RI", "Rhode Island"),
    ("SC", "South Carolina"),
    ("SD", "South Dakota"),
    ("TN", "Tennessee"),
    ("TX", "Texas"),
    ("UT", "Utah"),
    ("VT", "Vermont"),
    ("VA", "Virginia"),
    ("WA", "Washington"),
    ("WV", "West Virginia"),
    ("WI", "Wisconsin"),
    ("WY", "Wyoming"),
    ("DC", "District of Columbia"),
]

PROMPT_INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"system prompt",
    r"override rules",
    r"developer mode",
    r"delete database",
]
