import asyncio
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3)
def post_signature_task(self, document_id: str, org_id: str):
    """Async task: Post-signature processing.

    When all parties have signed:
    1. Embed signatures into the PDF
    2. Extract obligations from the document
    3. Send signed copies to all parties
    """
    from app.services.signature_service import SignatureService
    from app.services.obligation_extractor import ObligationExtractor
    from app.services.email_service import EmailService
    from app.utils.supabase_client import get_supabase_client

    try:
        loop = asyncio.new_event_loop()

        sig_service = SignatureService()
        extractor = ObligationExtractor()
        email_service = EmailService()
        supabase = get_supabase_client()

        # Embed signatures in PDF
        signed_path = loop.run_until_complete(
            sig_service.embed_signatures_in_pdf(document_id, org_id)
        )

        # Extract obligations
        loop.run_until_complete(
            extractor.extract_from_document(document_id, org_id)
        )

        # Send signed copies to all parties
        parties = (
            supabase.table("document_parties")
            .select("email, name")
            .eq("document_id", document_id)
            .execute()
        ).data

        document = (
            supabase.table("documents")
            .select("title")
            .eq("id", document_id)
            .single()
            .execute()
        ).data

        # Download signed PDF
        pdf_bytes = supabase.storage.from_("documents").download(signed_path)

        for party in (parties or []):
            loop.run_until_complete(
                email_service.send_signed_copy(
                    to=party["email"],
                    document_title=document["title"],
                    pdf_bytes=pdf_bytes,
                )
            )

        loop.close()
        return {"status": "completed", "signed_pdf": signed_path}
    except Exception as exc:
        self.retry(exc=exc)


@celery_app.task
def check_pending_signatures():
    """Periodic task: Send reminders for pending signatures.

    Runs daily at 9 AM UTC. Checks for signatures that have been
    pending for more than 3 days and sends reminder emails.
    """
    from app.services.email_service import EmailService
    from app.utils.supabase_client import get_supabase_client
    from datetime import datetime, timedelta

    supabase = get_supabase_client()
    three_days_ago = (datetime.utcnow() - timedelta(days=3)).isoformat()

    pending = (
        supabase.table("signatures")
        .select("*, document_parties(name, email), documents(title)")
        .in_("status", ["sent", "viewed"])
        .lt("created_at", three_days_ago)
        .execute()
    ).data

    if not pending:
        return {"reminded": 0}

    email_service = EmailService()
    loop = asyncio.new_event_loop()
    count = 0

    for sig in pending:
        party = sig.get("document_parties", {})
        doc = sig.get("documents", {})

        if party.get("email"):
            try:
                loop.run_until_complete(
                    email_service.send_reminder(
                        to=party["email"],
                        subject=f"Reminder: Signature pending for {doc.get('title', 'document')}",
                        body=f"Hi {party.get('name', '')}, you have a pending signature request. Please review and sign at your earliest convenience.",
                    )
                )
                count += 1
            except Exception:
                pass

    loop.close()
    return {"reminded": count}
