from fastapi import FastAPI
from src.routers import search, admin
from src.config.settings import settings

# Initialize FastAPI application
app = FastAPI(
    title="PGroonga Search Engine",
    description="Production-ready search engine using PGroonga and Redis",
    version="1.1.0"
)

# Include routers
app.include_router(search.router)
app.include_router(admin.router)

@app.get("/health")
def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.UVICORN_HOST, port=settings.UVICORN_PORT)
