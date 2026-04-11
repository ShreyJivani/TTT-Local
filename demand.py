"""
demand.py
─────────
Sliding-window demand scoring.

Formula
-------
demand = views * 0.5 + carts * 1 + purchases * 2

All counts are taken from a pre-filtered list of events that already
fall inside the desired time window (filtering is done in main.py so
this module stays pure and easily testable).
"""


# Action weights — tweak these to change demand sensitivity
ACTION_WEIGHTS: dict[str, float] = {
    "view"    : 0.5,
    "cart"    : 1.0,
    "purchase": 2.0,
}


def compute_demand(product_id: int, recent_events: list[dict]) -> float:
    """
    Compute the demand score for a single product over the supplied events.

    Parameters
    ----------
    product_id    : The product to score.
    recent_events : A list of event dicts already filtered to the time window.
                    Each dict has keys: product_id, action, timestamp, user_id.

    Returns
    -------
    demand : float ≥ 0
    """
    demand = 0.0
    for event in recent_events:
        if event["product_id"] == product_id:
            demand += ACTION_WEIGHTS.get(event["action"], 0.0)
    return demand


def compute_all_demands(
    product_ids: list[int],
    recent_events: list[dict],
) -> dict[int, float]:
    """
    Compute demand scores for multiple products in a single pass.
    More efficient than calling compute_demand() in a loop when you need
    scores for many products at once (e.g. the /products endpoint).

    Returns
    -------
    A dict mapping product_id → demand score.
    """
    scores: dict[int, float] = {pid: 0.0 for pid in product_ids}

    for event in recent_events:
        pid = event["product_id"]
        if pid in scores:
            scores[pid] += ACTION_WEIGHTS.get(event["action"], 0.0)

    return scores
