# src/routers/search.py
# Responsibility: Handles search API endpoints. Validates input and formats output.

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
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
    img_url: Optional[str] = None

class SearchResponse(BaseModel):
    query: str
    search_id: str
    count: int
    results: List[SearchResultItem]
    keywords: List[str] = []

class ClickRequest(BaseModel):
    search_id: str
    url: str
    rank: int

# --- Endpoints ---
@router.post("/click", tags=["Feedback"])
def log_click_endpoint(
    req: ClickRequest,
    service: SearchService = Depends(get_search_service)
):
    """
    Log user click events for search quality optimization.
    """
    success = service.log_click(req.search_id, req.url, req.rank)
    if not success:
        # We don't want to break the user experience if logging fails,
        # but returning 500 might be appropriate for monitoring.
        # For now, just return false status.
        return {"status": "error"}
    return {"status": "ok"}

@router.get("", response_model=SearchResponse)
def search_endpoint(
    q: str = Query(..., min_length=1, description="Search query string"),
    category: Optional[str] = Query(None, description="Category filter"),
    domain: Optional[str] = Query(None, description="Domain filter (e.g. 'example.com')"),
    include_images: bool = Query(False, description="Include representative image URL"),
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
    if domain:
        filters["domain"] = domain
    if include_images:
        filters["include_images"] = True
    if date_from:
        filters["from"] = date_from.isoformat()
    if date_to:
        filters["to"] = date_to.isoformat()

    # 2. Service Execution
    try:
        service_response = service.execute_search(q, filters, limit)
        results = service_response["results"]
        keywords = service_response.get("keywords", [])
        search_id = service_response.get("search_id", "")
    except Exception as e:
        # Catch unexpected errors to prevent 500 crashes propagating raw errors
        # In a real app, we'd log this properly.
        print(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during search")

    # 3. Response Construction
    # Explicitly convert dicts to Pydantic models to satisfy type checkers
    # and ensure strict schema compliance.
    typed_results = [SearchResultItem(**item) for item in results]

    return SearchResponse(
        query=q,
        search_id=search_id,
        count=len(typed_results),
        results=typed_results,
        keywords=keywords
    )
