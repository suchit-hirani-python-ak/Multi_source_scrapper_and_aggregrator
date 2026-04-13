from app.core.config import settings
from pymongo import AsyncMongoClient

class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None

    async def connect_to_mongo(self):
        """Initialize the single shared client."""
        # AsyncMongoClient handles connection pooling (default 100) automatically
        self.client = AsyncMongoClient(
            settings.mongo_url,
            # maxPoolSize to control concurrent connections
            maxPoolSize=100 
        )
        # Pre-select your database
        self.db = self.client["scraping-and-aggregratioin"]
        print("Connected to MongoDB")

    async def close_mongo_connection(self):
        """Close the client on app shutdown."""
        if self.client:
            await self.client.close()
            print("Closed MongoDB connection")
db_manager = DatabaseManager()

async def get_db():
    if db_manager.db is None:
        raise RuntimeError("Database not initialized")
    return db_manager.db