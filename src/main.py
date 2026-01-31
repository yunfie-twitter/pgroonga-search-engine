# src/main.py
# Responsibility: Application entry point. Configures and launches the FastAPI app.

import uvicorn
from fastapi import FastAPI
from src.routers import search, admin
from src.config.settings import settings

def create_app() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.
    """
    app = FastAPI(
        title="PGroonga Search Engine",
        description="Scalable search engine using PGroonga, Redis, and RQ.",
        version="2.0.0",
        debug=settings.SERVER.DEBUG
    )

    # Register Routers
    app.include_router(search.router)
    app.include_router(admin.router)

    # Health Check
    @app.get("/health", tags=["System"])
    def health_check():
        return {"status": "ok", "version": "2.0.0"}

    return app

# Application instance
app = create_app()

if __name__ == "__main__":
    # Local development entry point
    uvicorn.run(
        "src.main:app", 
        host=settings.SERVER.HOST, 
        port=settings.SERVER.PORT, 
        reload=settings.SERVER.DEBUG
    )
