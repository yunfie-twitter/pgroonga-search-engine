from fastapi import FastAPI
from src.routers import search
from src.config.settings import settings

# Initialize FastAPI application
# Title and version are useful for automatic API documentation (Swagger UI)
app = FastAPI(
    title="PGroonga Search Engine",
    description="Production-ready search engine using PGroonga and Redis",
    version="1.0.0"
)

# Include the search router
# Segregating routes into routers keeps the main application file clean
app.include_router(search.router)

@app.get("/health")
def health_check():
    """
    Simple health check endpoint for monitoring tools (like Docker healthcheck).
    """
    return {"status": "ok"}

if __name__ == "__main__":
    # For local debugging purposes
    import uvicorn
    uvicorn.run(app, host=settings.UVICORN_HOST, port=settings.UVICORN_PORT)
