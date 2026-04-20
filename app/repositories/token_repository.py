from pymongo.asynchronous.database import AsyncDatabase

from datetime import datetime, timezone

from datetime import datetime, timedelta, timezone

class TokenRepository:
    def __init__(self, db: AsyncDatabase):
        self.collection = db.get_collection("refresh_token")

    async def create_token(self, user_id: str, token_str: str, days_valid: int):
        
        await self.collection.insert_one({
            "user_id": user_id,
            "refresh_token": token_str,
            "revoked": False,
            "expire_at": datetime.now(timezone.utc) + timedelta(days=days_valid),
            "created_at": datetime.now(timezone.utc)
        })

    async def find_and_revoke(self, token_str: str):
        
        return await self.collection.find_one_and_update(
            {"refresh_token": token_str, "revoked": False}, 
            {"$set": {"revoked": True}},
            return_document=True 
        )



