from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

from app.schemas.scraper import JobRequest


class JobRepository:
    def __init__(self, db:AsyncDatabase) -> None:
        self.collection = db.get_collection("ScraperData")
        
    async def create_job(self,job_request:JobRequest):
        job_data = job_request.model_dump()
        
        job_data.update({
            "status":"pending",
            "progress":0,
            "created_at":datetime.now(),
            "updated_at": datetime.now()
        })
        result = await self.collection.insert_one(job_data)
        job_data["_id"] = result.inserted_id
        return job_data
    
    async def update(self, job_id:str, update_data: dict) -> bool:
        update_data["updated_at"] = datetime.now()
        
        result = await self.collection.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": update_data}
        )
        return result.matched_count>0
    
    async def get_by_id(self,job_id: str) -> Optional[dict]:
        return await self.collection.find_one({"_id":ObjectId(job_id)})
    
    async def save_results(self, job_id: str,  results: List[dict]) -> bool:
        return await self.update(job_id,{
            "status":"completed",
            "progress": 100,
            "results": results
        })
        