from pymongo.asynchronous.database import AsyncDatabase

class LogRepository:
    def __init__(self, db: AsyncDatabase):
        self.collection = db.get_collection("RequestLogs")

    async def create_log(self, data: dict):
        await self.collection.insert_one(data)