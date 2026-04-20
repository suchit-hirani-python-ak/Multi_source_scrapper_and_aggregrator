import uvicorn
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from app.db.session import db_manager,get_db
from app.routes import  jobscrape_route, user_route
from app.exception.error import BaseException
from app.middleware.log_middleware import log_requests_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup: Connect to MongoDB
    await db_manager.connect_to_mongo()
    app.state.db = db_manager.db 
    yield
    
    # 3. Shutdown: Close connection
    await db_manager.close_mongo_connection()



# 2. Pass the lifespan to the FastAPI app
app = FastAPI(lifespan=lifespan)

app.middleware("http")(log_requests_middleware)

app.include_router(user_route.router,prefix="/auth",tags=["Authentication"])
app.include_router(jobscrape_route.router, prefix="/scrape", tags=["Scrape data"])

@app.get("/")
def server():
    return "server is running"

@app.exception_handler(BaseException)
async def global_app_exception_handler(request: Request, exc: BaseException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": exc.message,
            "path": request.url.path,
            "timestamp": datetime.now().isoformat(),
        },headers={"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    )

if __name__ == "__main__":
    uvicorn.run("main:app",port=8000,host="0.0.0.0",reload=True)