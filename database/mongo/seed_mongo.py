"""Fill MongoDB menu_details from the dishes in MariaDB. Owner: Mann.

Reads every row of menu_items and inserts one document per dish.
Known dishes get hand-written details; any other dish gets sensible
defaults based on its category, so this works with any seed data.

Run with database/mongo/setup.sh, or:
    venv/bin/python database/mongo/seed_mongo.py
"""

import os
import sys
from datetime import datetime, timezone

import pymysql
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

# name (lower case) -> details. Fields beyond the core ones show the
# flexible schema: each dish only has the fields that make sense for it.
KNOWN = {
    "samosa":            dict(dietary="veg", spice_level=2, allergens=["gluten"], tags=["bestseller", "fried"], calories=260),
    "veg puff":          dict(dietary="veg", spice_level=1, allergens=["gluten", "dairy"], tags=["baked"], calories=280),
    "aloo tikki":        dict(dietary="vegan", spice_level=2, allergens=[], tags=["fried", "street food"], calories=220),
    "vada pav":          dict(dietary="vegan", spice_level=2, allergens=["gluten"], tags=["street food", "bestseller"], calories=290),
    "veg thali":         dict(dietary="veg", spice_level=1, allergens=["gluten", "dairy"], tags=["filling", "bestseller"],
                              calories=650, portion="full plate", includes=["rice", "dal", "sabzi", "2 roti", "salad"]),
    "rajma chawal":      dict(dietary="vegan", spice_level=2, allergens=[], tags=["protein rich", "filling"],
                              calories=540, portion="full plate"),
    "paneer biryani":    dict(dietary="veg", spice_level=3, allergens=["dairy"], tags=["chef special"], calories=720,
                              portion="full plate", special={"note": "Extra raita free today"}),
    "dal khichdi":       dict(dietary="vegan", spice_level=0, allergens=[], tags=["light", "comfort food"], calories=430),
    "masala dosa":       dict(dietary="vegan", spice_level=1, allergens=[], tags=["south indian"], calories=390,
                              served_with=["sambar", "coconut chutney"]),
    "paneer wrap":       dict(dietary="veg", spice_level=2, allergens=["gluten", "dairy"], tags=["bestseller", "protein rich"], calories=480),
    "veg frankie":       dict(dietary="veg", spice_level=2, allergens=["gluten"], tags=["street food"], calories=390),
    "grilled sandwich":  dict(dietary="veg", spice_level=1, allergens=["gluten", "dairy"], tags=["grilled"], calories=410, cheese="cheddar"),
    "egg roll":          dict(dietary="egg", spice_level=2, allergens=["gluten", "egg"], tags=["street food"], calories=420),
    "masala chai":       dict(dietary="veg", spice_level=0, allergens=["dairy"], tags=["hot drink"], calories=120, served="hot", cup_ml=150),
    "cold coffee":       dict(dietary="veg", spice_level=0, allergens=["dairy"], tags=["cold drink"], calories=210, served="cold", caffeine=True),
    "mango lassi":       dict(dietary="veg", spice_level=0, allergens=["dairy"], tags=["cold drink", "seasonal"], calories=240,
                              served="cold", special={"note": "Made with Alphonso mangoes"}),
    "lemon soda":        dict(dietary="vegan", spice_level=0, allergens=[], tags=["cold drink"], calories=90, served="cold"),
    "gulab jamun":       dict(dietary="veg", spice_level=0, allergens=["dairy", "gluten"], tags=["sweet"], calories=300, sugar_free=False, pieces=2),
    "chocolate brownie": dict(dietary="egg", spice_level=0, allergens=["gluten", "dairy", "egg", "nuts"], tags=["sweet", "bestseller"],
                              calories=380, sugar_free=False),
}

# fallback by category for dishes not listed above
BY_CATEGORY = {
    "beverages": dict(tags=["drink"], served="hot"),
    "desserts":  dict(tags=["sweet"], allergens=["dairy"], sugar_free=False),
    "meals":     dict(tags=["filling"], spice_level=1, portion="full plate"),
    "snacks":    dict(tags=["snack"], spice_level=1),
}


def details_for(name, category):
    doc = {"dietary": "veg", "spice_level": 0, "allergens": [], "tags": [], "calories": None}
    doc.update(BY_CATEGORY.get((category or "").lower(), {}))
    doc.update(KNOWN.get(name.lower(), {}))
    return doc


def main():
    sql = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "campuseats"), password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "campuseats"), cursorclass=pymysql.cursors.DictCursor,
    )
    with sql.cursor() as cur:
        cur.execute("SELECT item_id, name, category FROM menu_items ORDER BY item_id")
        dishes = cur.fetchall()
    sql.close()

    mongo = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"),
                        serverSelectionTimeoutMS=3000)
    col = mongo[os.getenv("MONGO_DB", "campuseats")]["menu_details"]
    col.delete_many({})
    now = datetime.now(timezone.utc)
    docs = [{"_id": d["item_id"], **details_for(d["name"], d["category"]), "updated_at": now}
            for d in dishes]
    if docs:
        col.insert_many(docs)
    known = sum(1 for d in dishes if d["name"].lower() in KNOWN)
    print(f"menu_details: {len(docs)} documents ({known} hand-written, {len(docs) - known} from category defaults)")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # show a short, readable error
        sys.exit(f"Could not seed MongoDB: {exc}")
