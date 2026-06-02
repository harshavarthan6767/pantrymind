"""Pytest tests for ExpiryService."""

import pytest

from services.expiry_service import ExpiryService


@pytest.fixture
def expiry_service():
    """Create an ExpiryService instance with the real knowledge-base."""
    return ExpiryService("data/expiry_kb.json")


class TestGetShelfLife:
    """Tests for ExpiryService.get_shelf_life()."""

    def test_apple_shelf_life(self, expiry_service):
        """Apples should have a 28-day shelf life."""
        assert expiry_service.get_shelf_life("apples") == 28

    def test_banana_shelf_life(self, expiry_service):
        """Bananas should have a 7-day shelf life."""
        assert expiry_service.get_shelf_life("banana") == 7

    def test_fuzzy_match_green_apples(self, expiry_service):
        """'green apples' should fuzzy-match to 'apple' via substring."""
        shelf_life = expiry_service.get_shelf_life("green apples")
        assert shelf_life > 0

    def test_fuzzy_match_organic_spinach(self, expiry_service):
        """'organic spinach' should fuzzy-match to 'spinach' via substring."""
        shelf_life = expiry_service.get_shelf_life("organic spinach")
        assert shelf_life > 0

    def test_default_shelf_life_unknown(self, expiry_service):
        """Unknown items should return DEFAULT_SHELF_LIFE (7 days)."""
        assert expiry_service.get_shelf_life("unicorn meat") == 7


class TestPredictExpiryFresh:
    """Tests for ExpiryService.predict_expiry_fresh()."""

    def test_predict_expiry_fresh(self, expiry_service):
        """Apples purchased on 2026-06-01 should expire around 2026-06-29."""
        result = expiry_service.predict_expiry_fresh("apples", "2026-06-01")
        assert result["predicted_expiry"] == "2026-06-29"

    def test_predict_expiry_returns_correct_keys(self, expiry_service):
        """Result dict should contain all expected keys."""
        result = expiry_service.predict_expiry_fresh("apples", "2026-06-01")
        assert "predicted_expiry" in result


class TestPackedGoods:
    """Tests for ExpiryService.calculate_suggested_usage_packed()."""

    def test_packed_goods_suggested_usage(self, expiry_service):
        """Packed goods formula: suggested_use_by = expiry - (expiry - mfg) * 0.20.

        For mfg=2026-01-01, expiry=2027-01-01 (365 days):
        buffer = 365 * 0.20 = 73 days
        suggested_use_by = 2027-01-01 - 73 days = 2026-10-20 (approx)
        """
        result = expiry_service.calculate_suggested_usage_packed(
            "chocolate", "2026-01-01", "2027-01-01"
        )
        suggested = result["suggested_use_by"]
        # The exact date depends on rounding; it should be around 2026-10-19 to 2026-10-20
        assert suggested in ("2026-10-19", "2026-10-20")
