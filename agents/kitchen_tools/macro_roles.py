# agents/kitchen_tools/macro_roles.py

MACRO_ROLE_TO_CATEGORY_QUERY = {

    "protein": {
        "description": "Protein sources for muscle, satiety, and calorie density",
        "mongo_filter": {
            "$or": [
                # Direct animal proteins
                {"category": "MEAT_SEAFOOD"},
                # Eggs and hard/soft cheese
                {"category": "DAIRY_EGGS", "sub_category": {"$in": ["eggs", "hard_cheese", "soft_cheese"]}},
                # Plant proteins (dal, rajma, chana, soy)
                {"category": "PANTRY_DRY", "sub_category": "legumes_pulses"},
                # Packaged high-protein (e.g., canned tuna, sardines)
                {"category": "PANTRY_DRY", "sub_category": "canned_goods"},
                # Dairy protein (paneer, yogurt)
                {"category": "DAIRY_EGGS", "sub_category": {"$in": ["soft_cheese", "yogurt"]}},
            ]
        }
    },

    "carbohydrate": {
        "description": "Energy-dense carbohydrate sources",
        "mongo_filter": {
            "$or": [
                {"category": "PANTRY_DRY", "sub_category": {"$in": ["rice_pasta", "flour", "instant_food"]}},
                {"category": "BAKERY"},
                # Root vegetables are starchy carbs
                {"category": "PRODUCE", "sub_category": "root_vegetables"},
                # Fruits as natural carbs
                {"category": "PRODUCE", "sub_category": {"$in": ["tropical_fruits", "citrus_fruits", "berries"]}},
            ]
        }
    },

    "vegetable": {
        "description": "Fiber, micronutrients, volume with low calories",
        "mongo_filter": {
            "$or": [
                {"category": "PRODUCE", "sub_category": {
                    "$in": ["leafy_greens", "tomatoes_peppers", "mushrooms",
                            "herbs", "gourd_vegetables"]
                }},
                {"category": "FROZEN", "sub_category": "frozen_vegetables"},
            ]
        }
    },

    "dairy": {
        "description": "Calcium, fat, protein from dairy products",
        "mongo_filter": {
            "$or": [
                {"category": "DAIRY_EGGS"},
                {"category": "FROZEN", "sub_category": "ice_cream"},
            ]
        }
    },

    "fat": {
        "description": "Healthy fats for cooking, satiety, fat-soluble vitamins",
        "mongo_filter": {
            "$or": [
                {"category": "PANTRY_DRY", "sub_category": {"$in": ["oil", "oils"]}},
                {"category": "DAIRY_EGGS", "sub_category": "butter_cream"},
                {"category": "CONDIMENTS", "sub_category": "spread_butter"},
                {"category": "SNACKS", "sub_category": "nuts_dried_fruits"},
            ]
        }
    },

    "flavoring": {
        "description": "Spices, herbs, condiments that add flavor without bulk",
        "mongo_filter": {
            "$or": [
                {"category": "PANTRY_DRY", "sub_category": "spices_masala"},
                {"category": "CONDIMENTS"},
                {"category": "PRODUCE", "sub_category": {"$in": ["herbs", "onion_garlic"]}},
            ]
        }
    },

    "grain": {
        "description": "Whole grains and cereals",
        "mongo_filter": {
            "$or": [
                {"category": "PANTRY_DRY", "sub_category": {"$in": ["rice_pasta", "flour"]}},
                {"category": "BAKERY", "sub_category": "bread"},
            ]
        }
    }
}

# Dietary flag filters — applied on top of macro role queries
DIETARY_FILTERS = {
    "VEG":    {"dietary_flag": {"$in": ["VEG", "VEGAN", "DAIRY", "EGG"]}},
    "VEGAN":  {"dietary_flag": "VEGAN"},
    "NON_VEG":{"dietary_flag": {"$in": ["NON_VEG", "SEAFOOD", "VEG", "VEGAN", "DAIRY", "EGG"]}},
    "KETO":   {
        # Keto = high protein + fat, low carb. Exclude grains/sugar.
        "category": {"$nin": ["PANTRY_DRY", "BAKERY", "SNACKS", "BEVERAGES"]},
        "dietary_flag": {"$nin": ["NA"]}
    },
    "SEAFOOD_FREE": {"dietary_flag": {"$nin": ["SEAFOOD"]}},
    "DAIRY_FREE":   {"dietary_flag": {"$nin": ["DAIRY", "EGG"]}},
}
