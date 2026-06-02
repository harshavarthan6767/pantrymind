#!/usr/bin/env python3
"""Build expiry_kb.json from USDA FoodKeeper data.

Source: USDA FoodKeeper application data (data.gov)
https://catalog.data.gov/dataset/foodkeeper-data

This script:
1. Downloads or reads the FoodKeeper product CSV
2. Normalizes shelf-life values to days
3. Maps categories
4. Outputs data/expiry_kb.json
"""

import csv
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FOODKEEPER_CSV_URL = (
    "https://data.gov/api/views/cxgb-2r8f/rows.csv?accessType=DOWNLOAD"
)
FALLBACK_CSV_URL = (
    "https://raw.githubusercontent.com/nicholasgasior/usda-foodkeeper/"
    "master/data/products.csv"
)

OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = OUTPUT_DIR / "expiry_kb.json"

# Mapping from USDA FoodKeeper category IDs → simplified PantryMind categories
CATEGORY_MAP: dict[int | str, str] = {
    1: "baby_food",
    2: "baked_goods",
    3: "beverages",
    4: "condiments",
    5: "dairy",
    6: "deli",
    7: "fish_shellfish",
    8: "fruits",
    9: "grains_pasta",
    10: "meat",
    11: "meat",          # poultry → meat
    12: "nuts",
    13: "prepared_foods",
    14: "produce",       # vegetables
    15: "snacks",
    16: "spices",
    17: "other",
}

