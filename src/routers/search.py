from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from datetime import date
from pydantic import BaseModel

from src.services.search_service import SearchService, get_search_service

router = APIRouter(
    prefix="/search",
    tags=["Search"]
)

class SearchResultItem(BaseModel):
    """
    Schema for individual search result items.
    """
    url: str
    title: str
    snippet: str
    score: float

class SearchResponse(BaseModel):
    """
    Schema for the search API response.
    """
    query: str
    count: int
    results: List[SearchResultItem]

@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, description="Search query"),
    category: Optional[str] = Query(None, description="Category filter"),
    date_from: Optional[date] = Query(None, description="Filter by published date from (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Filter by published date to (YYYY-MM-DD)"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
    service: SearchService = Depends(get_search_service)
):
    """
    Executes a search query against the web pages index.
    
    Flow:
    1. Receives request
    2. Calls SearchService (which handles normalization, expansion, cache, DB)
    3. Returns formatted response
    """
    
    # Construct filters dictionary
    filters = {}
    if category:
        filters["category"] = category
    if date_from:
        filters["from"] = date_from.isoformat()
    if date_to:
        filters["to"] = date_to.isoformat()

    # Delegate logic to the service layer
    results = service.search(q, filters, limit)

    return SearchResponse(
        query=q,
        count=len(results),
        results=results
    )
