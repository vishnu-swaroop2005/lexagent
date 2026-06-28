from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_current_user, CurrentUser
from app.utils.supabase_client import get_supabase_client

router = APIRouter()


@router.get("/")
async def get_organization(user: CurrentUser = Depends(get_current_user)):
    """Return the current user's organisation details for the settings page.

    Shape matches the web app's `Organization` interface:
    { id, name, plan, members_count, created_at }.
    """
    supabase = get_supabase_client()

    org = (
        supabase.table("organisations")
        .select("id, name, plan, created_at")
        .eq("id", user.org_id)
        .single()
        .execute()
    )
    if not org.data:
        raise HTTPException(status_code=404, detail="Organization not found")

    members = (
        supabase.table("users")
        .select("id", count="exact")
        .eq("org_id", user.org_id)
        .execute()
    )

    return {
        "id": org.data["id"],
        "name": org.data.get("name"),
        "plan": org.data.get("plan", "free"),
        "members_count": members.count or 0,
        "created_at": org.data.get("created_at"),
    }
