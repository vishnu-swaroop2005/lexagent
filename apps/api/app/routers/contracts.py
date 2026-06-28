from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from typing import Optional

from app.deps import get_current_user, require_role, CurrentUser
from app.models.schemas import (
    ContractUploadResponse,
    ContractResponse,
    ClauseResponse,
    RedlineResponse,
    PaginatedResponse,
    ContractStatus,
)
from app.services.parser import ParserService
from app.services.redline import RedlineEngine
from app.utils.supabase_client import get_supabase_client

router = APIRouter()


@router.post("/upload", response_model=ContractUploadResponse)
async def upload_contract(
    file: UploadFile = File(...),
    title: str = Form(...),
    counterparty: Optional[str] = Form(None),
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Upload a PDF or DOCX contract for AI processing.

    Stores the file in Supabase Storage, creates a contract record,
    and queues an async parsing task via Celery.
    """
    if file.content_type not in [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    file_type = "pdf" if "pdf" in file.content_type else "docx"
    contents = await file.read()

    parser = ParserService()
    result = await parser.upload_and_queue(
        file_bytes=contents,
        filename=file.filename,
        file_type=file_type,
        title=title,
        counterparty=counterparty,
        org_id=user.org_id,
        user_id=user.user_id,
    )

    return ContractUploadResponse(**result)


@router.get("/", response_model=PaginatedResponse)
async def list_contracts(
    status: Optional[ContractStatus] = None,
    page: int = 1,
    per_page: int = 20,
    user: CurrentUser = Depends(get_current_user),
):
    """List all contracts for the current organization."""
    supabase = get_supabase_client()
    query = supabase.table("contracts").select("*", count="exact").eq("org_id", user.org_id)

    if status:
        query = query.eq("status", status.value)

    query = query.order("created_at", desc=True)
    query = query.range((page - 1) * per_page, page * per_page - 1)

    result = query.execute()
    return PaginatedResponse(
        items=result.data,
        total=result.count or 0,
        page=page,
        per_page=per_page,
    )


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get contract details including extracted clauses."""
    supabase = get_supabase_client()

    contract = (
        supabase.table("contracts")
        .select("*")
        .eq("id", contract_id)
        .eq("org_id", user.org_id)
        .single()
        .execute()
    )
    if not contract.data:
        raise HTTPException(status_code=404, detail="Contract not found")

    clauses = (
        supabase.table("clauses")
        .select("*")
        .eq("contract_id", contract_id)
        .eq("org_id", user.org_id)
        .order("position_start")
        .execute()
    )

    return ContractResponse(**contract.data, clauses=clauses.data or [])


@router.post("/{contract_id}/parse")
async def reparse_contract(
    contract_id: str,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Re-trigger parsing for a contract."""
    from app.tasks.contract_tasks import parse_contract_task

    task = parse_contract_task.delay(contract_id, user.org_id)
    return {"task_id": task.id, "status": "parsing"}


@router.post("/{contract_id}/redline")
async def generate_redline(
    contract_id: str,
    review_report_id: str,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Generate a redlined DOCX from a review report."""
    engine = RedlineEngine()
    result = await engine.generate_redline(contract_id, review_report_id, user.org_id)
    return result


@router.post("/{contract_id}/redline/{redline_id}/apply")
async def apply_redline_changes(
    contract_id: str,
    redline_id: str,
    change_ids: list[str],
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Accept specific redline changes and generate a clean document."""
    engine = RedlineEngine()
    result = await engine.apply_changes(redline_id, change_ids, user.org_id)
    return result


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: str,
    user: CurrentUser = Depends(require_role("admin")),
):
    """Delete a contract and all related data."""
    supabase = get_supabase_client()
    supabase.table("contracts").delete().eq("id", contract_id).eq("org_id", user.org_id).execute()
    return {"success": True}
