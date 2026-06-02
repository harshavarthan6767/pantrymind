"""Pytest tests for Indian tax computation under the New Tax Regime FY 2025-26."""

import pytest


def compute_new_regime_tax(annual_salary: float) -> dict:
    """Compute Indian income tax under the New Tax Regime FY 2025-26.

    Standard deduction: ₹75,000
    Slabs on taxable income:
      0 - 4L:     0%
      4L - 8L:    5%
      8L - 12L:  10%
      12L - 16L: 15%
      16L - 20L: 20%
      20L - 24L: 25%
      24L+:      30%

    Section 87A rebate: If taxable income <= 12L, tax is 0.
    Cess: 4% on tax.
    """
    std_deduction = 75_000
    taxable = max(0, annual_salary - std_deduction)

    slabs = [
        (400000, 0.00),
        (400000, 0.05),
        (400000, 0.10),
        (400000, 0.15),
        (400000, 0.20),
        (400000, 0.25),
        (float("inf"), 0.30),
    ]

    tax = 0
    remaining = taxable
    for width, rate in slabs:
        if remaining <= 0:
            break
        chunk = min(remaining, width)
        tax += chunk * rate
        remaining -= chunk

    # Section 87A rebate
    if taxable <= 1_200_000:
        tax = 0

    cess = tax * 0.04
    total_tax = tax + cess

    return {
        "annual_salary": annual_salary,
        "standard_deduction": std_deduction,
        "taxable_income": taxable,
        "tax_before_cess": tax,
        "cess": cess,
        "total_tax": total_tax,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNewRegimeTax:
    """Tests for the New Tax Regime FY 2025-26 computation."""

    def test_nil_tax_below_threshold(self):
        """Salary ₹4,00,000 → taxable ₹3,25,000 → under 4L slab → 0 tax."""
        result = compute_new_regime_tax(400_000)
        assert result["taxable_income"] == 325_000
        assert result["tax_before_cess"] == 0
        assert result["total_tax"] == 0

    def test_section_87a_rebate(self):
        """Salary ₹12,75,000 → taxable ₹12,00,000 → 87A applies → 0 tax."""
        result = compute_new_regime_tax(1_275_000)
        assert result["taxable_income"] == 1_200_000
        assert result["tax_before_cess"] == 0
        assert result["total_tax"] == 0

    def test_salary_8_lakh(self):
        """Salary ₹8,00,000 → taxable ₹7,25,000 → under 12L → rebate → 0."""
        result = compute_new_regime_tax(800_000)
        assert result["taxable_income"] == 725_000
        # Under 12L threshold, so Section 87A wipes the tax
        assert result["tax_before_cess"] == 0
        assert result["total_tax"] == 0

    def test_salary_12_lakh(self):
        """Salary ₹12,00,000 → taxable ₹11,25,000 → under 12L → rebate → 0."""
        result = compute_new_regime_tax(1_200_000)
        assert result["taxable_income"] == 1_125_000
        assert result["tax_before_cess"] == 0
        assert result["total_tax"] == 0

    def test_salary_16_lakh(self):
        """Salary ₹16,00,000 → taxable ₹15,25,000.

        Slabs: 4L×0% + 4L×5% + 4L×10% + 3.25L×15%
             = 0 + 20,000 + 40,000 + 48,750 = 1,08,750
        Cess: 4,350  |  Total: 1,13,100
        """
        result = compute_new_regime_tax(1_600_000)
        assert result["taxable_income"] == 1_525_000
        assert result["tax_before_cess"] == 108_750
        assert result["cess"] == pytest.approx(4_350)
        assert result["total_tax"] == pytest.approx(113_100)

    def test_salary_20_lakh(self):
        """Salary ₹20,00,000 → taxable ₹19,25,000.

        Slabs: 4L×0% + 4L×5% + 4L×10% + 4L×15% + 3.25L×20%
             = 0 + 20,000 + 40,000 + 60,000 + 65,000 = 1,85,000
        Cess: 7,400  |  Total: 1,92,400
        """
        result = compute_new_regime_tax(2_000_000)
        assert result["taxable_income"] == 1_925_000
        assert result["tax_before_cess"] == 185_000
        assert result["cess"] == pytest.approx(7_400)
        assert result["total_tax"] == pytest.approx(192_400)

    def test_salary_25_lakh(self):
        """Salary ₹25,00,000 → taxable ₹24,25,000.

        Slabs: 4L×0% + 4L×5% + 4L×10% + 4L×15% + 4L×20% + 4L×25% + 0.25L×30%
             = 0 + 20,000 + 40,000 + 60,000 + 80,000 + 100,000 + 7,500
             = 3,07,500
        Cess: 12,300  |  Total: 3,19,800
        """
        result = compute_new_regime_tax(2_500_000)
        assert result["taxable_income"] == 2_425_000
        assert result["tax_before_cess"] == 307_500
        assert result["cess"] == pytest.approx(12_300)
        assert result["total_tax"] == pytest.approx(319_800)

    def test_cess_calculation(self):
        """Verify cess is exactly 4% of pre-cess tax."""
        result = compute_new_regime_tax(2_000_000)
        assert result["cess"] == pytest.approx(result["tax_before_cess"] * 0.04)

    def test_standard_deduction(self):
        """Standard deduction is always ₹75,000 regardless of salary."""
        for salary in [300_000, 800_000, 1_500_000, 5_000_000]:
            result = compute_new_regime_tax(salary)
            assert result["standard_deduction"] == 75_000
