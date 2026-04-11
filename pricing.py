"""
pricing.py
──────────
Dynamic pricing logic.

Formula
-------
raw_price  = base_price + (demand * DEMAND_MULTIPLIER)
final_price = clip(raw_price, 0.80 * base, 1.50 * base)

Reason labels
-------------
"High demand"   → raw_price hit the 150 % ceiling
"Low activity"  → raw_price fell to the 80 % floor (or demand == 0)
"Stable"        → price sits between floor and ceiling
"""

# How much each unit of demand adds to the base price (in INR)
DEMAND_MULTIPLIER: float = 5.0

# Price band as fractions of base price
FLOOR_RATIO: float = 0.80   # 80 %  — minimum the price can drop to
CEIL_RATIO:  float = 1.50   # 150 % — maximum the price can rise to


def compute_price(base_price: float, demand: float) -> dict:
    """
    Compute the final dynamic price for a product.

    Parameters
    ----------
    base_price : The catalogue base price in INR.
    demand     : The current demand score (output of demand.compute_demand).

    Returns
    -------
    dict with keys:
        price  (int)  — rounded final price in INR
        reason (str)  — human-readable label
    """
    floor = base_price * FLOOR_RATIO
    ceil  = base_price * CEIL_RATIO

    raw_price = base_price + (demand * DEMAND_MULTIPLIER)

    if raw_price >= ceil:
        final_price = ceil
        reason = "High demand"
    elif raw_price <= floor or demand == 0:
        final_price = floor
        reason = "Low activity"
    else:
        final_price = raw_price
        reason = "Stable"

    return {
        "price" : int(round(final_price)),
        "reason": reason,
    }
