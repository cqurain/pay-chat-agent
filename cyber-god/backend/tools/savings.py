def calculate_savings_impact(price: float, savings: float, target: float) -> dict:
    """
    Calculate the impact of a purchase on savings progress.

    Args:
        price: Cost of the item being considered.
        savings: Current savings amount.
        target: Savings goal/target amount.

    Returns:
        new_savings (float): savings - price
        progress (float): (new_savings / target) * 100, rounded to 2 decimal places
        delta (float): -price (always negative or zero)
        comment_hint (str): "deficit" if price > 0 else "neutral"
    """
    new_savings = savings - price
    progress = round((new_savings / target) * 100, 2) if target != 0 else 0.0
    delta = -price
    comment_hint = "deficit" if price > 0 else "neutral"
    return {
        "new_savings": new_savings,
        "progress": progress,
        "delta": delta,
        "comment_hint": comment_hint,
    }
