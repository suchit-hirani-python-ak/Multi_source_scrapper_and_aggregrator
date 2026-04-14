from app.core.config import settings
from pymongo.asynchronous.database import AsyncDatabase
from bson import ObjectId



class UserRepository:
    def __init__(self, db: AsyncDatabase):
        self.collection =  db.get_collection("users")

    async def create_user(self, user_data: dict) -> dict:
        result = await self.collection.insert_one(user_data)
        user_data["_id"] = str(result.inserted_id)
        return user_data

    async def find_by_email(self, email: str):
        return await self.collection.find_one({"email": email})

    async def find_by_id(self,user_id: str):
        return await self.collection.find_one({"_id":ObjectId(user_id)})
    
    
    async def remove_user(self,user_id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0