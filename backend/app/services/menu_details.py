"""Dish details stored in MongoDB (collection: menu_details). Owner: Mann.

Read, update and delete the flexible extra info about each dish:
dietary type, allergens, spice level, tags, calories, today's special,
plus any extra fields (served hot/cold, sugar_free, portion, ...).

A document's _id is the dish's menu_items.item_id in MariaDB, so the two
databases are linked by that id.
"""

from datetime import datetime, timezone

from fastapi import HTTPException
from pymongo import ReturnDocument

from ..mongo import menu_details as collection

# fields the app manages; anything else is shown as "extra"
CORE_FIELDS = {"_id", "dietary", "spice_level", "allergens", "tags",
               "calories", "special", "updated_at"}


def _now():
    return datetime.now(timezone.utc)


def _out(doc):
    """Mongo document -> JSON-friendly dict."""
    if doc is None:
        return None
    doc = dict(doc)
    doc["item_id"] = doc.pop("_id")
    doc["extra"] = {k: doc.pop(k) for k in list(doc) if k not in CORE_FIELDS | {"item_id"}}
    return doc


def _check_menu_item(conn, item_id):
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM menu_items WHERE item_id = %s", (item_id,))
        if cur.fetchone() is None:
            raise HTTPException(404, "Menu item not found")


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


def get_details(item_id):
    doc = collection().find_one({"_id": item_id})
    if doc is None:
        raise HTTPException(404, "No details saved for this dish yet")
    return _out(doc)


def summary():
    """Aggregation pipelines: counts per dietary type and per allergen."""
    col = collection()
    by_dietary = col.aggregate([
        {"$group": {"_id": "$dietary", "dishes": {"$sum": 1}}},
        {"$sort": {"dishes": -1}},
    ])
    by_allergen = col.aggregate([
        {"$unwind": "$allergens"},
        {"$group": {"_id": "$allergens", "dishes": {"$sum": 1}}},
        {"$sort": {"dishes": -1}},
    ])
    return {
        "by_dietary": [{"dietary": d["_id"], "dishes": d["dishes"]} for d in by_dietary],
        "by_allergen": [{"allergen": d["_id"], "dishes": d["dishes"]} for d in by_allergen],
        "specials": col.count_documents({"special": {"$ne": None, "$exists": True}}),
        "total": col.count_documents({}),
    }


# ---------------------------------------------------------------- update

def save_details(conn, item_id, data):
    """Create or update a dish's document (upsert). Extra fields not in
    the form (served, sugar_free, ...) are kept."""
    _check_menu_item(conn, item_id)
    doc = {
        "dietary": data["dietary"],
        "spice_level": data["spice_level"],
        "allergens": sorted({a.strip().lower() for a in data["allergens"] if a.strip()}),
        "tags": sorted({t.strip().lower() for t in data["tags"] if t.strip()}),
        "calories": data.get("calories"),
        "special": {"note": data["special_note"]} if data.get("special_note") else None,
        "updated_at": _now(),
    }
    doc.update(data.get("extra") or {})
    saved = collection().find_one_and_update(
        {"_id": item_id}, {"$set": doc}, upsert=True, return_document=ReturnDocument.AFTER,
    )
    return _out(saved)


def set_special(item_id, note):
    """Partial update of one field: $set it, or $unset it to clear."""
    update = ({"$set": {"special": {"note": note}, "updated_at": _now()}} if note
              else {"$unset": {"special": ""}, "$set": {"updated_at": _now()}})
    doc = collection().find_one_and_update({"_id": item_id}, update,
                                           return_document=ReturnDocument.AFTER)
    if doc is None:
        raise HTTPException(404, "No details saved for this dish yet")
    return _out(doc)


def change_tag(item_id, tag, add=True):
    """Array update: $addToSet adds a tag only once, $pull removes it."""
    op = "$addToSet" if add else "$pull"
    doc = collection().find_one_and_update(
        {"_id": item_id},
        {op: {"tags": tag.strip().lower()}, "$set": {"updated_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        raise HTTPException(404, "No details saved for this dish yet")
    return _out(doc)


# ---------------------------------------------------------------- delete

def delete_details(item_id):
    if collection().delete_one({"_id": item_id}).deleted_count == 0:
        raise HTTPException(404, "No details saved for this dish yet")
    return {"item_id": item_id, "deleted": True}


def delete_details_if_any(item_id):
    """For when a dish is deleted from MariaDB; ignores missing documents."""
    collection().delete_one({"_id": item_id})
