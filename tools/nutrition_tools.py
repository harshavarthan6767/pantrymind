"""
Nutritional Intelligence Tools for PantryMind.

Wraps NutritionService for macro lookups, intake logging, weekly reports,
deficiency checking, and Gemini-powered nutrition report generation.
"""

import logging
from datetime import datetime, timedelta

from google.adk.tools import ToolContext

from services.nutrition_service import NutritionService
from services.db_service import MongoDBService

logger = logging.getLogger("pantrymind.tools.nutrition")

nutrition_service = NutritionService()
db = MongoDBService()


async def lookup_nutrition(
    item_name: str,
    tool_context: ToolContext,
) -> dict:
    """Look up per-100g nutritional data for a food item.

    Call this tool when the user asks about the calories, protein, carbs,
    fat, or fiber content of a food item. Uses the USDA FoodData Central
    knowledge base.

    Args:
        item_name: Name of the food item (e.g. 'chicken breast', 'rice').
        tool_context: ADK tool context.

    Returns:
        dict with keys: item, calories_per_100g, protein_g, carbs_g,
        fat_g, fiber_g.
    """
    try:
        result = nutrition_service.get_nutrition(item_name)
        logger.info(
            "Nutrition lookup: %s → %d kcal/100g, %.1fg protein",
            item_name, result.get("calories_per_100g", 0), result.get("protein_g", 0),
        )
        return result
    except Exception as e:
        logger.error("Nutrition lookup failed for '%s': %s", item_name, e, exc_info=True)
        return {"error": str(e), "item": item_name}


async def log_nutrition_intake(
    item_name: str,
    quantity_grams: float,
    date: str = "",
    tool_context: ToolContext = None,
) -> dict:
    """Log a food intake event with calculated macronutrients.

    Call this tool when the user says they ate something, e.g. "I ate
    200g of chicken" or "had 2 apples (about 300g)". Calculates macros
    and stores in the nutrition_log collection.

    Args:
        item_name: Name of the food item consumed.
        quantity_grams: Amount consumed in grams.
        date: Optional date (ISO YYYY-MM-DD). Defaults to today.
        tool_context: ADK tool context.

    Returns:
        dict with keys: log_id, item, quantity_grams, calories, protein_g,
        carbs_g, fat_g, fiber_g, date.
    """
    try:
        intake = nutrition_service.calculate_intake(item_name, quantity_grams)

        log_date = date if date else datetime.now().strftime("%Y-%m-%d")

        log_doc = {
            **intake,
            "date": log_date,
            "created_at": datetime.now().isoformat(),
        }
        log_id = await db.insert_one("nutrition_log", log_doc)

        result = {
            "log_id": log_id,
            **intake,
            "date": log_date,
        }

        logger.info(
            "Nutrition logged: %s, %.0fg → %.0f kcal (id=%s)",
            item_name, quantity_grams, intake.get("calories", 0), log_id,
        )
        return result

    except Exception as e:
        logger.error("Nutrition logging failed: %s", e, exc_info=True)
        return {"error": str(e), "item": item_name}


async def get_weekly_nutrition(
    tool_context: ToolContext = None,
) -> dict:
    """Aggregate nutrition intake for the last 7 days.

    Call this tool when the user asks about their weekly nutrition
    summary, macro totals, or dietary compliance.

    Args:
        tool_context: ADK tool context.

    Returns:
        dict with keys: start_date, end_date, total (macro totals),
        daily_avg (average per day), days_logged (number of distinct days).
    """
    try:
        now = datetime.now()
        start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")

        pipeline = [
            {"$match": {"date": {"$gte": start, "$lte": end}}},
            {"$group": {
                "_id": None,
                "total_calories": {"$sum": "$calories"},
                "total_protein": {"$sum": "$protein_g"},
                "total_carbs": {"$sum": "$carbs_g"},
                "total_fat": {"$sum": "$fat_g"},
                "total_fiber": {"$sum": "$fiber_g"},
                "log_count": {"$sum": 1},
                "distinct_days": {"$addToSet": "$date"},
            }},
        ]
        results = await db.aggregate("nutrition_log", pipeline)

        if not results:
            return {
                "start_date": start,
                "end_date": end,
                "total": {},
                "daily_avg": {},
                "days_logged": 0,
                "message": "No nutrition data logged in the last 7 days.",
            }

        data = results[0]
        days_count = len(data.get("distinct_days", []))
        days_divisor = max(1, days_count)

        total = {
            "calories": round(data.get("total_calories", 0), 1),
            "protein_g": round(data.get("total_protein", 0), 1),
            "carbs_g": round(data.get("total_carbs", 0), 1),
            "fat_g": round(data.get("total_fat", 0), 1),
            "fiber_g": round(data.get("total_fiber", 0), 1),
        }

        daily_avg = {
            "calories": round(total["calories"] / days_divisor, 1),
            "protein_g": round(total["protein_g"] / days_divisor, 1),
            "carbs_g": round(total["carbs_g"] / days_divisor, 1),
            "fat_g": round(total["fat_g"] / days_divisor, 1),
            "fiber_g": round(total["fiber_g"] / days_divisor, 1),
        }

        result = {
            "start_date": start,
            "end_date": end,
            "total": total,
            "daily_avg": daily_avg,
            "days_logged": days_count,
            "log_count": data.get("log_count", 0),
        }

        logger.info(
            "Weekly nutrition: %d days, avg %.0f kcal/day",
            days_count, daily_avg["calories"],
        )
        return result

    except Exception as e:
        logger.error("Weekly nutrition query failed: %s", e, exc_info=True)
        return {"error": str(e)}


