
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError

router = APIRouter()

class ProfileQueryParams(BaseModel):
    """
    Strict validation model for Profile API query parameters to resolve Issue #547.
    Ensures that all query params are strictly typed and bounded to prevent injection or type errors.
    """
    limit: int = Field(10, ge=1, le=100, description="Number of profiles to return")
    offset: int = Field(0, ge=0, description="Pagination offset")
    sort_by: str | None = Field(None, pattern="^(created_at|updated_at|name)$", description="Field to sort by")
    tags: list[str] | None = Field(None, description="List of tags to filter by")
    active_only: bool = Field(True, description="Filter only active profiles")

@router.get("/profiles/validated")
async def get_validated_profiles(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str | None = Query(None, regex="^(created_at|updated_at|name)$"),
    tags: list[str] | None = Query(None, max_items=10),
    active_only: bool = Query(True)
):
    """
    Endpoint demonstrating the applied validation rules.
    """
    try:
        # Validate parameters via Pydantic explicit model as a secondary defense layer
        params = ProfileQueryParams(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            tags=tags,
            active_only=active_only
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    # Mock response
    return {
        "status": "success",
        "data": [],
        "meta": {
            "limit": params.limit,
            "offset": params.offset,
            "sort_by": params.sort_by,
            "active_only": params.active_only,
            "tags": params.tags
        }
    }
