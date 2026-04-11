"""
Real-Time Dynamic Pricing and Recommendation Engine
====================================================
Run with:  uvicorn main:app --reload
Docs at:   http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime, timedelta

from data_loader import load_products, load_clickstream
from demand import compute_demand
from pricing import compute_price
from recommender import get_recommendations

# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SmartPrice Engine",
    description="Real-Time Dynamic Pricing & Recommendation Backend",
    version="1.0.0",
)

# Serve the demo frontend from /demo so it can call API routes via same origin.
app.mount("/demo", StaticFiles(directory="frontend", html=True), name="demo")

# ── In-memory state (loaded once at startup) ──────────────────────────────────

products_df   = load_products("techshop_products_20_INR.csv")
clickstream   = load_clickstream("clickstream_clean_timestamp.csv")   # list[dict]

# ── Request / Response models ─────────────────────────────────────────────────

class EventRequest(BaseModel):
    product_id: int
    action: str           # "view" | "cart" | "purchase"
    user_id: int = 0      # optional; defaults to anonymous

# ── Helper ────────────────────────────────────────────────────────────────────

WINDOW_MINUTES = 10

def _recent_events():
    """Return only events in the last WINDOW_MINUTES."""
    cutoff = datetime.now() - timedelta(minutes=WINDOW_MINUTES)
    return [e for e in clickstream if e["timestamp"] >= cutoff]


def _product_or_404(product_id: int):
    row = products_df[products_df["product_id"] == product_id]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return row.iloc[0]


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/products", summary="List all products with live price & demand")
def list_products():
    """
    Returns every product with:
    - current demand score (sliding 10-min window)
    - dynamically adjusted price
    - demand label
    """
    recent = _recent_events()
    result = []

    for _, row in products_df.iterrows():
        pid        = int(row["product_id"])
        demand     = compute_demand(pid, recent)
        price_info = compute_price(row["price_inr"], demand)

        result.append({
            "product_id"  : pid,
            "name"        : row["name"],
            "category"    : row["category"],
            "base_price"  : int(row["price_inr"]),
            "current_price": price_info["price"],
            "demand"      : round(demand, 2),
            "reason"      : price_info["reason"],
        })

    # Sort by demand descending so the hottest items come first
    result.sort(key=lambda x: x["demand"], reverse=True)
    return {"count": len(result), "products": result}


@app.post("/event", summary="Record a user interaction event")
def post_event(event: EventRequest):
    """
    Accepts a new user event and appends it to the in-memory clickstream.
    The demand & price for that product update immediately.
    """
    valid_actions = {"view", "cart", "purchase"}
    if event.action not in valid_actions:
        raise HTTPException(
            status_code=422,
            detail=f"action must be one of {valid_actions}"
        )

    product = _product_or_404(event.product_id)

    new_event = {
        "user_id"   : event.user_id,
        "product_id": event.product_id,
        "action"    : event.action,
        "timestamp" : datetime.now(),
    }
    clickstream.append(new_event)

    # Compute updated state immediately
    recent     = _recent_events()
    demand     = compute_demand(event.product_id, recent)
    price_info = compute_price(product["price_inr"], demand)

    return {
        "status"         : "recorded",
        "product_id"     : event.product_id,
        "action"         : event.action,
        "timestamp"      : new_event["timestamp"].isoformat(),
        "updated_demand" : round(demand, 2),
        "updated_price"  : price_info["price"],
        "reason"         : price_info["reason"],
    }


@app.get("/price/{product_id}", summary="Get live price for a product")
def get_price(product_id: int):
    """
    Returns:
    - updated price (clipped to 80–150 % of base)
    - demand score
    - human-readable reason
    """
    product    = _product_or_404(product_id)
    recent     = _recent_events()
    demand     = compute_demand(product_id, recent)
    price_info = compute_price(product["price_inr"], demand)

    return {
        "product_id"  : product_id,
        "name"        : product["name"],
        "base_price"  : int(product["price_inr"]),
        "current_price": price_info["price"],
        "demand"      : round(demand, 2),
        "reason"      : price_info["reason"],
        "window_minutes": WINDOW_MINUTES,
    }


@app.get("/recommendations/{product_id}", summary="Get recommendations for a product")
def recommend(product_id: int, top_n: int = 5):
    """
    Returns top-N products from the same category, ranked by live demand.
    Excludes the queried product itself.
    """
    product = _product_or_404(product_id)
    recent  = _recent_events()
    recs    = get_recommendations(
        product_id=product_id,
        category=product["category"],
        products_df=products_df,
        recent_events=recent,
        top_n=min(top_n, 5),   # cap at 5
    )
    return {
        "product_id"     : product_id,
        "category"       : product["category"],
        "recommendations": recs,
    }


@app.get("/health", summary="Health check")
def health_check():
    """Quick status endpoint to verify backend connectivity."""
    return {
        "status": "ok",
        "service": "SmartPrice Engine",
        "products_loaded": int(len(products_df)),
        "events_loaded": int(len(clickstream)),
        "time": datetime.now().isoformat(),
    }


@app.get("/", include_in_schema=False)
def root():
    return {"message": "SmartPrice Engine is running. Visit /docs for the API."}
