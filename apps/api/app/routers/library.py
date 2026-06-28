from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from app.deps import get_current_user, require_role, CurrentUser
from app.models.schemas import (
    ClauseLibraryCreate,
    ClauseLibraryResponse,
    SemanticSearchRequest,
    PaginatedResponse,
)
from app.services.clause_library import ClauseLibraryService
from app.utils.supabase_client import get_supabase_client

router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def list_library_clauses(
    clause_type: Optional[str] = None,
    approved: Optional[bool] = None,
    q: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    user: CurrentUser = Depends(get_current_user),
):
    """List clauses in the organization's clause library."""
    supabase = get_supabase_client()
    query = supabase.table("clause_library").select("*", count="exact").eq("org_id", user.org_id)

    if clause_type:
        query = query.eq("clause_type", clause_type)
    if approved is not None:
        query = query.eq("is_approved", approved)
    if q:
        query = query.ilike("content", f"%{q}%")

    query = query.order("usage_count", desc=True)
    query = query.range((page - 1) * per_page, page * per_page - 1)

    result = query.execute()
    return PaginatedResponse(items=result.data, total=result.count or 0, page=page, per_page=per_page)


@router.post("/", response_model=ClauseLibraryResponse)
async def add_clause(
    request: ClauseLibraryCreate,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Add a new clause to the organization's library."""
    service = ClauseLibraryService()
    clause = await service.add_clause(
        org_id=user.org_id,
        clause_type=request.clause_type,
        title=request.title,
        content=request.content,
        tags=request.tags,
    )
    return ClauseLibraryResponse(**clause)


@router.put("/{clause_id}", response_model=ClauseLibraryResponse)
async def update_clause(
    clause_id: str,
    request: ClauseLibraryCreate,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Update an existing library clause."""
    supabase = get_supabase_client()
    result = (
        supabase.table("clause_library")
        .update({
            "clause_type": request.clause_type,
            "title": request.title,
            "content": request.content,
            "tags": request.tags,
        })
        .eq("id", clause_id)
        .eq("org_id", user.org_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Clause not found")
    return ClauseLibraryResponse(**result.data[0])


@router.post("/{clause_id}/approve")
async def approve_clause(
    clause_id: str,
    user: CurrentUser = Depends(require_role("admin")),
):
    """Approve a clause in the library (admin only)."""
    service = ClauseLibraryService()
    await service.approve_clause(clause_id, user.user_id, user.org_id)
    return {"approved": True}


@router.post("/import")
async def import_from_contract(
    clause_id: str,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Import a clause from a contract into the library."""
    service = ClauseLibraryService()
    result = await service.import_from_contract(clause_id, user.org_id)
    return ClauseLibraryResponse(**result)


@router.post("/search")
async def search_library(
    request: SemanticSearchRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Semantic search across the clause library."""
    service = ClauseLibraryService()
    results = await service.search_library(
        org_id=user.org_id,
        query=request.query,
        threshold=request.threshold,
        limit=request.limit,
    )
    return {"results": results}
