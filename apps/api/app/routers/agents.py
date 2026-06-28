from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_current_user, require_role, CurrentUser
from app.models.schemas import (
    ReviewReportResponse,
    NegotiationStartRequest,
    NegotiationHistoryEntry,
)
from app.services.reviewer import ReviewerService
from app.services.negotiator import NegotiationAgent
from app.utils.supabase_client import get_supabase_client

router = APIRouter()


# --- Review Agent ---

@router.post("/review/{contract_id}")
async def start_review(
    contract_id: str,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Start an AI review of a contract. Runs asynchronously via Celery."""
    from app.tasks.contract_tasks import review_contract_task

    task = review_contract_task.delay(contract_id, user.org_id)
    return {"task_id": task.id, "status": "reviewing"}


@router.get("/review/{contract_id}/report", response_model=ReviewReportResponse)
async def get_review_report(
    contract_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get the latest AI review report for a contract."""
    supabase = get_supabase_client()
    result = (
        supabase.table("review_reports")
        .select("*")
        .eq("contract_id", contract_id)
        .eq("org_id", user.org_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="No review report found")

    report = result.data[0]
    return ReviewReportResponse(**report)


@router.post("/review/{contract_id}/report/{report_id}/accept")
async def accept_findings(
    contract_id: str,
    report_id: str,
    finding_ids: list[str],
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Accept specific review findings. Accepted clauses are added to the org library."""
    reviewer = ReviewerService()
    result = await reviewer.accept_findings(report_id, finding_ids, user.org_id)
    return {"updated": result}


# --- Negotiation Agent ---

@router.post("/negotiate/{contract_id}/start")
async def start_negotiation(
    contract_id: str,
    request: NegotiationStartRequest,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Start a negotiation thread for a contract."""
    agent = NegotiationAgent()
    negotiation_id = await agent.start_negotiation(
        contract_id=contract_id,
        counterparty_email=request.counterparty_email,
        counterparty_name=request.counterparty_name,
        org_id=user.org_id,
    )
    return {"negotiation_id": negotiation_id}


@router.get("/negotiate/{negotiation_id}/history")
async def get_negotiation_history(
    negotiation_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get the full negotiation timeline."""
    supabase = get_supabase_client()
    result = (
        supabase.table("negotiation_history")
        .select("*")
        .eq("negotiation_id", negotiation_id)
        .eq("org_id", user.org_id)
        .order("created_at")
        .execute()
    )
    return {"history": result.data or []}


@router.get("/negotiate/{negotiation_id}/suggest")
async def get_suggestion(
    negotiation_id: str,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Get AI-generated counter-offer suggestions."""
    agent = NegotiationAgent()
    suggestions = await agent.suggest_counter_offer(negotiation_id, user.org_id)
    return {"suggestions": suggestions}
