from datetime import datetime, timedelta

def parse_date_range(natural_date: str) -> dict:
    """
    Converts natural language date expressions to ISO date strings for MongoDB queries.
    
    The Finance Agent calls this before building any aggregate() pipeline.
    
    Input:  "this month" | "last month" | "last 30 days" | "last 7 days" | "YYYY-MM"
    Output: {"start": "2026-06-01T00:00:00Z", "end": "2026-06-06T23:59:59Z"}
    """
    now = datetime.utcnow()
    
    if natural_date in ("this month", "current month"):
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end   = now
    elif natural_date == "last month":
        first_this = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end   = first_this - timedelta(seconds=1)
        start = end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif natural_date == "last 30 days":
        start = now - timedelta(days=30)
        end   = now
    elif natural_date == "last 7 days":
        start = now - timedelta(days=7)
        end   = now
    else:
        # Try parsing YYYY-MM format
        try:
            year, month = map(int, natural_date.split("-"))
            start = datetime(year, month, 1)
            if month == 12:
                end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end = datetime(year, month + 1, 1) - timedelta(seconds=1)
        except Exception:
            start = now.replace(day=1, hour=0, minute=0, second=0)
            end   = now
    
    return {
        "start": start.isoformat() + "Z",
        "end":   end.isoformat()   + "Z"
    }


def compute_budget_summary(monthly_salary: float, spent_this_month: float) -> dict:
    """
    Computes disposable income and spend rate.
    Finance Agent calls this after querying the ledger total.
    """
    disposable  = monthly_salary - spent_this_month
    rate_pct    = round((spent_this_month / monthly_salary * 100) if monthly_salary else 0, 1)
    days_in_month = 30  # Approximation
    days_elapsed  = datetime.utcnow().day
    daily_rate    = round(spent_this_month / days_elapsed, 2) if days_elapsed > 0 else 0
    projected     = round(daily_rate * days_in_month, 2)
    
    return {
        "monthly_salary":    round(monthly_salary, 2),
        "spent_this_month":  round(spent_this_month, 2),
        "disposable_income": round(disposable, 2),
        "spend_rate_pct":    rate_pct,
        "daily_burn_rate":   daily_rate,
        "projected_monthly": projected,
        "on_track":          projected <= monthly_salary
    }

def compare_period_totals(this_period: float, last_period: float) -> dict:
    return {"delta": this_period - last_period}
