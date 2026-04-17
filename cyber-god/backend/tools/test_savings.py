"""TDD tests for calculate_savings_impact (tools/savings.py)."""
import pytest
from tools.savings import calculate_savings_impact


def test_basic_deficit():
    """Test 1: standard deficit case — purchase reduces savings below target."""
    result = calculate_savings_impact(800, 5000, 10000)
    assert result["new_savings"] == 4200
    assert result["progress"] == 42.0
    assert result["delta"] == -800
    assert result["comment_hint"] == "deficit"


def test_zero_price_neutral():
    """Test 2: zero-cost purchase — savings unchanged, progress stays."""
    result = calculate_savings_impact(0, 5000, 10000)
    assert result["new_savings"] == 5000
    assert result["progress"] == 50.0
    assert result["delta"] == 0
    assert result["comment_hint"] == "neutral"


def test_purchase_exceeds_savings():
    """Test 3: purchase price exceeds current savings — new_savings is negative."""
    result = calculate_savings_impact(200, 150, 1000)
    assert result["new_savings"] == -50
    assert result["progress"] == -5.0
    assert result["delta"] == -200
    assert result["comment_hint"] == "deficit"


def test_progress_rounding():
    """Test 4: progress is float rounded to 2 decimal places."""
    result = calculate_savings_impact(100, 333, 1000)
    assert result["progress"] == 23.3


def test_zero_price_surplus_hint():
    """Test 5: zero-cost with positive savings -> comment_hint is 'neutral' (not 'deficit')."""
    result = calculate_savings_impact(0, 5000, 10000)
    # zero-cost is treated as neutral (price == 0 means no deficit)
    assert result["comment_hint"] == "neutral"
    assert result["delta"] == 0
