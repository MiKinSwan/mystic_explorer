# ruff: noqa: E402, W293
import logging

import truststore
from dotenv import load_dotenv

truststore.inject_into_ssl()
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.config import SUPER_CATEGORIES, US_STATES
from app.db.queries import query_pois
from app.db.session import get_session
from app.rendering import render_dossier_markdown

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("oddities_explorer.api")

fastapi_app = FastAPI(
    title="Mystic Shadow API",
    description="3-Super Category Explorer (Stay, Shop, Explore) with 15-Initial + Load More Pagination.",
    version="4.0.0",
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    state: str | None = Field(default="", description="State abbreviation")
    city: str | None = Field(default="", description="City name")
    street: str | None = Field(default="", description="Street name")
    category_filter: str | None = Field(
        default="All Categories",
        description="Super category filter (Stay, Shop, Explore)",
    )
    use_gps: bool | None = Field(
        default=False, description="True if using real browser GPS"
    )
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)


@fastapi_app.get("/healthz")
async def health_check():
    return {
        "status": "healthy",
        "service": "oddities-explorer",
        "version": "5.0.0",
        "super_categories": SUPER_CATEGORIES,
        "data_source": "mined Postgres dataset (see app/pipeline/mine.py)",
    }


@fastapi_app.post("/api/search")
async def search_oddities(req: SearchRequest):
    logger.info(
        f"Search request: State={req.state}, GPS={req.use_gps} ({req.latitude}, {req.longitude}), Filter={req.category_filter}"
    )

    input_payload = {
        "state": req.state or "",
        "city": req.city or "",
        "street": req.street or "",
        "category_filter": req.category_filter or "All Categories",
        "use_gps": req.use_gps or False,
        "user_latitude": req.latitude,
        "user_longitude": req.longitude,
    }

    if req.use_gps and (req.latitude is None or req.longitude is None):
        raise HTTPException(status_code=400, detail="latitude/longitude are required when use_gps is true")
    if not req.use_gps and not (req.state or "").strip():
        raise HTTPException(status_code=400, detail="state is required when not using GPS")

    try:
        db_session = get_session()
        try:
            venues = query_pois(
                db_session,
                state=req.state or "",
                category_filter=req.category_filter or "All Categories",
                use_gps=req.use_gps or False,
                latitude=req.latitude,
                longitude=req.longitude,
            )
        finally:
            db_session.close()

        location_name = (
            f"Current GPS Location ({req.latitude:.4f}, {req.longitude:.4f})"
            if req.use_gps and req.latitude is not None and req.longitude is not None
            else (req.state or "Target Area").upper()
        )

        dossier_markdown = render_dossier_markdown(
            location_name=location_name,
            target_state=req.state or "",
            use_gps=req.use_gps or False,
            category_filter=req.category_filter or "All Categories",
            venues=venues,
        )

        return {
            "status": "success",
            "location_input": input_payload,
            "dossier_markdown": dossier_markdown,
            "venues": venues,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error querying mined dataset: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {e!s}") from e


@fastapi_app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """High-Density Dashboard with 3 Super Categories (Stay, Shop, Explore)."""
    state_options = ['<option value="">-- Select State (Mandatory) --</option>'] + [
        f'<option value="{code}" {"selected" if code == "PA" else ""}>{code} - {name}</option>'
        for code, name in US_STATES
    ]
    state_options_html = "\n".join(state_options)

    super_category_options_html = """
    <option value="All Categories" selected>&#9670; All Categories</option>
    <option value="Stay">&#9670; Stay &mdash; Haunted Inns, Hotels &amp; B&amp;Bs</option>
    <option value="Shop">&#9670; Shop &mdash; Curiosities, Crystals &amp; Witchcraft</option>
    <option value="Explore">&#9670; Explore &mdash; Castles, Asylums &amp; Ruins</option>
    """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mystic Shadow</title>
        <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%95%B8%EF%B8%8F%3C/text%3E%3C/svg%3E">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700;900&family=Cinzel:wght@400;600;700&family=EB+Garamond:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-void: #08070a;
                --bg-panel: #14101a;
                --bg-panel-2: #1b1420;
                --gold: #9c7a24;
                --gold-bright: #d8b354;
                --blood: #5c0e14;
                --blood-bright: #8a1c22;
                --ember: #ff8a3d;
                --parchment: #e4d8bb;
                --parchment-dim: #a89a7c;
            }}

            body {{
                background: radial-gradient(ellipse 1200px 800px at 50% -10%, #241016 0%, #0d0a0d 45%, var(--bg-void) 100%) var(--bg-void) fixed;
                color: var(--parchment);
                font-family: 'EB Garamond', Georgia, serif;
            }}

            .header-banner {{
                position: relative;
                overflow: hidden;
                background: radial-gradient(ellipse at top, #2a0d12 0%, #100a0d 65%, #08070a 100%);
                border-bottom: 2px solid var(--gold);
                padding: 55px 20px 65px;
                text-align: center;
                box-shadow: 0 6px 30px rgba(0,0,0,0.6);
            }}
            .cobweb {{ position: absolute; top: -12px; width: 210px; height: 210px; opacity: 0.28; pointer-events: none; z-index: 0; }}
            .cobweb-left {{ left: -14px; }}
            .cobweb-right {{ right: -14px; transform: scaleX(-1); }}
            .spider {{
                position: absolute; top: 58px; left: 78px; font-size: 1.15rem; opacity: 0.6;
                transform-origin: top center; animation: spiderSway 4.5s ease-in-out infinite; z-index: 0;
            }}
            @keyframes spiderSway {{ 0%, 100% {{ transform: rotate(-7deg); }} 50% {{ transform: rotate(7deg); }} }}

            .header-content {{ position: relative; z-index: 1; }}

            .torch {{
                display: inline-block; font-size: 1.9rem; color: var(--ember);
                text-shadow: 0 0 8px #ff6a00, 0 0 18px #ff3d00, 0 0 34px rgba(255,90,0,0.55);
                animation: torchFlicker 2.4s ease-in-out infinite; vertical-align: middle; margin: 0 20px;
            }}
            .torch-right {{ animation-delay: 0.9s; }}
            @keyframes torchFlicker {{
                0%, 100% {{ opacity: 0.85; transform: scale(1); }}
                20% {{ opacity: 1; transform: scale(1.08) rotate(-2deg); }}
                45% {{ opacity: 0.7; transform: scale(0.92); }}
                70% {{ opacity: 1; transform: scale(1.05) rotate(2deg); }}
            }}

            .gothic-title {{
                font-family: 'Cinzel Decorative', 'Cinzel', serif; font-weight: 700; letter-spacing: 3px;
                text-transform: uppercase; color: var(--parchment);
                text-shadow: 0 0 18px rgba(255,120,40,0.25), 0 2px 0 #000;
                font-size: 2.3rem; margin: 0; display: inline-flex; align-items: center;
            }}
            .gothic-title .fa-crow {{ color: var(--gold-bright); margin: 0 10px; }}
            .gothic-subtitle {{ font-family: 'Cinzel', serif; color: var(--parchment-dim); letter-spacing: 1px; margin-top: 16px; font-size: 1.08rem; }}
            .gothic-subtitle strong {{ color: var(--gold-bright); font-weight: 600; }}
            .divider {{ color: var(--gold); font-size: 1.1rem; margin: 14px auto 0; letter-spacing: 10px; opacity: 0.7; }}

            .search-box {{
                max-width: 950px; margin: -35px auto 30px auto; position: relative;
                background: var(--bg-panel); padding: 30px 28px; border-radius: 60px 60px 10px 10px;
                border: 1px solid var(--gold); box-shadow: 0 15px 40px rgba(0,0,0,0.6), inset 0 0 40px rgba(0,0,0,0.4);
            }}
            .form-label {{ font-family: 'Cinzel', serif; letter-spacing: 1px; color: var(--gold-bright) !important; }}
            .form-control, .form-select {{ background: var(--bg-void); border: 1px solid #40331a; color: var(--parchment); font-family: 'EB Garamond', serif; }}
            .form-control:focus, .form-select:focus {{ background: #0f0b10; color: var(--parchment); border-color: var(--ember); box-shadow: 0 0 0 0.2rem rgba(255, 138, 61, 0.25); }}
            .form-select option {{ background: var(--bg-panel); color: var(--parchment); }}

            .btn-spooky {{ background: linear-gradient(160deg, var(--blood-bright) 0%, #2a0508 100%); border: 1px solid var(--gold); color: var(--parchment); font-family: 'Cinzel', serif; letter-spacing: 1px; font-weight: 600; text-shadow: 0 1px 2px #000; }}
            .btn-spooky:hover {{ background: linear-gradient(160deg, #a3232a 0%, #3a070b 100%); color: var(--parchment); box-shadow: 0 0 20px rgba(255,80,20,0.3); }}
            .btn-gps {{ background: linear-gradient(160deg, #4a3a10 0%, #201808 100%); border: 1px solid var(--gold); color: var(--parchment); font-family: 'Cinzel', serif; font-weight: 600; }}
            .btn-gps:hover {{ color: var(--parchment); box-shadow: 0 0 16px rgba(200,150,40,0.3); }}
            .btn-gps.active-gps {{ background: linear-gradient(160deg, #1f4d2b 0%, #0e2214 100%); border-color: #4a9a5f; }}
            .btn-loadmore {{ background: linear-gradient(160deg, var(--blood-bright) 0%, #2a0508 100%); color: var(--parchment); border: 1px solid var(--gold); font-family: 'Cinzel', serif; font-weight: 600; padding: 15px 40px; border-radius: 30px; font-size: 1.05rem; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }}
            .btn-loadmore:hover {{ box-shadow: 0 0 24px rgba(255,90,20,0.35); color: var(--parchment); }}

            .dossier-card {{ background: var(--bg-panel-2); border-radius: 10px; border: 1px solid #4a3a1e; padding: 34px; margin-bottom: 20px; line-height: 1.75; box-shadow: 0 10px 30px rgba(0,0,0,0.5); font-family: 'EB Garamond', serif; font-size: 1.08rem; }}
            .dossier-card h1 {{ font-family: 'Cinzel Decorative', serif; color: var(--gold-bright); border-bottom: 2px solid var(--blood-bright); padding-bottom: 12px; font-weight: 700; letter-spacing: 1px; }}
            .dossier-card h3 {{ font-family: 'Cinzel', serif; color: var(--ember); margin-top: 25px; font-weight: 600; }}
            .dossier-card a {{ color: #d9a441; text-decoration: none; font-weight: 600; border-bottom: 1px dotted #d9a441; }}
            .dossier-card a:hover {{ color: var(--ember); }}

            .alert-warning {{ background: #241708; border: 1px solid var(--gold); color: var(--parchment) !important; }}
            .alert-danger {{ background: #2a0a0c; border: 1px solid var(--blood-bright); color: var(--parchment) !important; }}
            .spinner-border.text-primary {{ color: var(--gold-bright) !important; }}
        </style>
    </head>
    <body>
        <div class="header-banner">
            <svg class="cobweb cobweb-left" viewBox="0 0 200 200" aria-hidden="true">
                <g stroke="#d8b354" stroke-width="1" fill="none">
                    <line x1="0" y1="0" x2="200" y2="0"/>
                    <line x1="0" y1="0" x2="200" y2="50"/>
                    <line x1="0" y1="0" x2="200" y2="100"/>
                    <line x1="0" y1="0" x2="200" y2="150"/>
                    <line x1="0" y1="0" x2="200" y2="200"/>
                    <line x1="0" y1="0" x2="150" y2="200"/>
                    <line x1="0" y1="0" x2="100" y2="200"/>
                    <line x1="0" y1="0" x2="50" y2="200"/>
                    <line x1="0" y1="0" x2="0" y2="200"/>
                    <path d="M 26 0 Q 26 26 0 26"/>
                    <path d="M 58 0 Q 58 58 0 58"/>
                    <path d="M 95 0 Q 95 95 0 95"/>
                    <path d="M 135 0 Q 135 135 0 135"/>
                    <path d="M 175 0 Q 175 175 0 175"/>
                </g>
            </svg>
            <svg class="cobweb cobweb-right" viewBox="0 0 200 200" aria-hidden="true">
                <g stroke="#d8b354" stroke-width="1" fill="none">
                    <line x1="0" y1="0" x2="200" y2="0"/>
                    <line x1="0" y1="0" x2="200" y2="50"/>
                    <line x1="0" y1="0" x2="200" y2="100"/>
                    <line x1="0" y1="0" x2="200" y2="150"/>
                    <line x1="0" y1="0" x2="200" y2="200"/>
                    <line x1="0" y1="0" x2="150" y2="200"/>
                    <line x1="0" y1="0" x2="100" y2="200"/>
                    <line x1="0" y1="0" x2="50" y2="200"/>
                    <line x1="0" y1="0" x2="0" y2="200"/>
                    <path d="M 26 0 Q 26 26 0 26"/>
                    <path d="M 58 0 Q 58 58 0 58"/>
                    <path d="M 95 0 Q 95 95 0 95"/>
                    <path d="M 135 0 Q 135 135 0 135"/>
                    <path d="M 175 0 Q 175 175 0 175"/>
                </g>
            </svg>
            <div class="spider">&#128375;&#65039;</div>
            <div class="header-content">
                <h1 class="gothic-title">
                    <span class="torch torch-left"><i class="fa-solid fa-fire"></i></span>
                    <i class="fa-solid fa-crow"></i> Mystic Shadow
                    <span class="torch torch-right"><i class="fa-solid fa-fire"></i></span>
                </h1>
                <div class="divider">&#10070; &#10070; &#10070;</div>
                <p class="gothic-subtitle">A dossier of the strange, sorted into <strong>Stay</strong>, <strong>Shop</strong>, and <strong>Explore</strong>.</p>
            </div>
        </div>

        <div class="container">
            <div class="search-box">
                <form id="searchForm">
                    <div class="row g-3 align-items-end">
                        <div class="col-md-4">
                            <label class="form-label small">SELECT STATE (MANDATORY)</label>
                            <select id="stateInput" class="form-select form-select-lg">
                                {state_options_html}
                            </select>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label small">WHAT DO YOU WANT TO DO?</label>
                            <select id="categoryInput" class="form-select form-select-lg">
                                {super_category_options_html}
                            </select>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label small">NEAR ME (OPTIONAL OVERRIDE)</label>
                            <button type="button" id="gpsBtn" class="btn btn-gps btn-lg w-100">
                                <i class="fa-solid fa-location-crosshairs me-2"></i> Use Current Location
                            </button>
                        </div>
                    </div>
                    <div class="mt-4 text-center">
                        <button type="submit" class="btn btn-spooky btn-lg px-5"><i class="fa-solid fa-feather-pointed me-2"></i> Consult the Dossier</button>
                    </div>
                </form>
            </div>

            <div id="loading" class="text-center my-5 d-none">
                <div class="spinner-border text-primary" style="width: 3rem; height: 3rem;" role="status"></div>
                <p class="mt-3 fs-5" style="color: var(--parchment-dim); font-family: 'Cinzel', serif;">Consulting the archives for Stay, Shop &amp; Explore...</p>
            </div>

            <div id="resultsArea" class="my-4"></div>

            <div id="loadMoreContainer" class="text-center my-5 d-none">
                <button type="button" id="loadMoreBtn" class="btn btn-loadmore">
                    <i class="fa-solid fa-scroll me-2"></i> Unfurl 20 More Entries
                </button>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <script>
            let useGpsLocation = false;
            let gpsLat = null;
            let gpsLon = null;
            let fullMarkdownText = '';
            let parsedSections = [];
            let currentlyShown = 15;

            const stateInput = document.getElementById('stateInput');
            const categoryInput = document.getElementById('categoryInput');
            const gpsBtn = document.getElementById('gpsBtn');
            const searchForm = document.getElementById('searchForm');
            const resultsArea = document.getElementById('resultsArea');
            const loading = document.getElementById('loading');
            const loadMoreContainer = document.getElementById('loadMoreContainer');
            const loadMoreBtn = document.getElementById('loadMoreBtn');

            // GPS BUTTON CLICK HANDLER
            gpsBtn.addEventListener('click', () => {{
                if (!navigator.geolocation) {{
                    alert('Geolocation is not supported by your browser.');
                    return;
                }}

                gpsBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i> Locating GPS...';

                navigator.geolocation.getCurrentPosition(
                    (pos) => {{
                        useGpsLocation = true;
                        gpsLat = pos.coords.latitude;
                        gpsLon = pos.coords.longitude;
                        gpsBtn.classList.add('active-gps');
                        gpsBtn.innerHTML = '<i class="fa-solid fa-circle-check me-2"></i> GPS Active (' + gpsLat.toFixed(2) + ', ' + gpsLon.toFixed(2) + ')';
                        searchForm.dispatchEvent(new Event('submit'));
                    }},
                    (err) => {{
                        useGpsLocation = false;
                        gpsBtn.classList.remove('active-gps');
                        gpsBtn.innerHTML = '<i class="fa-solid fa-location-crosshairs me-2"></i> Use Current Location';
                        alert('Could not retrieve GPS location: ' + err.message);
                    }}
                );
            }});

            // AUTO-SEARCH ON STATE CHANGE
            stateInput.addEventListener('change', () => {{
                useGpsLocation = false;
                gpsBtn.classList.remove('active-gps');
                gpsBtn.innerHTML = '<i class="fa-solid fa-location-crosshairs me-2"></i> Use Current Location';
                searchForm.dispatchEvent(new Event('submit'));
            }});

            // AUTO-SEARCH ON CATEGORY CHANGE
            categoryInput.addEventListener('change', () => {{
                searchForm.dispatchEvent(new Event('submit'));
            }});

            // RENDER CARDS WITH 15-INITIAL + LOAD MORE PAGINATION
            function renderPaginatedCards() {{
                if (parsedSections.length === 0) {{
                    resultsArea.innerHTML = '<div class="alert alert-warning">No places found for this selection. Try selecting "All Categories"!</div>';
                    loadMoreContainer.classList.add('d-none');
                    return;
                }}

                const header = parsedSections[0] || '';
                const items = parsedSections.slice(1);
                
                const visibleItems = items.slice(0, currentlyShown);
                const combinedMarkdown = header + '\\n\\n' + visibleItems.join('\\n\\n---\\n\\n');

                resultsArea.innerHTML = `
                    <div class="dossier-card">
                        ${{marked.parse(combinedMarkdown)}}
                    </div>
                `;

                if (currentlyShown < items.length) {{
                    const remaining = items.length - currentlyShown;
                    const nextBatch = Math.min(20, remaining);
                    loadMoreBtn.innerHTML = `<i class="fa-solid fa-scroll me-2"></i> Unfurl ${{nextBatch}} More Entries (${{remaining}} remain)`;
                    loadMoreContainer.classList.remove('d-none');
                }} else {{
                    loadMoreContainer.classList.add('d-none');
                }}
            }}

            // LOAD MORE BUTTON CLICK HANDLER
            loadMoreBtn.addEventListener('click', () => {{
                currentlyShown += 20;
                renderPaginatedCards();
            }});

            // FORM SUBMIT HANDLER
            searchForm.addEventListener('submit', async (e) => {{
                e.preventDefault();
                
                const state = stateInput.value;
                const category_filter = categoryInput.value;

                if (!useGpsLocation && !state) {{
                    resultsArea.innerHTML = '<div class="alert alert-warning text-center fs-5"><i class="fa-solid fa-triangle-exclamation me-2"></i> <strong>State is required!</strong> Please select a State from the dropdown or click "Use Current Location".</div>';
                    loadMoreContainer.classList.add('d-none');
                    return;
                }}
                
                loading.classList.remove('d-none');
                resultsArea.innerHTML = '';
                loadMoreContainer.classList.add('d-none');
                
                try {{
                    const payload = {{
                        state: state,
                        category_filter: category_filter,
                        use_gps: useGpsLocation,
                        latitude: gpsLat,
                        longitude: gpsLon
                    }};

                    const res = await fetch('/api/search', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(payload)
                    }});
                    const data = await res.json();
                    loading.classList.add('d-none');
                    
                    if (data.dossier_markdown) {{
                        fullMarkdownText = data.dossier_markdown;
                        // Split markdown by venue headers (### )
                        const rawChunks = fullMarkdownText.split(/(?=### \\d+\\.)/g);
                        parsedSections = rawChunks.map(c => c.trim()).filter(c => c.length > 0);
                        
                        currentlyShown = 15; // FAST 1-SECOND INITIAL LOAD: TOP 15 PLACES!
                        renderPaginatedCards();
                    }} else {{
                        resultsArea.innerHTML = '<div class="alert alert-warning">Sorry, we could not find any places matching your selected category. Try selecting "All Categories"!</div>';
                        loadMoreContainer.classList.add('d-none');
                    }}
                }} catch (err) {{
                    loading.classList.add('d-none');
                    resultsArea.innerHTML = `<div class="alert alert-danger">Error: ${{err.message}}</div>`;
                    loadMoreContainer.classList.add('d-none');
                }}
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("fast_api_app:fastapi_app", host="127.0.0.1", port=8080, reload=False)
