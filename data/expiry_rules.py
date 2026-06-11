# backend/data/expiry_rules.py
# 
# Structure per entry:
#   shelf_life_days:  Maximum days the item stays safe from purchase date
#   safety_factor:    Multiply shelf_life by this to get the "safe use by" date
#   storage_note:     Human-readable storage tip shown in UI
#   track_as_warranty: For electronics — track as warranty, not food expiry

EXPIRY_DATASET = {

    # =========================================================
    # PRODUCE
    # =========================================================
    "PRODUCE": {
        "_meta": {
            "safety_factor_default": 0.50,  # Show 50% of shelf life as safe
            "reasoning": "Fresh produce degrades rapidly; conservative dates prevent food poisoning"
        },
        "leafy_greens": {
            # Spinach, lettuce, coriander, mint, curry leaves, methi
            "shelf_life_days": 5,
            "safety_factor": 0.50,
            "safe_days": 2,
            "storage_note": "Refrigerate in damp cloth or airtight container"
        },
        "root_vegetables": {
            # Potato, carrot, beetroot, radish, turnip, yam
            "shelf_life_days": 21,
            "safety_factor": 0.60,
            "safe_days": 13,
            "storage_note": "Store in cool, dark, dry place. Don't refrigerate potatoes."
        },
        "tomatoes_peppers": {
            # Tomatoes, capsicum, chilies, brinjal
            "shelf_life_days": 7,
            "safety_factor": 0.50,
            "safe_days": 3,
            "storage_note": "Room temperature until ripe, then refrigerate"
        },
        "tropical_fruits": {
            # Mango, papaya, banana, guava, chikoo
            "shelf_life_days": 5,
            "safety_factor": 0.50,
            "safe_days": 2,
            "storage_note": "Store at room temperature; refrigerate once cut"
        },
        "citrus_fruits": {
            # Orange, lemon, mosambi, grapefruit
            "shelf_life_days": 14,
            "safety_factor": 0.60,
            "safe_days": 8,
            "storage_note": "Room temperature for up to 1 week, then refrigerate"
        },
        "berries": {
            # Strawberries, grapes, blueberries
            "shelf_life_days": 5,
            "safety_factor": 0.50,
            "safe_days": 2,
            "storage_note": "Refrigerate immediately, wash only before eating"
        },
        "mushrooms": {
            "shelf_life_days": 5,
            "safety_factor": 0.50,
            "safe_days": 2,
            "storage_note": "Refrigerate in paper bag, never in plastic"
        },
        "herbs": {
            # Fresh coriander, mint, basil
            "shelf_life_days": 5,
            "safety_factor": 0.50,
            "safe_days": 2,
            "storage_note": "Store like flowers in a glass of water, cover loosely"
        },
        "onion_garlic": {
            # Onion, garlic, ginger, shallots
            "shelf_life_days": 30,
            "safety_factor": 0.65,
            "safe_days": 20,
            "storage_note": "Store in cool, dry, well-ventilated place"
        },
        "gourd_vegetables": {
            # Lauki, tinda, turai, karela, bhindi, peas
            "shelf_life_days": 7,
            "safety_factor": 0.55,
            "safe_days": 4,
            "storage_note": "Refrigerate in produce drawer"
        },
        "default": {
            "shelf_life_days": 7,
            "safety_factor": 0.50,
            "safe_days": 3,
            "storage_note": "Refrigerate and consume promptly"
        }
    },

    # =========================================================
    # MEAT & SEAFOOD  
    # =========================================================
    "MEAT_SEAFOOD": {
        "_meta": {
            "safety_factor_default": 0.50,
            "reasoning": "Raw meat is a high-risk category; 50% safety margin prevents serious illness"
        },
        "poultry": {
            # Chicken (all cuts), turkey, duck
            "shelf_life_days": 2,
            "safety_factor": 0.50,
            "safe_days": 1,
            "storage_note": "Refrigerate immediately; cook within 24hr or freeze"
        },
        "red_meat": {
            # Mutton, lamb, beef (where applicable), goat
            "shelf_life_days": 4,
            "safety_factor": 0.50,
            "safe_days": 2,
            "storage_note": "Refrigerate at 0-4°C; freeze if not using within 2 days"
        },
        "pork": {
            # Pork chops, bacon, ham
            "shelf_life_days": 3,
            "safety_factor": 0.50,
            "safe_days": 1,
            "storage_note": "Keep refrigerated below 4°C; best consumed same day"
        },
        "seafood_fish": {
            # Salmon, tuna, rohu, pomfret, kingfish, catla
            "shelf_life_days": 2,
            "safety_factor": 0.50,
            "safe_days": 1,
            "storage_note": "Most perishable protein; cook same day or freeze immediately"
        },
        "seafood_shellfish": {
            # Prawns, shrimp, crab, lobster, mussels
            "shelf_life_days": 1,
            "safety_factor": 0.50,
            "safe_days": 1,
            "storage_note": "CRITICAL: Cook within 24 hours of purchase or freeze"
        },
        "processed_deli": {
            # Salami, pepperoni, sausages, hot dogs, sliced deli meat
            "shelf_life_days": 7,
            "safety_factor": 0.55,
            "safe_days": 4,
            "storage_note": "Once opened, consume within 3-5 days; keep sealed"
        },
        "default": {
            "shelf_life_days": 2,
            "safety_factor": 0.50,
            "safe_days": 1,
            "storage_note": "Refrigerate and cook as soon as possible"
        }
    },

    # =========================================================
    # DAIRY & EGGS
    # =========================================================
    "DAIRY_EGGS": {
        "_meta": {
            "safety_factor_default": 0.55,
            "reasoning": "Dairy safety varies widely by type; eggs last longer than liquid dairy"
        },
        "milk": {
            # Full fat, toned, skimmed, plant-based (oat/almond/soy)
            "shelf_life_days": 7,
            "safety_factor": 0.50,
            "safe_days": 3,
            "storage_note": "Keep refrigerated at all times; never leave at room temperature"
        },
        "hard_cheese": {
            # Cheddar, parmesan, gouda, processed cheese blocks
            "shelf_life_days": 45,
            "safety_factor": 0.65,
            "safe_days": 29,
            "storage_note": "Wrap in parchment paper; refrigerate below 4°C"
        },
        "soft_cheese": {
            # Paneer, ricotta, cottage cheese, cream cheese, mozzarella
            "shelf_life_days": 5,
            "safety_factor": 0.55,
            "safe_days": 3,
            "storage_note": "Store in airtight container with water; highly perishable"
        },
        "yogurt": {
            # Curd, Greek yogurt, flavored yogurt, lassi
            "shelf_life_days": 10,
            "safety_factor": 0.50,
            "safe_days": 5,
            "storage_note": "Keep refrigerated; do not freeze plain yogurt"
        },
        "butter_cream": {
            # Butter, margarine, heavy cream, whipping cream, ghee
            "shelf_life_days": 30,
            "safety_factor": 0.65,
            "safe_days": 20,
            "storage_note": "Refrigerate butter; ghee can be stored at room temp"
        },
        "eggs": {
            "shelf_life_days": 21,
            "safety_factor": 0.60,
            "safe_days": 13,
            "storage_note": "Refrigerate; place in coldest part of fridge, not door"
        },
        "condensed_milk": {
            "shelf_life_days": 14,
            "safety_factor": 0.60,
            "safe_days": 8,
            "storage_note": "Once opened, refrigerate and consume within 2 weeks"
        },
        "default": {
            "shelf_life_days": 7,
            "safety_factor": 0.55,
            "safe_days": 4,
            "storage_note": "Refrigerate promptly"
        }
    },

    # =========================================================
    # FROZEN
    # =========================================================
    "FROZEN": {
        "_meta": {
            "safety_factor_default": 0.75,
            "reasoning": "Frozen items have much longer shelf life; 75% of max is generous but safe"
        },
        "frozen_meat": {
            # Frozen chicken, frozen mutton, frozen fish
            "shelf_life_days": 120,
            "safety_factor": 0.75,
            "safe_days": 90,
            "storage_note": "Keep at -18°C; do not refreeze after thawing"
        },
        "frozen_meals": {
            # Ready-to-eat frozen meals, frozen parathas, samosas
            "shelf_life_days": 90,
            "safety_factor": 0.75,
            "safe_days": 67,
            "storage_note": "Check package date; maintain continuous freezer storage"
        },
        "ice_cream": {
            "shelf_life_days": 60,
            "safety_factor": 0.75,
            "safe_days": 45,
            "storage_note": "Store at -18°C; texture degrades with temperature fluctuations"
        },
        "frozen_vegetables": {
            # Frozen peas, corn, mixed veg
            "shelf_life_days": 180,
            "safety_factor": 0.75,
            "safe_days": 135,
            "storage_note": "Keep frozen; high vitamin retention when cooked directly from frozen"
        },
        "frozen_seafood": {
            "shelf_life_days": 90,
            "safety_factor": 0.75,
            "safe_days": 67,
            "storage_note": "Keep frozen; thaw in refrigerator overnight, never at room temperature"
        },
        "default": {
            "shelf_life_days": 90,
            "safety_factor": 0.75,
            "safe_days": 67,
            "storage_note": "Keep frozen at -18°C"
        }
    },

    # =========================================================
    # BAKERY
    # =========================================================
    "BAKERY": {
        "_meta": {
            "safety_factor_default": 0.60,
            "reasoning": "Baked goods stale before becoming dangerous; early alert prevents waste"
        },
        "bread": {
            # White bread, brown bread, whole wheat, buns, rolls
            "shelf_life_days": 7,
            "safety_factor": 0.60,
            "safe_days": 4,
            "storage_note": "Keep in breadbox or paper bag; refrigerating dries it out"
        },
        "pastry": {
            # Croissants, danishes, puffs
            "shelf_life_days": 2,
            "safety_factor": 0.55,
            "safe_days": 1,
            "storage_note": "Best consumed same day; refrigerate for next day only"
        },
        "cakes": {
            "shelf_life_days": 4,
            "safety_factor": 0.55,
            "safe_days": 2,
            "storage_note": "Refrigerate cream cakes; unfrosted cakes can stay at room temp"
        },
        "rusk_biscuits": {
            # Packaged rusk, marie biscuits
            "shelf_life_days": 60,
            "safety_factor": 0.75,
            "safe_days": 45,
            "storage_note": "Store in airtight container; keep moisture-free"
        },
        "default": {
            "shelf_life_days": 5,
            "safety_factor": 0.60,
            "safe_days": 3,
            "storage_note": "Check for mold; store in cool, dry place"
        }
    },

    # =========================================================
    # BEVERAGES
    # =========================================================
    "BEVERAGES": {
        "_meta": {
            "safety_factor_default": 0.75,
            "reasoning": "Most beverages are packaged; 75% of shelf life is appropriate"
        },
        "juice_fresh": {
            # Cold-pressed, fresh squeezed, no preservatives
            "shelf_life_days": 4,
            "safety_factor": 0.55,
            "safe_days": 2,
            "storage_note": "Keep refrigerated; shake before drinking; highly perishable"
        },
        "juice_packed": {
            # Tetra-pack, bottled juice (Real, Tropicana, B Natural)
            "shelf_life_days": 180,
            "safety_factor": 0.75,
            "safe_days": 135,
            "storage_note": "Once opened, refrigerate and consume within 5-7 days"
        },
        "soda_carbonated": {
            # Pepsi, Coke, Sprite, soda water
            "shelf_life_days": 120,
            "safety_factor": 0.75,
            "safe_days": 90,
            "storage_note": "Keep sealed; store upright; consume within days of opening"
        },
        "water": {
            "shelf_life_days": 365,
            "safety_factor": 0.75,
            "safe_days": 274,
            "storage_note": "Store away from sunlight and strong odors"
        },
        "alcohol_beer": {
            "shelf_life_days": 90,
            "safety_factor": 0.75,
            "safe_days": 67,
            "storage_note": "Refrigerate for best taste; avoid sunlight exposure"
        },
        "alcohol_spirits": {
            "shelf_life_days": 730,
            "safety_factor": 0.75,
            "safe_days": 547,
            "storage_note": "Store upright in cool, dark place; opened bottles 1-2 years"
        },
        "hot_beverage": {
            # Tea, coffee, Bournvita, Horlicks, health mixes
            "shelf_life_days": 365,
            "safety_factor": 0.75,
            "safe_days": 274,
            "storage_note": "Store in airtight container away from moisture and strong smells"
        },
        "energy_drinks": {
            "shelf_life_days": 180,
            "safety_factor": 0.75,
            "safe_days": 135,
            "storage_note": "Store in cool, dry place"
        },
        "default": {
            "shelf_life_days": 180,
            "safety_factor": 0.75,
            "safe_days": 135,
            "storage_note": "Check product date; refrigerate once opened"
        }
    },

    # =========================================================
    # PANTRY / DRY GOODS
    # =========================================================
    "PANTRY_DRY": {
        "_meta": {
            "safety_factor_default": 0.75,
            "reasoning": "Dry goods are shelf-stable; 75% of shelf life prevents staleness"
        },
        "rice_pasta": {
            # White rice, brown rice, pasta, noodles, vermicelli
            "shelf_life_days": 730,
            "safety_factor": 0.75,
            "safe_days": 548,
            "storage_note": "Store in airtight container; check for weevils periodically"
        },
        "flour": {
            # Maida, atta, besan, sooji, cornflour
            "shelf_life_days": 365,
            "safety_factor": 0.75,
            "safe_days": 274,
            "storage_note": "Airtight container in cool, dry place; whole wheat flour lasts less"
        },
        "legumes_pulses": {
            # Dal, rajma, chana, moong, masoor
            "shelf_life_days": 365,
            "safety_factor": 0.75,
            "safe_days": 274,
            "storage_note": "Airtight container; older lentils take longer to cook"
        },
        "canned_goods": {
            # Canned tomatoes, beans, corn, tuna, sardines
            "shelf_life_days": 730,
            "safety_factor": 0.75,
            "safe_days": 548,
            "storage_note": "Store in cool, dry place; use within days of opening (refrigerate)"
        },
        "spices_masala": {
            # Whole and ground spices, masala mixes, MDH, Everest
            "shelf_life_days": 365,
            "safety_factor": 0.75,
            "safe_days": 274,
            "storage_note": "Airtight container; away from heat and light; whole spices last longer"
        },
        "oil": {
            # Sunflower, mustard, coconut, olive, groundnut oil
            "shelf_life_days": 365,
            "safety_factor": 0.75,
            "safe_days": 274,
            "storage_note": "Store away from heat and light; coconut oil solidifies in cold"
        },
        "sugar_salt": {
            "shelf_life_days": 1825,   # 5 years
            "safety_factor": 0.75,
            "safe_days": 1369,
            "storage_note": "Airtight container away from moisture; sugar may clump"
        },
        "pickles_preserves": {
            # Achaar, jam, marmalade, honey
            "shelf_life_days": 365,
            "safety_factor": 0.75,
            "safe_days": 274,
            "storage_note": "Refrigerate after opening; always use dry spoon to prevent contamination"
        },
        "instant_food": {
            # Maggi, Cup Noodles, instant oats, upma mixes
            "shelf_life_days": 180,
            "safety_factor": 0.75,
            "safe_days": 135,
            "storage_note": "Store in cool, dry place away from moisture"
        },
        "default": {
            "shelf_life_days": 365,
            "safety_factor": 0.75,
            "safe_days": 274,
            "storage_note": "Store in airtight container in cool, dry pantry"
        }
    },

    # =========================================================
    # SNACKS
    # =========================================================
    "SNACKS": {
        "_meta": {
            "safety_factor_default": 0.75,
            "reasoning": "Packaged snacks stale before expiry; 75% keeps them optimal"
        },
        "chips_crisps": {
            # Lays, Kurkure, Pringles, popcorn
            "shelf_life_days": 90,
            "safety_factor": 0.75,
            "safe_days": 67,
            "storage_note": "Once opened, transfer to airtight container"
        },
        "cookies_biscuits": {
            # Parle-G, Good Day, Oreo, Marie Gold
            "shelf_life_days": 120,
            "safety_factor": 0.75,
            "safe_days": 90,
            "storage_note": "Keep sealed; humidity makes biscuits soft"
        },
        "namkeen": {
            # Bhujia, mixture, chakli, mathri
            "shelf_life_days": 60,
            "safety_factor": 0.75,
            "safe_days": 45,
            "storage_note": "Airtight container; moisture is the enemy"
        },
        "nuts_dried_fruits": {
            # Almonds, cashews, raisins, dates, walnuts
            "shelf_life_days": 180,
            "safety_factor": 0.75,
            "safe_days": 135,
            "storage_note": "Refrigerate for extended shelf life; airtight container"
        },
        "chocolate_candy": {
            # Dairy Milk, Kit Kat, Eclairs, candies
            "shelf_life_days": 270,
            "safety_factor": 0.75,
            "safe_days": 202,
            "storage_note": "Cool, dark place; chocolate blooms when temperature fluctuates"
        },
        "default": {
            "shelf_life_days": 90,
            "safety_factor": 0.75,
            "safe_days": 67,
            "storage_note": "Seal after opening to maintain crunch"
        }
    },

    # =========================================================
    # CONDIMENTS
    # =========================================================
    "CONDIMENTS": {
        "_meta": {
            "safety_factor_default": 0.75,
            "reasoning": "High acid/salt content extends shelf life"
        },
        "ketchup_sauces": {
            # Maggi ketchup, Heinz, hot sauce, Tabasco
            "shelf_life_days": 180,
            "safety_factor": 0.75,
            "safe_days": 135,
            "storage_note": "Refrigerate after opening; check for discoloration"
        },
        "mayonnaise": {
            "shelf_life_days": 60,
            "safety_factor": 0.70,
            "safe_days": 42,
            "storage_note": "Refrigerate after opening; egg-based mayo is higher risk"
        },
        "vinegar_mustard": {
            "shelf_life_days": 730,
            "safety_factor": 0.75,
            "safe_days": 548,
            "storage_note": "Very long shelf life; store away from heat"
        },
        "spread_butter": {
            # Peanut butter, Nutella, fruit spreads
            "shelf_life_days": 180,
            "safety_factor": 0.75,
            "safe_days": 135,
            "storage_note": "Refrigerate natural peanut butter; others can stay at room temp"
        },
        "default": {
            "shelf_life_days": 180,
            "safety_factor": 0.75,
            "safe_days": 135,
            "storage_note": "Refrigerate after opening"
        }
    },

    # =========================================================
    # NON-FOOD CATEGORIES (no food expiry)
    # =========================================================
    "HOUSEHOLD": {
        "_meta": {"is_consumable": False},
        "default": {
            "shelf_life_days": None,
            "safety_factor": None,
            "safe_days": None,
            "storage_note": "Store per product label; keep chemicals away from children"
        }
    },
    "PERSONAL_CARE": {
        "_meta": {"is_consumable": False},
        "toiletries": {
            # Shampoo, conditioner, face wash, body lotion
            "shelf_life_days": 548,   # ~18 months typical PAO
            "safety_factor": 1.0,     # Use full estimated life (printed PAO symbol)
            "safe_days": 548,
            "storage_note": "Check Period After Opening (PAO) symbol on packaging"
        },
        "toothpaste": {
            "shelf_life_days": 730,
            "safety_factor": 1.0,
            "safe_days": 730,
            "storage_note": "Store in cool, dry place"
        },
        "soap": {
            "shelf_life_days": 1095,   # 3 years
            "safety_factor": 1.0,
            "safe_days": 1095,
            "storage_note": "Store in dry place; some fragrance loss over time"
        },
        "default": {
            "shelf_life_days": 548,
            "safety_factor": 1.0,
            "safe_days": 548,
            "storage_note": "Check product expiry printed on packaging"
        }
    },
    "CLOTHING": {
        "_meta": {"is_consumable": False},
        "default": {
            "shelf_life_days": None,
            "safety_factor": None,
            "safe_days": None,
            "storage_note": "No expiry. Tracked for purchase history only."
        }
    },
    "ELECTRONICS": {
        "_meta": {"is_consumable": False, "track_as_warranty": True},
        "batteries": {
            "shelf_life_days": 1825,   # 5-year shelf life
            "safety_factor": 1.0,
            "safe_days": 1825,
            "storage_note": "Store at room temperature; cold storage extends shelf life"
        },
        "default": {
            "shelf_life_days": 365,    # 1-year default warranty assumption
            "safety_factor": 1.0,
            "safe_days": 365,
            "storage_note": "Tracked as warranty period. Check manufacturer warranty card."
        }
    },
    "MEDICATIONS": {
        "_meta": {"is_consumable": True},
        "default": {
            "shelf_life_days": 365,
            "safety_factor": 0.85,    # Use 85% — medications can lose potency before expiry
            "safe_days": 310,
            "storage_note": "IMPORTANT: Always follow printed expiry date on packaging"
        }
    },
    "BABY_PRODUCTS": {
        "_meta": {"is_consumable": True},
        "baby_food": {
            "shelf_life_days": 365,
            "safety_factor": 0.75,
            "safe_days": 274,
            "storage_note": "Strictly follow manufacturer expiry date for infant safety"
        },
        "formula": {
            "shelf_life_days": 30,    # Once opened
            "safety_factor": 0.75,
            "safe_days": 22,
            "storage_note": "Once opened, use within 1 month; do not freeze"
        },
        "diapers": {
            "shelf_life_days": None,
            "safety_factor": None,
            "safe_days": None,
            "storage_note": "No expiry. Store in cool, dry place."
        },
        "default": {
            "shelf_life_days": 365,
            "safety_factor": 0.75,
            "safe_days": 274,
            "storage_note": "Always check manufacturer expiry for baby safety"
        }
    },
    "PET_SUPPLIES": {
        "_meta": {"is_consumable": True},
        "pet_food_dry": {
            "shelf_life_days": 365,
            "safety_factor": 0.75,
            "safe_days": 274,
            "storage_note": "Airtight container; check bag date and seal after each use"
        },
        "pet_food_wet": {
            "shelf_life_days": 3,     # Once opened
            "safety_factor": 0.65,
            "safe_days": 2,
            "storage_note": "Refrigerate unused portion; use within 2-3 days"
        },
        "default": {
            "shelf_life_days": 180,
            "safety_factor": 0.75,
            "safe_days": 135,
            "storage_note": "Check product date; store per label"
        }
    },
    "OTHER": {
        "_meta": {},
        "default": {
            "shelf_life_days": 90,
            "safety_factor": 0.75,
            "safe_days": 67,
            "storage_note": "Check product packaging for storage instructions"
        }
    }
}
