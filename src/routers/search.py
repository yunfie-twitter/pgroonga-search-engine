# src/routers/search.py
# Responsibility: Handles search API endpoints. Validates input and formats output.

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from datetime import date
from pydantic import BaseModel

from src.services.search_service import SearchService, get_search_service

router = APIRouter(
    prefix="/search",
    tags=["Search"]
)

# --- Pydantic Models ---
class SearchResultItem(BaseModel):
    url: str
    title: str
    snippet: str
    score: float

class SearchResponse(BaseModel):
    query: str
    count: int
    results: List[SearchResultItem]

# --- Endpoints ---
@router.get("", response_model=SearchResponse)
def search_endpoint(
    q: str = Query(..., min_length=1, description="Search query string"),
    category: Optional[str] = Query(None, description="Category filter"),
    date_from: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(20, ge=1, le=100, description="Max results (1-100)"),
    service: SearchService = Depends(get_search_service)
):
    """
    Search API endpoint.
    Receives query parameters, calls the service, and returns structured results.
    """
    # 1. Parameter Preparation
    # Convert API parameters into a dictionary format expected by the service.
    filters = {}
    if category:
        filters["category"] = category
    if date_from:
        filters["from"] = date_from.isoformat()
    if date_to:
        filters["to"] = date_to.isoformat()

    # 2. Service Execution
    try:
        results = service.execute_search(q, filters, limit)
    except Exception as e:
        # Catch unexpected errors to prevent 500 crashes propagating raw errors
        # In a real app, we'd log this properly.
        print(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during search")

    # 3. Response Construction
    return SearchResponse(
        query=q,
        count=len(results),
        results=results
    )
