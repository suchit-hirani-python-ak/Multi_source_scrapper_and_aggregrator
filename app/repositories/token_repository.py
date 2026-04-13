from pymongo.asynchronous.database import AsyncDatabase

class TokenRepository:
    def __init__(self, db: AsyncDatabase):
        self.collection = db["refresh_tokens"]

    async def get_refresh_token(self, token_str: str):
        # Find by token string or a unique identifier (JTI) from the payload
        return await self.collection.find_one({"token": token_str})

    async def revoke_token(self, token_str: str):
        await self.collection.update_one(
            {"token": token_str}, 
            {"$set": {"revoked": True}}
        )
