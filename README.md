# SmartPrice Engine — Real-Time Dynamic Pricing & Recommendation Backend

## Project structure

```
smartprice/
├── main.py           ← FastAPI app & all routes
├── data_loader.py    ← CSV loading & parsing
├── demand.py         ← Sliding-window demand scoring
├── pricing.py        ← Dynamic pricing logic
├── recommender.py    ← Category-based recommendation engine
├── requirements.txt
├── techshop_products_20_INR.csv      ← place your products CSV here
└── clickstream_clean_timestamp.csv   ← place your clickstream CSV here
```

## Setup

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Place CSVs in the same folder as main.py

# 4. Start the server
uvicorn main:app --reload
```

Then open **http://127.0.0.1:8000/demo** in your browser.

API docs auto-generated at → **http://127.0.0.1:8000/docs**
Frontend demo at → **http://127.0.0.1:8000/demo**

### Backend access quick links

- Health check: **http://127.0.0.1:8000/health**
- API docs (Swagger UI): **http://127.0.0.1:8000/docs**
- ReDoc docs: **http://127.0.0.1:8000/redoc**
- Root status message: **http://127.0.0.1:8000/**

### How to verify backend is connected

1. Open **http://127.0.0.1:8000/health**.
2. If connected, you should get JSON like:

```json
{
  "status": "ok",
  "service": "SmartPrice Engine",
  "products_loaded": 20,
  "events_loaded": 8,
  "time": "2026-04-11T10:30:00.000000"
}
```

3. In the demo UI (**/demo**), top-right status should show **API connected**.

---

## Endpoints

### GET /products
List all products with live demand and dynamic price.

```bash
curl http://127.0.0.1:8000/products
```

### POST /event
Record a user interaction (view / cart / purchase).

```bash
curl -X POST http://127.0.0.1:8000/event \
     -H "Content-Type: application/json" \
     -d '{"product_id": 107, "action": "view", "user_id": 1}'
```

### GET /price/{product_id}
Get the current dynamic price for a product.

```bash
curl http://127.0.0.1:8000/price/107
```

Sample response:
```json
{
  "product_id": 107,
  "name": "Laptop Aquamarine 815",
  "base_price": 5286,
  "current_price": 5357,
  "demand": 14.5,
  "reason": "Stable",
  "window_minutes": 10
}
```

### GET /recommendations/{product_id}
Get top-5 same-category recommendations ranked by live demand.

```bash
curl http://127.0.0.1:8000/recommendations/107
```

Optional query param: `?top_n=3`

---

## Pricing logic

| Condition                      | Rule                        | Label          |
|--------------------------------|-----------------------------|----------------|
| demand == 0 or raw ≤ 80% base  | price = 80% of base         | Low activity   |
| 80% < raw < 150%               | price = base + demand × 5   | Stable         |
| raw ≥ 150% base                | price capped at 150% base   | High demand    |

## Demand formula (10-minute sliding window)

```
demand = views × 0.5  +  carts × 1.0  +  purchases × 2.0
```

---

## Real-time behaviour

Every `POST /event` call:
1. Appends the event to the in-memory clickstream with `datetime.now()`.
2. Re-computes demand instantly using the 10-minute window.
3. Returns the updated price in the same response.

All subsequent `GET /price` and `GET /recommendations` calls reflect
the new event immediately — no restart needed.

---

## Demo frontend features

- Live product list from `GET /products`
- Product detail panel powered by `GET /price/{product_id}`
- Event buttons (`view`, `cart`, `purchase`) posting to `POST /event`
- Same-category recommendations from `GET /recommendations/{product_id}`
- Optional auto-refresh every 8 seconds

---

## Update products and prices later

- Starter products are in `techshop_products_20_INR.csv`.
- Update `price_inr` values whenever you want.
- Keep required columns unchanged: `product_id, category, name, price_inr`.
- Restart the server after editing the CSV so new prices are loaded.
