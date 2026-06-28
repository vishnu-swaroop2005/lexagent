from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_current_user, require_role, CurrentUser
from app.models.schemas import ComplianceCheckRequest, ComplianceReportResponse, ComplianceFramework
from app.services.compliance_checker import ComplianceChecker
from app.utils.supabase_client import get_supabase_client

router = APIRouter()


@router.post("/check/{contract_id}")
async def run_compliance_check(
    contract_id: str,
    request: ComplianceCheckRequest,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Run a compliance check (GDPR/SOC2) on a contract."""
    checker = ComplianceChecker()
    report = await checker.check_contract(contract_id, request.framework.value, user.org_id)
    return report


@router.get("/reports/{contract_id}")
async def get_compliance_reports(
    contract_id: str,
    framework: ComplianceFramework = None,
    user: CurrentUser = Depends(get_current_user),
):
    """Get compliance reports for a contract."""
    supabase = get_supabase_client()
    query = (
        supabase.table("compliance_reports")
        .select("*")
        .eq("contract_id", contract_id)
        .eq("org_id", user.org_id)
    )
    if framework:
        query = query.eq("framework", framework.value)

    result = query.order("checked_at", desc=True).execute()
    return {"reports": result.data or []}


@router.get("/report/{report_id}", response_model=ComplianceReportResponse)
async def get_report(
    report_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get a specific compliance report."""
    supabase = get_supabase_client()
    result = (
        supabase.table("compliance_reports")
        .select("*")
        .eq("id", report_id)
        .eq("org_id", user.org_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Report not found")
    return ComplianceReportResponse(**result.data)


@router.get("/dashboard")
async def compliance_dashboard(user: CurrentUser = Depends(get_current_user)):
    """Get organization-wide compliance statistics."""
    supabase = get_supabase_client()
    reports = (
        supabase.table("compliance_reports")
        .select("framework, overall_score")
        .eq("org_id", user.org_id)
        .execute()
    )

    stats: dict = {}
    for report in reports.data or []:
        fw = report["framework"]
        if fw not in stats:
            stats[fw] = {"total": 0, "avg_score": 0, "scores": []}
        stats[fw]["total"] += 1
        if report.get("overall_score") is not None:
            stats[fw]["scores"].append(report["overall_score"])

    for fw in stats:
        scores = stats[fw].pop("scores")
        stats[fw]["avg_score"] = sum(scores) / len(scores) if scores else 0

    return {"by_framework": stats}
