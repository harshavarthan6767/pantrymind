"""
Indian Tax Computation Tools for PantryMind.

Implements full New Regime FY 2026-27 tax slabs with standard deduction,
Section 87A rebate, and 4 % Health & Education Cess.
"""

import logging

from google.adk.tools import ToolContext

logger = logging.getLogger("pantrymind.tools.tax")

# ── New Regime FY 2026-27 Tax Slabs ───────────────────────────────────────
# Each tuple: (upper_limit, rate).  upper_limit is None for the last slab.
_NEW_REGIME_SLABS: list[tuple[float | None, float]] = [
    (400_000, 0.00),    # Nil up to ₹4,00,000
    (800_000, 0.05),    # 5 % for ₹4L – ₹8L
    (1_200_000, 0.10),  # 10 % for ₹8L – ₹12L
    (1_600_000, 0.15),  # 15 % for ₹12L – ₹16L
    (2_000_000, 0.20),  # 20 % for ₹16L – ₹20L
    (2_400_000, 0.25),  # 25 % for ₹20L – ₹24L
    (None, 0.30),       # 30 % above ₹24L
]

_STANDARD_DEDUCTION = 75_000       # ₹75,000 standard deduction
_REBATE_87A_THRESHOLD = 1_200_000  # Taxable income ≤ ₹12L → full rebate
_CESS_RATE = 0.04                  # 4 % Health & Education Cess


def _compute_slab_tax(taxable_income: float) -> float:
    """Calculate tax strictly from slab rates (before rebate/cess)."""
    tax = 0.0
    prev_limit = 0.0

    for upper, rate in _NEW_REGIME_SLABS:
        if upper is None:
            # Last slab — tax on everything above prev_limit
            if taxable_income > prev_limit:
                tax += (taxable_income - prev_limit) * rate
            break
        slab_amount = min(taxable_income, upper) - prev_limit
        if slab_amount > 0:
            tax += slab_amount * rate
        if taxable_income <= upper:
            break
        prev_limit = upper

    return round(tax, 2)


async def compute_indian_tax(
    gross_annual_salary: float,
    regime: str = "new",
    tool_context: ToolContext = None,
) -> dict:
    """Compute Indian income tax under the New Regime FY 2026-27.

    Call this tool when the user asks about their income tax, take-home
    salary, tax liability, or net income in India. Works for salaried
    individuals under the **New Tax Regime** with the budget 2025 slabs.

    Args:
        gross_annual_salary: Gross annual salary/CTC in INR.
        regime: Tax regime — currently only 'new' is fully implemented.
            Pass 'old' to get a placeholder message.
        tool_context: ADK tool context.

    Returns:
        dict with keys: gross_annual_salary, standard_deduction,
        taxable_income, tax_before_rebate, rebate_87a, tax_after_rebate,
        cess, total_tax, net_income, effective_rate_pct, regime.
    """
    try:
        if regime.lower() not in ("new", "old"):
            return {"error": f"Unknown regime '{regime}'. Use 'new' or 'old'."}

        if regime.lower() == "old":
            return {
                "message": (
                    "Old Regime computation is not yet implemented. "
                    "Please use regime='new' for FY 2026-27 New Regime."
                ),
                "regime": "old",
            }

        gross = float(gross_annual_salary)
        deduction = _STANDARD_DEDUCTION
        taxable = max(0.0, gross - deduction)

        tax_before_rebate = _compute_slab_tax(taxable)

        # Section 87A rebate: if taxable income ≤ ₹12L, tax = 0
        rebate = tax_before_rebate if taxable <= _REBATE_87A_THRESHOLD else 0.0
        tax_after_rebate = max(0.0, tax_before_rebate - rebate)

        cess = round(tax_after_rebate * _CESS_RATE, 2)
        total_tax = round(tax_after_rebate + cess, 2)
        net_income = round(gross - total_tax, 2)

        effective_rate = round((total_tax / gross) * 100, 2) if gross > 0 else 0.0

        result = {
            "gross_annual_salary": gross,
            "standard_deduction": deduction,
            "taxable_income": taxable,
            "tax_before_rebate": tax_before_rebate,
            "rebate_87a": rebate,
            "tax_after_rebate": tax_after_rebate,
            "cess": cess,
            "total_tax": total_tax,
            "net_income": net_income,
            "effective_rate_pct": effective_rate,
            "regime": "new",
        }

        logger.info(
            "Tax computed: gross=%.0f, taxable=%.0f, total_tax=%.0f, net=%.0f",
            gross, taxable, total_tax, net_income,
        )
        return result

    except Exception as e:
        logger.error("Tax computation failed: %s", e, exc_info=True)
        return {"error": str(e), "status": "failed"}


async def compute_disposable_income(
    monthly_salary: float,
    monthly_spending: float,
    tool_context: ToolContext = None,
) -> dict:
    """Calculate monthly disposable income after tax and spending.

    Call this tool when the user wants to know their savings potential,
    discretionary income, or how much they can put away each month.

    Args:
        monthly_salary: Gross monthly salary in INR.
        monthly_spending: Total monthly expenses in INR.
        tool_context: ADK tool context.

    Returns:
        dict with keys: monthly_salary, annual_salary, monthly_tax,
        monthly_net, monthly_spending, disposable_income, savings_rate_pct.
    """
    try:
        annual = monthly_salary * 12
        tax_result = await compute_indian_tax(annual, "new", tool_context)

        if "error" in tax_result:
            return tax_result

        total_tax = tax_result["total_tax"]
        monthly_tax = round(total_tax / 12, 2)
        monthly_net = round(monthly_salary - monthly_tax, 2)
        disposable = round(monthly_net - monthly_spending, 2)
        savings_rate = round((disposable / monthly_net) * 100, 2) if monthly_net > 0 else 0.0

        result = {
            "monthly_salary": monthly_salary,
            "annual_salary": annual,
            "monthly_tax": monthly_tax,
            "monthly_net": monthly_net,
            "monthly_spending": monthly_spending,
            "disposable_income": disposable,
            "savings_rate_pct": savings_rate,
        }

        logger.info(
            "Disposable income: net=%.0f, spending=%.0f, disposable=%.0f",
            monthly_net, monthly_spending, disposable,
        )
        return result

    except Exception as e:
        logger.error("Disposable income calculation failed: %s", e, exc_info=True)
        return {"error": str(e), "status": "failed"}
