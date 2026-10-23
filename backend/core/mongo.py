from pymongo import MongoClient

from core.config import settings

_client = None


def get_client():
    global _client
    if _client is None:
        if not settings.MONGO_URI:
            raise RuntimeError(
                "MONGO_URI is not set. Copy .env.example to .env and paste your "
                "MongoDB connection string before running the server."
            )
        _client = MongoClient(settings.MONGO_URI)
    return _client


def get_db():
    return get_client()[settings.MONGO_DB_NAME]
