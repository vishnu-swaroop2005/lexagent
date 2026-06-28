import uuid
import base64
from io import BytesIO
from datetime import datetime

from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as reportlab_canvas
from PIL import Image

from app.services.email_service import EmailService
from app.config import get_settings
from app.utils.supabase_client import get_supabase_client


class SignatureService:
    """Open-source digital signature service.

    Flow:
    1. User draws signature on HTML5 Canvas (frontend)
    2. Canvas exported as base64 PNG
    3. PNG stored in Supabase Storage
    4. When all parties sign, PNGs are embedded into the PDF via ReportLab/PyPDF2
    5. Email verification via unique UUID tokens

    No external services required (no DocuSign).
    """

    def __init__(self):
        self.supabase = get_supabase_client()
        self.email_service = EmailService()
        self.settings = get_settings()

    async def send_for_signature(self, document_id: str, org_id: str) -> int:
        """Send a document to all signing parties via email.

        1. Gets all parties with role='signer'
        2. Creates signature records with verification tokens
        3. Sends signing link emails
        4. Updates document status to 'sent'

        Args:
            document_id: Document UUID.
            org_id: Organization ID.

        Returns:
            Number of signing requests sent.
        """
        # Get document
        document = (
            self.supabase.table("documents")
            .select("title, file_path")
            .eq("id", document_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        ).data

        # Ensure PDF exists
        if not document.get("file_path"):
            raise ValueError("Generate PDF before sending for signature")

        # Get signing parties
        parties = (
            self.supabase.table("document_parties")
            .select("*")
            .eq("document_id", document_id)
            .eq("role", "signer")
            .order("signing_order")
            .execute()
        ).data

        if not parties:
            raise ValueError("No signing parties added")

        sent_count = 0
        for party in parties:
            # Create signature record
            token = str(uuid.uuid4())
            self.supabase.table("signatures").insert({
                "id": str(uuid.uuid4()),
                "org_id": org_id,
                "document_id": document_id,
                "party_id": party["id"],
                "status": "sent",
                "verification_token": token,
                "verification_email_sent": True,
            }).execute()

            # Build signing URL
            signing_url = f"{self.settings.frontend_url}/documents/{document_id}/sign?token={token}"

            # Send email
            await self.email_service.send_signing_request(
                to=party["email"],
                recipient_name=party["name"],
                document_title=document["title"],
                signing_url=signing_url,
                sender_name="LexAgent",
            )

            sent_count += 1

            # Create reminder for unsigned after 3 days
            self.supabase.table("reminders").insert({
                "id": str(uuid.uuid4()),
                "org_id": org_id,
                "reminder_type": "signature_pending",
                "reference_id": document_id,
                "reference_table": "signatures",
                "recipient_email": party["email"],
                "subject": f"Reminder: Please sign {document['title']}",
                "body": f"You have a pending signature request for {document['title']}.",
                "scheduled_at": (datetime.utcnow().replace(hour=9, minute=0) + __import__('datetime').timedelta(days=3)).isoformat(),
                "is_sent": False,
            }).execute()

        # Update document status
        self.supabase.table("documents").update(
            {"status": "sent"}
        ).eq("id", document_id).execute()

        return sent_count

    async def verify_token(self, token: str) -> dict | None:
        """Verify a signing token and return document info for the signing page.

        Args:
            token: The verification UUID token.

        Returns:
            Dict with document and party info, or None if invalid.
        """
        signature = (
            self.supabase.table("signatures")
            .select("*, document_parties(*), documents(*)")
            .eq("verification_token", token)
            .single()
            .execute()
        ).data

        if not signature:
            return None

        if signature.get("status") == "signed":
            return {"already_signed": True, "signed_at": signature.get("signed_at")}

        # Mark as viewed
        self.supabase.table("signatures").update(
            {"status": "viewed"}
        ).eq("verification_token", token).execute()

        doc = signature.get("documents", {})
        party = signature.get("document_parties", {})

        return {
            "document_title": doc.get("title", ""),
            "document_type": doc.get("doc_type", ""),
            "content_preview": (doc.get("generated_content", ""))[:2000],
            "party_name": party.get("name", ""),
            "party_email": party.get("email", ""),
        }

    async def capture_signature(self, token: str, signature_image_base64: str) -> bool:
        """Process a submitted signature.

        1. Decode base64 PNG
        2. Store in Supabase Storage
        3. Update signature record
        4. Check if all parties have signed
        5. If fully signed, generate final PDF with embedded signatures

        Args:
            token: Verification token.
            signature_image_base64: Base64-encoded PNG of the signature.

        Returns:
            True if successful.
        """
        signature = (
            self.supabase.table("signatures")
            .select("id, org_id, document_id, party_id")
            .eq("verification_token", token)
            .single()
            .execute()
        ).data

        if not signature:
            return False

        # Decode and store signature image
        image_bytes = base64.b64decode(signature_image_base64)
        sig_path = f"{signature['org_id']}/{signature['document_id']}/sig_{signature['party_id']}.png"

        self.supabase.storage.from_("signatures").upload(
            path=sig_path,
            file=image_bytes,
            file_options={"content-type": "image/png"},
        )

        # Update signature record
        self.supabase.table("signatures").update({
            "status": "signed",
            "signature_image_path": sig_path,
            "signed_at": datetime.utcnow().isoformat(),
        }).eq("id", signature["id"]).execute()

        # Check if all parties have signed
        all_sigs = (
            self.supabase.table("signatures")
            .select("status")
            .eq("document_id", signature["document_id"])
            .execute()
        ).data

        all_signed = all(s["status"] == "signed" for s in all_sigs)

        if all_signed:
            # Update document status
            self.supabase.table("documents").update(
                {"status": "fully_signed"}
            ).eq("id", signature["document_id"]).execute()

            # Trigger obligation extraction via Celery
            from app.tasks.document_tasks import post_signature_task
            post_signature_task.delay(signature["document_id"], signature["org_id"])

        return True

    async def embed_signatures_in_pdf(self, document_id: str, org_id: str) -> str:
        """Embed all signature images into the document PDF.

        Uses PyPDF2 to read the existing PDF and ReportLab to create
        an overlay with the signature images.

        Args:
            document_id: Document UUID.
            org_id: Organization ID.

        Returns:
            Storage path of the signed PDF.
        """
        document = (
            self.supabase.table("documents")
            .select("file_path, title")
            .eq("id", document_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        ).data

        # Download original PDF
        pdf_bytes = self.supabase.storage.from_("documents").download(document["file_path"])
        reader = PdfReader(BytesIO(pdf_bytes))

        # Get all signatures
        signatures = (
            self.supabase.table("signatures")
            .select("signature_image_path, document_parties(name)")
            .eq("document_id", document_id)
            .eq("status", "signed")
            .execute()
        ).data

        # Create overlay PDF with signatures
        overlay_buffer = BytesIO()
        c = reportlab_canvas.Canvas(overlay_buffer, pagesize=A4)

        y_position = 200  # Start position for signatures
        for sig in signatures:
            if sig.get("signature_image_path"):
                # Download signature image
                sig_bytes = self.supabase.storage.from_("signatures").download(sig["signature_image_path"])
                sig_img = Image.open(BytesIO(sig_bytes))

                # Resize to fit
                sig_img.thumbnail((200, 60))
                temp_path = BytesIO()
                sig_img.save(temp_path, format="PNG")
                temp_path.seek(0)

                # Draw on canvas
                from reportlab.lib.utils import ImageReader
                c.drawImage(ImageReader(temp_path), 72, y_position, width=150, height=40)

                party_name = sig.get("document_parties", {}).get("name", "")
                c.drawString(72, y_position - 15, party_name)
                c.drawString(72, y_position - 30, f"Signed: {datetime.utcnow().strftime('%Y-%m-%d')}")

                y_position -= 80

        c.save()

        # Merge overlay onto last page of original PDF
        overlay_buffer.seek(0)
        overlay_reader = PdfReader(overlay_buffer)

        writer = PdfWriter()
        for i, page in enumerate(reader.pages):
            if i == len(reader.pages) - 1 and overlay_reader.pages:
                page.merge_page(overlay_reader.pages[0])
            writer.add_page(page)

        # Save signed PDF
        output_buffer = BytesIO()
        writer.write(output_buffer)
        output_buffer.seek(0)

        signed_path = f"{org_id}/{document_id}/{document['title'].replace(' ', '_')}_signed.pdf"
        self.supabase.storage.from_("documents").upload(
            path=signed_path,
            file=output_buffer.getvalue(),
            file_options={"content-type": "application/pdf"},
        )

        return signed_path
