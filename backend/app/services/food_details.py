"""Dish details stored in MongoDB (collection: food_details).

Read, update and delete for the flexible extra info about each dish:
dietary type, allergens, spice level, tags, calories, today's special,
plus any extra fields (served hot/cold, sugar_free, ...).

A document's _id is the dish's food_items.id in MariaDB, so the two
databases are linked by that id.
"""

from datetime import datetime, timezone

from fastapi import HTTPException
from pymongo import ReturnDocument

from ..mongo import food_details as collection

# fields the app manages; anything else is shown as "extra"
CORE_FIELDS = {"_id", "dietary", "spice_level", "allergens", "tags",
               "calories", "special", "updated_at"}


def _out(doc):
    """Mongo document -> JSON-friendly dict."""
    if doc is None:
        return None
    doc = dict(doc)
    doc["food_item_id"] = doc.pop("_id")
    doc["extra"] = {k: doc.pop(k) for k in list(doc) if k not in CORE_FIELDS | {"food_item_id"}}
    return doc


def _food_name(conn, food_id):
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM food_items WHERE id = %s", (food_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "Food item not found")
    return row["name"]


# ---------------------------------------------------------------- read

def list_details(dietary=None, exclude_allergen=None, max_spice=None, tag=None):
    """Find documents matching optional filters (each one uses an index)."""
    query = {}
    if dietary == "veg":
        query["dietary"] = {"$in": ["veg", "vegan"]}  # vegan dishes are veg too
    elif dietary:
        query["dietary"] = dietary
    if exclude_allergen:
        query["allergens"] = {"$nin": [exclude_allergen]}
    if max_spice is not None:
        query["spice_level"] = {"$lte": max_spice}
    if tag:
        query["tags"] = tag
    return [_out(d) for d in collection().find(query).sort("_id", 1)]


def get_details(food_id):
    doc = collection().find_one({"_id": food_id})
    if doc is None:
        raise HTTPException(404, "No details saved for this dish yet")
    return _out(doc)


def summary():
    """Aggregation pipelines: counts per dietary type and per allergen."""
    col = collection()
    by_dietary = list(col.aggregate([
        {"$group": {"_id": "$dietary", "dishes": {"$sum": 1}}},
        {"$sort": {"dishes": -1}},
    ]))
    by_allergen = list(col.aggregate([
        {"$unwind": "$allergens"},
        {"$group": {"_id": "$allergens", "dishes": {"$sum": 1}}},
        {"$sort": {"dishes": -1}},
    ]))
    specials = col.count_documents({"special": {"$ne": None, "$exists": True}})
    return {
        "by_dietary": [{"dietary": d["_id"], "dishes": d["dishes"]} for d in by_dietary],
        "by_allergen": [{"allergen": d["_id"], "dishes": d["dishes"]} for d in by_allergen],
        "specials": specials,
        "total": col.count_documents({}),
    }


# ---------------------------------------------------------------- update

def save_details(conn, food_id, data):
    """Create or fully replace a dish's document (upsert)."""
    _food_name(conn, food_id)  # dish must exist in MariaDB
    doc = {
        "dietary": data["dietary"],
        "spice_level": data["spice_level"],
        "allergens": sorted({a.strip().lower() for a in data["allergens"] if a.strip()}),
        "tags": sorted({t.strip().lower() for t in data["tags"] if t.strip()}),
        "calories": data.get("calories"),
        "special": {"note": data["special_note"]} if data.get("special_note") else None,
        "updated_at": datetime.now(timezone.utc),
    }
    # keep extra fields (served, sugar_free, ...) that the form doesn't edit
    doc.update(data.get("extra") or {})
    saved = collection().find_one_and_update(
        {"_id": food_id},
        {"$set": doc},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return _out(saved)


def set_special(food_id, note):
    """Partial update: only the 'special' field ($set or $unset)."""
    update = ({"$set": {"special": {"note": note}, "updated_at": datetime.now(timezone.utc)}}
              if note else
              {"$unset": {"special": ""}, "$set": {"updated_at": datetime.now(timezone.utc)}})
    doc = collection().find_one_and_update(
        {"_id": food_id}, update, return_document=ReturnDocument.AFTER
    )
    if doc is None:
        raise HTTPException(404, "No details saved for this dish yet")
    return _out(doc)


def change_tag(food_id, tag, add=True):
    """Array update: $addToSet adds a tag once, $pull removes it."""
    tag = tag.strip().lower()
    op = "$addToSet" if add else "$pull"
    doc = collection().find_one_and_update(
        {"_id": food_id},
        {op: {"tags": tag}, "$set": {"updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        raise HTTPException(404, "No details saved for this dish yet")
    return _out(doc)


# ---------------------------------------------------------------- delete

def delete_details(food_id):
    result = collection().delete_one({"_id": food_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "No details saved for this dish yet")
    return {"food_item_id": food_id, "deleted": True}


def delete_details_if_any(food_id):
    """Used when a dish is deleted from MariaDB; ignores missing docs."""
    collection().delete_one({"_id": food_id})
