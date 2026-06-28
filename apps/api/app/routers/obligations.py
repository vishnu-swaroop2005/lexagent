from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from app.deps import get_current_user, require_role, CurrentUser
from app.models.schemas import ObligationResponse, ObligationStatus, RiskLevel, PaginatedResponse
from app.services.obligation_extractor import ObligationExtractor
from app.utils.supabase_client import get_supabase_client

router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def list_obligations(
    status: Optional[ObligationStatus] = None,
    priority: Optional[RiskLevel] = None,
    page: int = 1,
    per_page: int = 20,
    user: CurrentUser = Depends(get_current_user),
):
    """List all obligations for the organization."""
    supabase = get_supabase_client()
    query = supabase.table("obligations").select("*", count="exact").eq("org_id", user.org_id)

    if status:
        query = query.eq("status", status.value)
    if priority:
        query = query.eq("priority", priority.value)

    query = query.order("due_date")
    query = query.range((page - 1) * per_page, page * per_page - 1)

    result = query.execute()
    return PaginatedResponse(items=result.data, total=result.count or 0, page=page, per_page=per_page)


@router.post("/extract/{contract_id}")
async def extract_obligations(
    contract_id: str,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Extract obligations and deadlines from a contract using AI."""
    extractor = ObligationExtractor()
    obligations = await extractor.extract_from_contract(contract_id, user.org_id)
    return {"count": len(obligations), "obligations": obligations}


@router.put("/{obligation_id}", response_model=ObligationResponse)
async def update_obligation(
    obligation_id: str,
    status: Optional[ObligationStatus] = None,
    assigned_to: Optional[str] = None,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Update an obligation's status or assignment."""
    supabase = get_supabase_client()
    update_data = {}
    if status:
        update_data["status"] = status.value
    if assigned_to:
        update_data["assigned_to"] = assigned_to

    result = (
        supabase.table("obligations")
        .update(update_data)
        .eq("id", obligation_id)
        .eq("org_id", user.org_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Obligation not found")
    return ObligationResponse(**result.data[0])


@router.post("/{obligation_id}/complete")
async def complete_obligation(
    obligation_id: str,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Mark an obligation as completed."""
    supabase = get_supabase_client()
    from datetime import datetime

    result = (
        supabase.table("obligations")
        .update({"status": "completed", "completed_at": datetime.utcnow().isoformat()})
        .eq("id", obligation_id)
        .eq("org_id", user.org_id)
        .execute()
    )
    return {"completed_at": result.data[0]["completed_at"] if result.data else None}


@router.get("/overdue")
async def get_overdue(user: CurrentUser = Depends(get_current_user)):
    """Get all overdue obligations."""
    supabase = get_supabase_client()
    from datetime import date

    result = (
        supabase.table("obligations")
        .select("*")
        .eq("org_id", user.org_id)
        .eq("status", "overdue")
        .order("due_date")
        .execute()
    )
    return {"obligations": result.data or []}


@router.get("/calendar")
async def calendar_view(
    month: int,
    year: int,
    user: CurrentUser = Depends(get_current_user),
):
    """Get obligations organized by day for calendar view."""
    supabase = get_supabase_client()
    start = f"{year}-{month:02d}-01"
    end = f"{year}-{month:02d}-31"

    result = (
        supabase.table("obligations")
        .select("*")
        .eq("org_id", user.org_id)
        .gte("due_date", start)
        .lte("due_date", end)
        .order("due_date")
        .execute()
    )

    days: dict = {}
    for ob in result.data or []:
        d = ob.get("due_date", "unknown")
        days.setdefault(d, []).append(ob)

    return {"days": days}
