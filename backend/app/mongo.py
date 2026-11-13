"""MongoDB connection (NoSQL part).

One MongoClient is shared by the whole app (it keeps its own connection
pool). If MongoDB is not running, calls raise ServerSelectionTimeoutError
after 2 seconds, and main.py turns that into a clean 503 message.
"""

import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

_client = None


def get_mongo_db():
    global _client
    if _client is None:
        _client = MongoClient(
            os.getenv("MONGO_URI", "mongodb://localhost:27017"),
            serverSelectionTimeoutMS=2000,
            tz_aware=True,  # dates come back with a UTC timezone
        )
    return _client[os.getenv("MONGO_DB", "campuseats")]


def food_details():
    return get_mongo_db()["food_details"]
