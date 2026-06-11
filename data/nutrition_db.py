# data/nutrition_db.py
# All values per 100g / 100ml

NUTRITION_DB = {
    # ─── MEAT & SEAFOOD ───────────────────────────────────────────
    "chicken breast":        {"calories": 165, "protein": 31.0, "carbs": 0.0,  "fat": 3.6,  "fiber": 0.0},
    "chicken thigh":         {"calories": 209, "protein": 26.0, "carbs": 0.0,  "fat": 11.0, "fiber": 0.0},
    "mutton":                {"calories": 218, "protein": 25.6, "carbs": 0.0,  "fat": 13.0, "fiber": 0.0},
    "mutton raan":           {"calories": 218, "protein": 25.6, "carbs": 0.0,  "fat": 13.0, "fiber": 0.0},
    "salmon":                {"calories": 208, "protein": 20.0, "carbs": 0.0,  "fat": 13.0, "fiber": 0.0},
    "salmon fillet":         {"calories": 208, "protein": 20.0, "carbs": 0.0,  "fat": 13.0, "fiber": 0.0},
    "pork chop":             {"calories": 242, "protein": 27.0, "carbs": 0.0,  "fat": 14.0, "fiber": 0.0},
    "bacon":                 {"calories": 541, "protein": 37.0, "carbs": 1.4,  "fat": 42.0, "fiber": 0.0},
    "prawns":                {"calories":  99, "protein": 24.0, "carbs": 0.2,  "fat": 0.3,  "fiber": 0.0},
    "pepperoni":             {"calories": 494, "protein": 22.0, "carbs": 1.2,  "fat": 44.0, "fiber": 0.0},
    "sliced pepperoni":      {"calories": 494, "protein": 22.0, "carbs": 1.2,  "fat": 44.0, "fiber": 0.0},
    "chicken nuggets":       {"calories": 260, "protein": 14.0, "carbs": 17.0, "fat": 15.0, "fiber": 0.8},
    "tuna":                  {"calories": 132, "protein": 29.0, "carbs": 0.0,  "fat": 1.3,  "fiber": 0.0},
    "sardines":              {"calories": 208, "protein": 24.5, "carbs": 0.0,  "fat": 11.5, "fiber": 0.0},
    "rohu fish":             {"calories": 107, "protein": 16.6, "carbs": 0.0,  "fat": 4.4,  "fiber": 0.0},
    "pomfret":               {"calories": 118, "protein": 19.0, "carbs": 0.0,  "fat": 4.0,  "fiber": 0.0},

    # ─── DAIRY & EGGS ─────────────────────────────────────────────
    "egg":                   {"calories":  68, "protein": 5.5,  "carbs": 0.6,  "fat": 4.8,  "fiber": 0.0},
    "whole milk":            {"calories":  61, "protein": 3.2,  "carbs": 4.8,  "fat": 3.3,  "fiber": 0.0},
    "toned milk":            {"calories":  46, "protein": 3.5,  "carbs": 5.0,  "fat": 1.5,  "fiber": 0.0},
    "paneer":                {"calories": 265, "protein": 18.3, "carbs": 1.2,  "fat": 20.8, "fiber": 0.0},
    "cheddar cheese":        {"calories": 402, "protein": 25.0, "carbs": 1.3,  "fat": 33.0, "fiber": 0.0},
    "processed cheese":      {"calories": 330, "protein": 20.0, "carbs": 2.5,  "fat": 26.0, "fiber": 0.0},
    "greek yogurt":          {"calories":  59, "protein": 10.0, "carbs": 3.6,  "fat": 0.4,  "fiber": 0.0},
    "curd":                  {"calories":  98, "protein": 3.1,  "carbs": 3.4,  "fat": 4.3,  "fiber": 0.0},
    "butter":                {"calories": 717, "protein": 0.9,  "carbs": 0.1,  "fat": 81.0, "fiber": 0.0},
    "ghee":                  {"calories": 900, "protein": 0.0,  "carbs": 0.0,  "fat": 100.0,"fiber": 0.0},
    "heavy cream":           {"calories": 340, "protein": 2.1,  "carbs": 2.8,  "fat": 36.0, "fiber": 0.0},

    # ─── PRODUCE ──────────────────────────────────────────────────
    "spinach":               {"calories":  23, "protein": 2.9,  "carbs": 3.6,  "fat": 0.4,  "fiber": 2.2},
    "tomato":                {"calories":  18, "protein": 0.9,  "carbs": 3.9,  "fat": 0.2,  "fiber": 1.2},
    "onion":                 {"calories":  40, "protein": 1.1,  "carbs": 9.3,  "fat": 0.1,  "fiber": 1.7},
    "garlic":                {"calories": 149, "protein": 6.4,  "carbs": 33.1, "fat": 0.5,  "fiber": 2.1},
    "ginger":                {"calories":  80, "protein": 1.8,  "carbs": 18.0, "fat": 0.8,  "fiber": 2.0},
    "potato":                {"calories":  77, "protein": 2.0,  "carbs": 17.5, "fat": 0.1,  "fiber": 2.2},
    "carrot":                {"calories":  41, "protein": 0.9,  "carbs": 9.6,  "fat": 0.2,  "fiber": 2.8},
    "capsicum":              {"calories":  31, "protein": 1.0,  "carbs": 6.0,  "fat": 0.3,  "fiber": 2.1},
    "brinjal":               {"calories":  25, "protein": 1.0,  "carbs": 6.0,  "fat": 0.2,  "fiber": 3.0},
    "mushroom":              {"calories":  22, "protein": 3.1,  "carbs": 3.3,  "fat": 0.3,  "fiber": 1.0},
    "cauliflower":           {"calories":  25, "protein": 1.9,  "carbs": 5.0,  "fat": 0.3,  "fiber": 2.0},
    "peas":                  {"calories":  81, "protein": 5.4,  "carbs": 14.5, "fat": 0.4,  "fiber": 5.7},
    "banana":                {"calories":  89, "protein": 1.1,  "carbs": 23.0, "fat": 0.3,  "fiber": 2.6},
    "mango":                 {"calories":  60, "protein": 0.8,  "carbs": 15.0, "fat": 0.4,  "fiber": 1.6},
    "lemon":                 {"calories":  29, "protein": 1.1,  "carbs": 9.3,  "fat": 0.3,  "fiber": 2.8},

    # ─── PANTRY / DRY GOODS ───────────────────────────────────────
    "basmati rice":          {"calories": 356, "protein": 7.1,  "carbs": 78.2, "fat": 0.6,  "fiber": 1.0},
    "white rice":            {"calories": 365, "protein": 7.0,  "carbs": 79.0, "fat": 0.7,  "fiber": 0.4},
    "atta":                  {"calories": 340, "protein": 12.0, "carbs": 70.0, "fat": 1.5,  "fiber": 12.0},
    "maida":                 {"calories": 348, "protein": 9.3,  "carbs": 74.5, "fat": 1.0,  "fiber": 2.7},
    "pasta":                 {"calories": 371, "protein": 13.0, "carbs": 74.7, "fat": 1.5,  "fiber": 3.2},
    "maggi noodles":         {"calories": 430, "protein": 9.0,  "carbs": 59.0, "fat": 17.0, "fiber": 2.5},
    "oats":                  {"calories": 389, "protein": 17.0, "carbs": 66.0, "fat": 7.0,  "fiber": 10.6},
    "moong dal":             {"calories": 347, "protein": 24.0, "carbs": 59.7, "fat": 1.2,  "fiber": 16.3},
    "masoor dal":            {"calories": 352, "protein": 25.0, "carbs": 59.0, "fat": 1.1,  "fiber": 10.7},
    "chana dal":             {"calories": 364, "protein": 20.0, "carbs": 61.0, "fat": 5.6,  "fiber": 17.4},
    "rajma":                 {"calories": 127, "protein": 8.7,  "carbs": 22.8, "fat": 0.5,  "fiber": 7.4},  # cooked
    "besan":                 {"calories": 387, "protein": 22.0, "carbs": 58.0, "fat": 6.0,  "fiber": 10.9},
    "sunflower oil":         {"calories": 884, "protein": 0.0,  "carbs": 0.0,  "fat": 100.0,"fiber": 0.0},
    "mustard oil":           {"calories": 884, "protein": 0.0,  "carbs": 0.0,  "fat": 100.0,"fiber": 0.0},
    "olive oil":             {"calories": 884, "protein": 0.0,  "carbs": 0.0,  "fat": 100.0,"fiber": 0.0},

    # ─── SNACKS & BAKERY ──────────────────────────────────────────
    "bread":                 {"calories": 265, "protein": 9.0,  "carbs": 49.0, "fat": 3.2,  "fiber": 2.7},
    "almonds":               {"calories": 579, "protein": 21.2, "carbs": 21.6, "fat": 49.9, "fiber": 12.5},
    "cashews":               {"calories": 553, "protein": 18.2, "carbs": 30.2, "fat": 43.9, "fiber": 3.3},
    "peanut butter":         {"calories": 588, "protein": 25.0, "carbs": 20.0, "fat": 50.0, "fiber": 6.0},

    # ─── CONDIMENTS ───────────────────────────────────────────────
    "tomato ketchup":        {"calories": 112, "protein": 1.4,  "carbs": 26.0, "fat": 0.1,  "fiber": 0.5},
    "soy sauce":             {"calories":  53, "protein": 5.6,  "carbs": 4.9,  "fat": 0.6,  "fiber": 0.8},
}
