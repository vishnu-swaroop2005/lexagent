from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from app.deps import get_current_user, require_role, CurrentUser
from app.models.schemas import (
    DocumentQuestionnaireRequest,
    DocumentCreateRequest,
    DocumentUpdateRequest,
    DocumentResponse,
    PartyCreateRequest,
    PartyResponse,
    SignatureSubmitRequest,
    PaginatedResponse,
)
from app.services.document_generator import DocumentGenerator
from app.services.signature_service import SignatureService
from app.utils.supabase_client import get_supabase_client

router = APIRouter()


@router.get("/templates")
async def list_templates(
    doc_type: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
):
    """List available document templates."""
    supabase = get_supabase_client()
    query = supabase.table("document_templates").select("*")
    # Include system templates and org-specific templates
    query = query.or_(f"org_id.eq.{user.org_id},is_system.eq.true")

    if doc_type:
        query = query.eq("doc_type", doc_type)

    result = query.execute()
    return {"templates": result.data or []}


@router.post("/questionnaire")
async def generate_questionnaire(
    request: DocumentQuestionnaireRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Generate a dynamic questionnaire for a document type using AI."""
    generator = DocumentGenerator()
    schema = await generator.generate_questionnaire(request.doc_type, user.org_id)
    return {"schema": schema}


@router.post("/", response_model=DocumentResponse)
async def create_document(
    request: DocumentCreateRequest,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Create a new document and start AI drafting."""
    generator = DocumentGenerator()
    document = await generator.create_and_draft(
        doc_type=request.doc_type,
        title=request.title,
        answers=request.answers,
        template_id=request.template_id,
        org_id=user.org_id,
        user_id=user.user_id,
    )
    return DocumentResponse(**document)


@router.get("/", response_model=PaginatedResponse)
async def list_documents(
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    user: CurrentUser = Depends(get_current_user),
):
    """List all documents for the organization."""
    supabase = get_supabase_client()
    query = supabase.table("documents").select("*", count="exact").eq("org_id", user.org_id)

    if status:
        query = query.eq("status", status)

    query = query.order("created_at", desc=True)
    query = query.range((page - 1) * per_page, page * per_page - 1)

    result = query.execute()
    return PaginatedResponse(items=result.data, total=result.count or 0, page=page, per_page=per_page)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get document details with parties and signature status."""
    supabase = get_supabase_client()

    doc = (
        supabase.table("documents")
        .select("*")
        .eq("id", document_id)
        .eq("org_id", user.org_id)
        .single()
        .execute()
    )
    if not doc.data:
        raise HTTPException(status_code=404, detail="Document not found")

    parties = (
        supabase.table("document_parties")
        .select("*")
        .eq("document_id", document_id)
        .order("signing_order")
        .execute()
    )

    return DocumentResponse(**doc.data, parties=parties.data or [])


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    request: DocumentUpdateRequest,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Edit a draft document's content or title."""
    supabase = get_supabase_client()
    update_data = {}
    if request.content is not None:
        update_data["generated_content"] = request.content
    if request.title is not None:
        update_data["title"] = request.title

    result = (
        supabase.table("documents")
        .update(update_data)
        .eq("id", document_id)
        .eq("org_id", user.org_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(**result.data[0])


@router.post("/{document_id}/generate-pdf")
async def generate_pdf(
    document_id: str,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Generate a PDF from the document content."""
    generator = DocumentGenerator()
    file_url = await generator.generate_pdf(document_id, user.org_id)
    return {"file_url": file_url}


@router.post("/{document_id}/parties", response_model=PartyResponse)
async def add_party(
    document_id: str,
    request: PartyCreateRequest,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Add a signing party to a document."""
    supabase = get_supabase_client()
    result = (
        supabase.table("document_parties")
        .insert({
            "org_id": user.org_id,
            "document_id": document_id,
            "name": request.name,
            "email": request.email,
            "role": request.role,
            "signing_order": request.signing_order,
        })
        .execute()
    )
    return PartyResponse(**result.data[0])


@router.delete("/{document_id}/parties/{party_id}")
async def remove_party(
    document_id: str,
    party_id: str,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Remove a party from a document."""
    supabase = get_supabase_client()
    supabase.table("document_parties").delete().eq("id", party_id).eq("org_id", user.org_id).execute()
    return {"deleted": True}


@router.post("/{document_id}/send")
async def send_for_signature(
    document_id: str,
    user: CurrentUser = Depends(require_role("admin", "lawyer")),
):
    """Send the document to all parties for digital signature via email."""
    sig_service = SignatureService()
    count = await sig_service.send_for_signature(document_id, user.org_id)
    return {"sent_count": count}


# --- Public signing endpoints (no auth, token-based) ---

@router.get("/sign/{token}")
async def get_signing_page(token: str):
    """Public endpoint: get document info for the signing page."""
    sig_service = SignatureService()
    data = await sig_service.verify_token(token)
    if not data:
        raise HTTPException(status_code=404, detail="Invalid or expired signing link")
    return data


@router.post("/sign/{token}")
async def submit_signature(token: str, request: SignatureSubmitRequest):
    """Public endpoint: submit a digital signature."""
    sig_service = SignatureService()
    result = await sig_service.capture_signature(token, request.signature_image)
    if not result:
        raise HTTPException(status_code=400, detail="Signature submission failed")
    return {"signed": True}


@router.get("/{document_id}/versions")
async def get_versions(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Get version history for a document."""
    supabase = get_supabase_client()
    result = (
        supabase.table("document_versions")
        .select("*")
        .eq("document_id", document_id)
        .eq("org_id", user.org_id)
        .order("version_number", desc=True)
        .execute()
    )
    return {"versions": result.data or []}
