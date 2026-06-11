"""
PantryMind — Product Image Dataset
Maps common grocery item names to static image filenames.
Used as Tier 1 (fast, local) before falling back to AI generation.
"""

# Mapping: normalized_name (lowercase) → image filename
# Images are served from /product-images/dataset/
PRODUCT_IMAGE_DATASET = {
    # ── PRODUCE ──
    "apple": "apple.webp",
    "banana": "banana.webp",
    "tomato": "tomato.webp",
    "tomatoes": "tomato.webp",
    "potato": "potato.webp",
    "potatoes": "potato.webp",
    "onion": "onion.webp",
    "onions": "onion.webp",
    "garlic": "garlic.webp",
    "ginger": "ginger.webp",
    "carrot": "carrot.webp",
    "carrots": "carrot.webp",
    "spinach": "spinach.webp",
    "palak": "spinach.webp",
    "coriander": "coriander.webp",
    "green chili": "green_chili.webp",
    "green chilli": "green_chili.webp",
    "capsicum": "capsicum.webp",
    "bell pepper": "capsicum.webp",
    "cucumber": "cucumber.webp",
    "lemon": "lemon.webp",
    "lime": "lemon.webp",
    "orange": "orange.webp",
    "mango": "mango.webp",
    "grapes": "grapes.webp",
    "pomegranate": "pomegranate.webp",
    "watermelon": "watermelon.webp",
    "papaya": "papaya.webp",
    "guava": "guava.webp",
    "mushroom": "mushroom.webp",
    "mushrooms": "mushroom.webp",
    "brinjal": "brinjal.webp",
    "eggplant": "brinjal.webp",
    "cauliflower": "cauliflower.webp",
    "cabbage": "cabbage.webp",
    "beetroot": "beetroot.webp",
    "radish": "radish.webp",
    "peas": "peas.webp",
    "green peas": "peas.webp",
    "bhindi": "okra.webp",
    "okra": "okra.webp",
    "lady finger": "okra.webp",
    "mint": "mint.webp",
    "pudina": "mint.webp",
    "curry leaves": "curry_leaves.webp",

    # ── MEAT & SEAFOOD ──
    "chicken": "chicken.webp",
    "chicken breast": "chicken_breast.webp",
    "chicken thigh": "chicken.webp",
    "chicken wings": "chicken_wings.webp",
    "mutton": "mutton.webp",
    "lamb": "mutton.webp",
    "goat meat": "mutton.webp",
    "fish": "fish.webp",
    "fish fillet": "fish_fillet.webp",
    "salmon": "salmon.webp",
    "prawns": "prawns.webp",
    "shrimp": "prawns.webp",
    "eggs": "eggs.webp",
    "egg": "eggs.webp",

    # ── DAIRY ──
    "milk": "milk.webp",
    "amul milk": "milk.webp",
    "curd": "curd.webp",
    "yogurt": "curd.webp",
    "paneer": "paneer.webp",
    "cottage cheese": "paneer.webp",
    "butter": "butter.webp",
    "amul butter": "butter.webp",
    "cheese": "cheese.webp",
    "cream": "cream.webp",
    "ghee": "ghee.webp",

    # ── PANTRY & DRY GOODS ──
    "rice": "rice.webp",
    "basmati rice": "basmati_rice.webp",
    "wheat flour": "wheat_flour.webp",
    "atta": "wheat_flour.webp",
    "maida": "maida.webp",
    "sugar": "sugar.webp",
    "salt": "salt.webp",
    "cooking oil": "cooking_oil.webp",
    "sunflower oil": "sunflower_oil.webp",
    "mustard oil": "mustard_oil.webp",
    "olive oil": "olive_oil.webp",
    "dal": "dal.webp",
    "toor dal": "dal.webp",
    "moong dal": "moong_dal.webp",
    "chana dal": "chana_dal.webp",
    "masoor dal": "dal.webp",
    "rajma": "rajma.webp",
    "kidney beans": "rajma.webp",
    "chana": "chana.webp",
    "chickpeas": "chana.webp",
    "turmeric": "turmeric.webp",
    "haldi": "turmeric.webp",
    "red chili powder": "red_chili.webp",
    "cumin": "cumin.webp",
    "jeera": "cumin.webp",
    "cinnamon": "cinnamon.webp",
    "tea": "tea.webp",
    "coffee": "coffee.webp",
    "noodles": "noodles.webp",
    "maggi": "noodles.webp",
    "pasta": "pasta.webp",
    "oats": "oats.webp",
    "poha": "poha.webp",
    "sooji": "sooji.webp",
    "besan": "besan.webp",
    "honey": "honey.webp",

    # ── SNACKS ──
    "chips": "chips.webp",
    "biscuits": "biscuits.webp",
    "cookies": "cookies.webp",
    "namkeen": "namkeen.webp",
    "mixture": "namkeen.webp",
    "almonds": "almonds.webp",
    "cashew": "cashew.webp",
    "cashews": "cashew.webp",
    "peanuts": "peanuts.webp",
    "raisins": "raisins.webp",
    "dates": "dates.webp",
    "chocolate": "chocolate.webp",

    # ── BEVERAGES ──
    "juice": "juice.webp",
    "water": "water.webp",
    "soda": "soda.webp",
    "cola": "soda.webp",
    "coconut water": "coconut_water.webp",

    # ── BAKERY ──
    "bread": "bread.webp",
    "pav": "bread.webp",

    # ── CONDIMENTS ──
    "ketchup": "ketchup.webp",
    "tomato sauce": "ketchup.webp",
    "mayonnaise": "mayonnaise.webp",
    "pickle": "pickle.webp",
    "achaar": "pickle.webp",
    "jam": "jam.webp",
    "peanut butter": "peanut_butter.webp",

    # ── FROZEN ──
    "frozen peas": "frozen_peas.webp",
    "frozen corn": "frozen_corn.webp",
    "ice cream": "ice_cream.webp",
}


def find_product_image(item_name: str) -> str | None:
    """
    Find a product image from the static dataset.
    Uses exact match first, then substring matching.
    Returns image filename or None.
    """
    name_lower = item_name.lower().strip()

    # Exact match
    if name_lower in PRODUCT_IMAGE_DATASET:
        return PRODUCT_IMAGE_DATASET[name_lower]

    # Substring match: check if any key is contained in the item name
    for key, filename in PRODUCT_IMAGE_DATASET.items():
        if key in name_lower or name_lower in key:
            return filename

    return None
