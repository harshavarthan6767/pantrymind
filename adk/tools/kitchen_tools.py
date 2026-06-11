from services.meal_optimizer import run_meal_optimizer as _run_optimizer
import asyncio

def run_meal_optimizer(
    available_items: list,
    calorie_target: int,
    protein_min_grams: float = 30.0,
    dietary_preference: str = "NON_VEG",
    meal_type: str = "dinner"
) -> dict:
    """
    Wraps the existing PuLP meal optimizer from services/meal_optimizer.py.
    ADK calls this as a FunctionTool — must be synchronous or wrapped.

    Returns exact gram portions for each ingredient that hit the macro targets.
    """
    # Get nutrition data for items (uses local DB + USDA fallback)
    item_names   = [item.get("name", item.get("normalized_name", "")) for item in available_items]
    
    # Mock nutrition lookup for wrapper
    nutrition_db = {}
    
    targets = {
        "calories":    calorie_target,
        "protein_min": protein_min_grams,
    }

    result = _run_optimizer(available_items, nutrition_db, targets, meal_type)
    return result


def build_macro_role_query(role: str, dietary_preference: str = None) -> dict:
    """
    Returns the MongoDB find() filter for a given macro nutritional role.
    
    The Kitchen Agent calls this to know what filter to pass to the MCP find() tool.
    This keeps the MongoDB query logic in Python, not inside the agent prompt.
    """
    from adk.agents.kitchen_agent import MACRO_ROLE_TO_CATEGORY_QUERY, DIETARY_FILTERS
    
    role_config = MACRO_ROLE_TO_CATEGORY_QUERY.get(role, {})
    base_filter = dict(role_config.get("mongo_filter", {}))
    base_filter["is_consumed"] = False
    
    if dietary_preference and dietary_preference in DIETARY_FILTERS:
        base_filter.update(DIETARY_FILTERS[dietary_preference])
    
    return {
        "collection":  "inventory",
        "filter":      base_filter,
        "description": role_config.get("description", f"{role} sources")
    }

def get_nutrition_for_items(items: list) -> dict:
    return {}
