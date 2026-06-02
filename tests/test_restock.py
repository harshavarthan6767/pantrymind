"""Pytest tests for restock prediction logic."""

import pytest
from datetime import datetime, timedelta


def predict_restock(item_name, current_qty, consumption_history):
    """Predict when an item will run out based on consumption history.

    consumption_history: list of {"date": datetime, "quantity": float}
    Returns: {"daily_rate": float, "days_remaining": int|None, "predicted_empty": str|None}
    """
    if not consumption_history:
        return {"daily_rate": 0, "days_remaining": None, "predicted_empty": None}

    dates = sorted(consumption_history, key=lambda x: x["date"])
    total_consumed = sum(c["quantity"] for c in dates)
    span_days = max(1, (dates[-1]["date"] - dates[0]["date"]).days)
    daily_rate = total_consumed / span_days

    if daily_rate <= 0:
        return {"daily_rate": 0, "days_remaining": None, "predicted_empty": None}

    days_remaining = int(current_qty / daily_rate)
    predicted_empty = (datetime.now() + timedelta(days=days_remaining)).strftime(
        "%Y-%m-%d"
    )

    return {
        "daily_rate": round(daily_rate, 2),
        "days_remaining": days_remaining,
        "predicted_empty": predicted_empty,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_history():
    """10-day consumption history: 50g/day over 10 days."""
    base = datetime(2026, 5, 22)
    return [
        {"date": base + timedelta(days=i), "quantity": 50}
        for i in range(11)  # days 0..10 → span = 10 days, total = 550g
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRestockPrediction:
    """Tests for the restock prediction logic."""

    def test_consumption_rate(self, sample_history):
        """Daily rate should be total_consumed / span_days = 550/10 = 55."""
        result = predict_restock("rice", 1000, sample_history)
        assert result["daily_rate"] == 55.0

    def test_depletion_prediction(self, sample_history):
        """days_remaining should be int(current_qty / daily_rate) = int(1000/55) = 18."""
        result = predict_restock("rice", 1000, sample_history)
        assert result["days_remaining"] == 18

    def test_zero_consumption(self):
        """Empty consumption history → daily_rate 0, days_remaining None."""
        result = predict_restock("sugar", 500, [])
        assert result["daily_rate"] == 0
        assert result["days_remaining"] is None
        assert result["predicted_empty"] is None

    def test_single_day_history(self):
        """Single entry → span_days clamped to 1, daily_rate = quantity."""
        history = [{"date": datetime(2026, 6, 1), "quantity": 100}]
        result = predict_restock("milk", 500, history)
        # span = max(1, 0) = 1, daily_rate = 100/1 = 100
        assert result["daily_rate"] == 100.0
        assert result["days_remaining"] == 5  # 500 / 100