# Time-unit multipliers to convert to days
UNIT_TO_DAYS: dict[str, float] = {
    "Days": 1.0,
    "Weeks": 7.0,
    "Months": 30.0,
    "Years": 365.0,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _download_csv(url: str, dest: Path) -> Path:
    """Download a CSV from *url* and save to *dest*. Returns *dest*."""
    import urllib.request
    import urllib.error

    logger.info("Downloading FoodKeeper CSV from %s …", url)
    try:
        urllib.request.urlretrieve(url, dest)
        logger.info("Saved to %s", dest)
        return dest
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to download {url}: {exc}") from exc


def _normalise_days(value: Any, unit: str | None) -> int | None:
    """Convert a numeric *value* with a time *unit* string into whole days.

    Returns ``None`` when the value cannot be converted.
    """
    if value is None or value == "" or unit is None or unit == "":
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    multiplier = UNIT_TO_DAYS.get(unit, UNIT_TO_DAYS.get(unit.capitalize(), None))
    if multiplier is None:
        logger.warning("Unknown time unit '%s' – skipping value %s", unit, value)
        return None
    return int(round(numeric * multiplier))


def _resolve_category(cat_id: Any) -> str:
    """Map a USDA category identifier to a simplified PantryMind category."""
    try:
        key = int(cat_id)
    except (TypeError, ValueError):
        key = str(cat_id).strip().lower()
    return CATEGORY_MAP.get(key, "other")


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------


def load_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV file and return a list of row dicts."""
    logger.info("Reading CSV from %s", path)
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    logger.info("Loaded %d rows", len(rows))
    return rows


def process_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Transform raw FoodKeeper rows into normalised expiry records.

    Expected CSV columns (FoodKeeper schema):
        ID, Category_ID, Name, Name_subtitle,
        Pantry_Min, Pantry_Max, Pantry_Metric,
        Pantry_After_Opening_Min, Pantry_After_Opening_Max, Pantry_After_Opening_Metric,
        Refrigerate_Min, Refrigerate_Max, Refrigerate_Metric,
        Refrigerate_After_Opening_Min, Refrigerate_After_Opening_Max,
        Refrigerate_After_Opening_Metric,
        Freeze_Min, Freeze_Max, Freeze_Metric,
        …
    """
    results: list[dict[str, Any]] = []
    skipped = 0

    for row in rows:
        name = (row.get("Name") or row.get("Product_Name") or "").strip()
        if not name:
            skipped += 1
            continue

        category = _resolve_category(
            row.get("Category_ID") or row.get("Category_Id") or "other"
        )

        # Build storage entries for each location
        storage: dict[str, dict[str, int | None]] = {}

        # --- Pantry (unopened) ---
        pantry_min = _normalise_days(row.get("Pantry_Min"), row.get("Pantry_Metric"))
        pantry_max = _normalise_days(row.get("Pantry_Max"), row.get("Pantry_Metric"))
        if pantry_min is not None or pantry_max is not None:
            storage["pantry"] = {"min_days": pantry_min, "max_days": pantry_max}

        # --- Pantry (after opening) ---
        pao_min = _normalise_days(
            row.get("Pantry_After_Opening_Min"),
            row.get("Pantry_After_Opening_Metric"),
        )
        pao_max = _normalise_days(
            row.get("Pantry_After_Opening_Max"),
            row.get("Pantry_After_Opening_Metric"),
        )
        if pao_min is not None or pao_max is not None:
            storage["pantry_opened"] = {"min_days": pao_min, "max_days": pao_max}

        # --- Refrigerator (unopened) ---
        ref_min = _normalise_days(
            row.get("Refrigerate_Min"), row.get("Refrigerate_Metric")
        )
        ref_max = _normalise_days(
            row.get("Refrigerate_Max"), row.get("Refrigerate_Metric")
        )
        if ref_min is not None or ref_max is not None:
            storage["refrigerator"] = {"min_days": ref_min, "max_days": ref_max}

        # --- Refrigerator (after opening) ---
        rao_min = _normalise_days(
            row.get("Refrigerate_After_Opening_Min"),
            row.get("Refrigerate_After_Opening_Metric"),
        )
        rao_max = _normalise_days(
            row.get("Refrigerate_After_Opening_Max"),
            row.get("Refrigerate_After_Opening_Metric"),
        )
        if rao_min is not None or rao_max is not None:
            storage["refrigerator_opened"] = {
                "min_days": rao_min,
                "max_days": rao_max,
            }

        # --- Freezer ---
        frz_min = _normalise_days(row.get("Freeze_Min"), row.get("Freeze_Metric"))
        frz_max = _normalise_days(row.get("Freeze_Max"), row.get("Freeze_Metric"))
        if frz_min is not None or frz_max is not None:
            storage["freezer"] = {"min_days": frz_min, "max_days": frz_max}

        if not storage:
            skipped += 1
            continue

        subtitle = (row.get("Name_subtitle") or "").strip()

        entry: dict[str, Any] = {
            "name": name,
            "category": category,
            "storage": storage,
        }
        if subtitle:
            entry["subtitle"] = subtitle

        results.append(entry)

    logger.info("Processed %d items, skipped %d", len(results), skipped)
    return results


def write_json(data: list[dict[str, Any]], dest: Path) -> None:
    """Write *data* as pretty-printed JSON to *dest*."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "_meta": {
                    "source": "USDA FoodKeeper (data.gov)",
                    "url": "https://catalog.data.gov/dataset/foodkeeper-data",
                    "description": (
                        "Shelf-life data normalised to days for "
                        "pantry, refrigerator, and freezer storage."
                    ),
                    "item_count": len(data),
                },
                "items": data,
            },
            fh,
            indent=2,
            ensure_ascii=False,
        )
    logger.info("Wrote %d items to %s", len(data), dest)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def build(csv_path: str | Path | None = None) -> Path:
    """Run the full pipeline and return the path to the output JSON.

    Parameters
    ----------
    csv_path:
        Path to a local FoodKeeper CSV.  If ``None`` the script will attempt
        to download the CSV from data.gov.
    """
    if csv_path is not None:
        csv_file = Path(csv_path)
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV not found: {csv_file}")
    else:
        csv_file = OUTPUT_DIR / "foodkeeper_products.csv"
        if not csv_file.exists():
            try:
                _download_csv(FOODKEEPER_CSV_URL, csv_file)
            except RuntimeError:
                logger.warning(
                    "Primary URL failed – trying fallback …"
                )
                _download_csv(FALLBACK_CSV_URL, csv_file)

    rows = load_csv(csv_file)
    items = process_rows(rows)

    if not items:
        logger.error("No items produced – aborting.")
        sys.exit(1)

    write_json(items, OUTPUT_FILE)
    return OUTPUT_FILE


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Build expiry_kb.json from USDA FoodKeeper CSV."
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Path to a local FoodKeeper products CSV (optional).",
    )
    args = parser.parse_args()

    out = build(csv_path=args.csv)
    print(f"✅  Output written to {out}")
