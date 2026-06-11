"""
MongoDB Atlas async service using Motor.

Provides connection management, CRUD helpers, and collection references
for all 10 PantryMind collections.
"""

import os
import logging
from typing import Any

import certifi

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import TEXT, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure

logger = logging.getLogger("pantrymind.db")

_global_db_service = None

def get_db_service():
    global _global_db_service
    if not _global_db_service:
        _global_db_service = MongoDBService()
    return _global_db_service

async def get_db():
    svc = get_db_service()
    return svc.db

class MongoDBService:
    """Async MongoDB Atlas client wrapper."""

    # All collection names used by the system
    COLLECTIONS = [
        "inventory",
        "receipts",
        "consumption_history",
        "financial_ledger",
        "warranties",
        "user_profile",
        "behavior_snapshots",
        "carbon_log",
        "nutrition_log",
        "restock_predictions",
        "conversation_history",
        "medical_conditions",
    ]

    def __init__(self):
        self._client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None

    @property
    def db(self) -> AsyncIOMotorDatabase:
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------
    async def connect(self) -> None:
        """Connect to MongoDB Atlas."""
        uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("MONGODB_DATABASE", "finmind")

        if not uri:
            raise ValueError("MONGODB_URI environment variable not set.")

        self._client = AsyncIOMotorClient(
            uri,
            maxPoolSize=20,
            minPoolSize=2,
            serverSelectionTimeoutMS=8000,
            connectTimeoutMS=8000,
            socketTimeoutMS=15000,
            retryWrites=True,
            tlsCAFile=certifi.where(),
        )
        self._db = self._client[db_name]
        logger.info(f"Connected to MongoDB database: {db_name}")

    async def close(self) -> None:
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed.")

    async def ping(self) -> bool:
        """Verify database connectivity."""
        try:
            await self._client.admin.command("ping")
            return True
        except ConnectionFailure as e:
            logger.error(f"MongoDB ping failed: {e}")
            raise

    # ------------------------------------------------------------------
    # Collection accessors
    # ------------------------------------------------------------------
    def collection(self, name: str):
        """Get a collection reference."""
        return self.db[name]

    @property
    def inventory(self):
        return self.db["inventory"]

    @property
    def receipts(self):
        return self.db["receipts"]

    @property
    def consumption_history(self):
        return self.db["consumption_history"]

    @property
    def financial_ledger(self):
        return self.db["financial_ledger"]

    @property
    def warranties(self):
        return self.db["warranties"]

    @property
    def user_profile(self):
        return self.db["user_profile"]

    @property
    def behavior_snapshots(self):
        return self.db["behavior_snapshots"]

    @property
    def carbon_log(self):
        return self.db["carbon_log"]

    @property
    def nutrition_log(self):
        return self.db["nutrition_log"]

    @property
    def restock_predictions(self):
        return self.db["restock_predictions"]

    @property
    def conversation_history(self):
        return self.db["conversation_history"]

    @property
    def medical_conditions(self):
        return self.db["medical_conditions"]

    # ------------------------------------------------------------------
    # Generic CRUD helpers (used by REST endpoints as fallback)
    # ------------------------------------------------------------------
    async def find(
        self,
        collection_name: str,
        query: dict | None = None,
        projection: dict | None = None,
        limit: int = 100,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[dict]:
        """Find documents in a collection."""
        cursor = self.db[collection_name].find(
            query or {},
            projection=projection,
        )
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.limit(limit)

        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])  # Serialize ObjectId
            results.append(doc)
        return results

    async def insert_one(self, collection_name: str, document: dict) -> str:
        """Insert a single document. Returns the inserted ID."""
        result = await self.db[collection_name].insert_one(document)
        return str(result.inserted_id)

    async def insert_many(self, collection_name: str, documents: list[dict]) -> list[str]:
        """Insert multiple documents. Returns list of inserted IDs."""
        result = await self.db[collection_name].insert_many(documents, ordered=False)
        return [str(id_) for id_ in result.inserted_ids]

    async def update_one(
        self,
        collection_name: str,
        query: dict,
        update: dict,
        upsert: bool = False,
    ) -> int:
        """Update a single document. Returns modified count."""
        result = await self.db[collection_name].update_one(
            query, update, upsert=upsert
        )
        return result.modified_count

    async def delete_one(self, collection_name: str, query: dict) -> int:
        """Delete a single document. Returns deleted count."""
        result = await self.db[collection_name].delete_one(query)
        return result.deleted_count

    async def delete_many(self, collection_name: str, query: dict) -> int:
        """Delete multiple documents. Returns deleted count."""
        result = await self.db[collection_name].delete_many(query)
        return result.deleted_count

    async def find_one(
        self, collection_name: str, query: dict
    ) -> dict | None:
        """Find a single document."""
        doc = await self.db[collection_name].find_one(query)
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def count_documents(self, collection_name: str, query: dict | None = None) -> int:
        """Count documents in a collection matching a query."""
        return await self.db[collection_name].count_documents(query or {})

    async def aggregate(
        self,
        collection_name: str,
        pipeline: list[dict],
    ) -> list[dict]:
        """Run an aggregation pipeline."""
        results = []
        async for doc in self.db[collection_name].aggregate(pipeline):
            if "_id" in doc and hasattr(doc["_id"], "__str__"):
                doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results


    # ------------------------------------------------------------------
    # Index setup (called by scripts/setup_mongodb.py)
    # ------------------------------------------------------------------
    async def setup_indexes(self) -> None:
        """Create all required indexes for PantryMind collections."""
        logger.info("Setting up MongoDB indexes...")

        # Inventory: text search on item_name and normalized_name
        await self.inventory.create_index(
            [("item_name", TEXT), ("normalized_name", TEXT)],
            name="inventory_item_text",
        )
        await self.inventory.create_index(
            [("category", ASCENDING), ("purchase_date", DESCENDING)],
            name="inventory_category_date",
        )
        await self.inventory.create_index(
            [("status", ASCENDING)],
            name="inventory_status",
        )
        await self.inventory.create_index(
            [("dietary_flag", ASCENDING)],
            name="inventory_dietary_flag",
        )
        await self.inventory.create_index(
            [("safe_expiry_date", ASCENDING)],
            name="inventory_safe_expiry",
        )
        await self.inventory.create_index(
            [("is_consumed", ASCENDING), ("category", ASCENDING), ("safe_expiry_date", ASCENDING)],
            name="inventory_active_category_expiry",
        )

        # Receipts: date index for range queries
        await self.receipts.create_index(
            [("receipt_date", DESCENDING)],
            name="receipts_date",
        )

        # Consumption history: compound for monthly queries
        await self.consumption_history.create_index(
            [("month_key", ASCENDING), ("item_name", ASCENDING)],
            name="consumption_month_item",
        )

        # Financial ledger: date for time-series queries
        await self.financial_ledger.create_index(
            [("date", DESCENDING)],
            name="ledger_date",
        )

        # Warranties: expiry date for alert queries
        await self.warranties.create_index(
            [("expiry_date", ASCENDING)],
            name="warranty_expiry",
        )

        # User profile: unique user_id
        await self.user_profile.create_index(
            [("user_id", ASCENDING)],
            name="user_id_unique",
            unique=True,
        )

        # Behavior snapshots: week key
        await self.behavior_snapshots.create_index(
            [("week_key", DESCENDING)],
            name="behavior_week",
        )

        # Carbon log: date for aggregation
        await self.carbon_log.create_index(
            [("date", DESCENDING)],
            name="carbon_date",
        )

        # Nutrition log: date for weekly reports
        await self.nutrition_log.create_index(
            [("date", DESCENDING)],
            name="nutrition_date",
        )

        # Restock predictions: predicted empty date for alerts
        await self.restock_predictions.create_index(
            [("predicted_empty_date", ASCENDING)],
            name="restock_depletion",
        )

        # Medical conditions: user + condition name unique
        await self.medical_conditions.create_index(
            [("user_id", ASCENDING), ("condition_name", ASCENDING)],
            name="medical_user_condition",
            unique=True,
        )

        logger.info("All indexes created successfully.")

    async def setup_chat_indexes(self) -> None:
        """Create indexes for conversation history."""
        await self.conversation_history.create_index(
            [("session_id", ASCENDING), ("timestamp", ASCENDING)],
            name="chat_session_timeline",
        )
        logger.info("Chat indexes created.")
