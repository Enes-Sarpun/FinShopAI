from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

class ProductSearch(BaseModel):
    query: str
    budget: Optional[float] = None
    category: Optional[str] = None
    limit: Optional[int] = 10

class ProductOut(BaseModel):
    id: UUID
    name: str
    category: str
    price: float
    description: Optional[str] = None
    image_url: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    seller: Optional[str] = None
    tags: Optional[List[str]] = None

class SearchResult(BaseModel):
    query: str
    total_found: int
    products: List[ProductOut] 