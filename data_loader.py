"""
data_loader.py
──────────────
Handles all CSV I/O and initial data preparation.
Only the product_id column is used to identify products
(price columns in clickstream are intentionally ignored per spec).
"""

import pandas as pd
from datetime import datetime


def load_products(path: str) -> pd.DataFrame:
    """
    Load the products CSV.

    Expected columns:
        product_id, category, name, price_inr, cost_inr, margin_inr

    Returns a clean DataFrame indexed by position (not product_id) so
    iterrows() works normally throughout the app.
    """
    df = pd.read_csv(path)

    # Normalise column names (strip whitespace, lowercase)
    df.columns = df.columns.str.strip().str.lower()

    required = {"product_id", "category", "name", "price_inr"}
    missing  = required - set(df.columns)
    if missing:
        raise ValueError(f"products CSV is missing columns: {missing}")

    df["product_id"] = df["product_id"].astype(int)
    df["price_inr"]  = df["price_inr"].astype(float)
    df["name"]       = df["name"].astype(str).str.strip()
    df["category"]   = df["category"].astype(str).str.strip()

    return df.reset_index(drop=True)


def load_clickstream(path: str) -> list[dict]:
    """
    Load the clickstream CSV and return a list of event dicts.

    Each dict contains:
        user_id    : int
        product_id : int
        action     : str  ("view" | "cart" | "purchase")
        timestamp  : datetime

    The price_inr column from clickstream is NOT carried forward —
    pricing is always derived from the products catalogue + demand.
    """
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()

    # Parse timestamp; coerce bad rows to NaT then drop them
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])

    df["product_id"] = df["product_id"].astype(int)
    df["user_id"]    = df["user_id"].astype(int)
    df["action"]     = df["action"].astype(str).str.strip().str.lower()

    # Keep only recognised actions
    valid = {"view", "cart", "purchase"}
    df    = df[df["action"].isin(valid)]

    # Convert to a plain list of dicts for fast in-memory mutation
    events = []
    for _, row in df.iterrows():
        events.append({
            "user_id"   : int(row["user_id"]),
            "product_id": int(row["product_id"]),
            "action"    : row["action"],
            "timestamp" : row["timestamp"].to_pydatetime(),
        })

    return events
