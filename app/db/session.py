import asyncio
from pymongo import AsyncMongoClient
from app.core.config import settings
class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self._loop_id = None  # Track which loop owns this client

    async def connect_to_mongo(self):
        current_loop = asyncio.get_running_loop()
        
        # If loop changed or client is missing, recreate it
        if self.client is None or self._loop_id != id(current_loop):
            # Important: Don't await old client.close() if the loop is already dead
            self.client = AsyncMongoClient(
                settings.mongo_url,
                maxPoolSize=100 
            )
            self.db = self.client["scraping-and-aggregratioin"]
            self._loop_id = id(current_loop)
            print(f"Connected to MongoDB on loop {self._loop_id}")

    async def close_mongo_connection(self):
        if self.client:
            # We don't await here because if the loop is closed, 
            # awaiting will throw the same RuntimeError.
            self.client.close()  # type: ignore
            self.client = None
            self.db = None
            self._loop_id = None

db_manager = DatabaseManager()

async def get_db():
    # Force a loop-check every time we get the DB
    await db_manager.connect_to_mongo()
    return db_manager.db
