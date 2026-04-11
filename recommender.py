"""
recommender.py
──────────────
Category-based recommendation engine.

Strategy
--------
1. Find all products in the same category as the queried product.
2. Score each candidate by its live demand over the current time window.
3. Exclude the queried product itself.
4. Return the top-N candidates sorted by demand (descending).

If fewer than top_n candidates exist in the category, all are returned.
"""

import pandas as pd
from demand import compute_all_demands
from pricing import compute_price


def get_recommendations(
    product_id: int,
    category: str,
    products_df: pd.DataFrame,
    recent_events: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """
    Parameters
    ----------
    product_id    : The product the user is currently viewing.
    category      : Its category (used to filter candidates).
    products_df   : Full products DataFrame.
    recent_events : Pre-filtered events for the current time window.
    top_n         : Maximum recommendations to return (1–5).

    Returns
    -------
    A list of recommendation dicts, each with:
        product_id, name, category, base_price, current_price, demand, reason
    """
    # Filter to same category, excluding the queried product
    candidates = products_df[
        (products_df["category"] == category) &
        (products_df["product_id"] != product_id)
    ]

    if candidates.empty:
        return []

    candidate_ids = candidates["product_id"].tolist()

    # Compute demand for all candidates in one pass
    demand_map = compute_all_demands(candidate_ids, recent_events)

    # Build recommendation list
    recs = []
    for _, row in candidates.iterrows():
        pid    = int(row["product_id"])
        demand = demand_map.get(pid, 0.0)
        price_info = compute_price(row["price_inr"], demand)

        recs.append({
            "product_id"   : pid,
            "name"         : row["name"],
            "category"     : row["category"],
            "base_price"   : int(row["price_inr"]),
            "current_price": price_info["price"],
            "demand"       : round(demand, 2),
            "reason"       : price_info["reason"],
        })

    # Sort by demand descending; tie-break on product_id for determinism
    recs.sort(key=lambda x: (-x["demand"], x["product_id"]))

    return recs[:top_n]