async def check_deficiencies(
    daily_avg: dict,
    tool_context: ToolContext = None,
) -> dict:
    """Check daily average intake against Recommended Daily Allowances.

    Call this tool after get_weekly_nutrition to identify nutritional
    deficiencies or excesses. Uses standard adult RDA values.

    Args:
        daily_avg: dict with keys: calories, protein_g, carbs_g, fat_g, fiber_g.
        tool_context: ADK tool context.

    Returns:
        dict mapping each nutrient to {actual, rda, status, pct} where
        status is 'adequate', 'low', or 'deficit'.
    """
    try:
        result = nutrition_service.check_rda_compliance(daily_avg)

        # Add summary
        deficits = [
            k for k, v in result.items() if v.get("status") == "deficit"
        ]
        low = [
            k for k, v in result.items() if v.get("status") == "low"
        ]

        summary = {
            "compliance": result,
            "deficits": deficits,
            "low": low,
            "overall_status": (
                "good" if not deficits and not low
                else "attention_needed" if deficits
                else "fair"
            ),
        }

        logger.info(
            "Deficiency check: %d deficits, %d low",
            len(deficits), len(low),
        )
        return summary

    except Exception as e:
        logger.error("Deficiency check failed: %s", e, exc_info=True)
        return {"error": str(e)}


async def generate_nutrition_report(
    tool_context: ToolContext = None,
) -> str:
    """Generate a human-readable weekly nutrition report using Gemini.

    Call this tool when the user asks for a full nutrition report or
    dietary assessment. Combines weekly nutrition data and deficiency
    analysis, then uses Gemini to write a friendly, actionable report.

    Args:
        tool_context: ADK tool context.

    Returns:
        str — a multi-paragraph natural-language nutrition report.
    """
    try:
        # Gather data
        weekly = await get_weekly_nutrition(tool_context)
        if "error" in weekly or not weekly.get("daily_avg"):
            return (
                "Unable to generate nutrition report — no intake data logged "
                "in the last 7 days. Start logging your meals to get insights!"
            )

        deficiency = await check_deficiencies(weekly["daily_avg"], tool_context)

        import google.generativeai as genai

        prompt = f"""You are a friendly nutritionist for PantryMind.
Generate a concise weekly nutrition report based on this data.
Include 3-5 actionable recommendations.

Weekly summary:
- Period: {weekly.get('start_date')} to {weekly.get('end_date')}
- Days logged: {weekly.get('days_logged')}
- Daily averages: {weekly.get('daily_avg')}
- Total intake: {weekly.get('total')}

RDA compliance:
{deficiency}

Keep the tone supportive and motivational. Use ₹ for any cost references.
Focus on practical food suggestions available in India."""

        model = genai.GenerativeModel("gemini-3.1-pro")
        response = model.generate_content(prompt)
        report = response.text

        logger.info("Nutrition report generated (%d chars)", len(report))
        return report

    except Exception as e:
        logger.error("Nutrition report generation failed: %s", e, exc_info=True)
        # Fallback template
        return (
            f"Weekly Nutrition Summary\n"
            f"Period: {weekly.get('start_date', '?')} – {weekly.get('end_date', '?')}\n"
            f"Daily avg: {weekly.get('daily_avg', {}).get('calories', 0):.0f} kcal, "
            f"{weekly.get('daily_avg', {}).get('protein_g', 0):.1f}g protein\n"
            f"(Detailed AI report unavailable — see raw data above.)"
        )
