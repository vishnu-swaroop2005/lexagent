import uuid
from datetime import datetime, timedelta

from app.services.gemini_client import GeminiClient
from app.utils.supabase_client import get_supabase_client


OBLIGATION_EXTRACTION_PROMPT = """You are a legal obligation analyst. Extract all obligations, deadlines,
and commitments from the following contract clauses.

For each obligation, identify:
- title: Short description of the obligation
- description: Full details
- obligated_party: Who is responsible ("us" or "counterparty")
- due_date: Specific date if mentioned (ISO format YYYY-MM-DD), or null
- recurring: Whether this is a recurring obligation (true/false)
- recurrence_rule: If recurring, the pattern (e.g., "monthly", "annually")
- priority: How critical this is ("low", "medium", "high", "critical")

Return a JSON array of obligations.

Contract clauses:
"""


class ObligationExtractor:
    """Extracts obligations, deadlines, and commitments from contracts.

    Post-signature, this service scans all clauses and uses AI to identify
    actionable obligations, then creates reminders for approaching deadlines.

    Integrates with the reminder system (Celery beat) for automated alerts.
    """

    def __init__(self):
        self.gemini = GeminiClient()
        self.supabase = get_supabase_client()

    async def extract_from_contract(self, contract_id: str, org_id: str) -> list[dict]:
        """Extract all obligations from a contract's clauses.

        1. Loads all clauses for the contract
        2. Sends to Gemini for obligation extraction
        3. Stores obligations in the database
        4. Schedules reminders for each obligation with a due date

        Args:
            contract_id: Contract UUID.
            org_id: Organization ID.

        Returns:
            List of created obligation records.
        """
        clauses = (
            self.supabase.table("clauses")
            .select("id, clause_type, content")
            .eq("contract_id", contract_id)
            .eq("org_id", org_id)
            .execute()
        ).data

        if not clauses:
            return []

        clauses_text = "\n\n".join(
            f"[{c['clause_type']}] {c['content']}" for c in clauses
        )

        obligations = await self.gemini.generate_json(
            OBLIGATION_EXTRACTION_PROMPT + clauses_text,
            system_instruction="You are a legal analyst. Return only valid JSON.",
        )

        if not isinstance(obligations, list):
            obligations = [obligations]

        records = []
        for ob in obligations:
            ob_id = str(uuid.uuid4())
            record = {
                "id": ob_id,
                "org_id": org_id,
                "contract_id": contract_id,
                "title": ob.get("title", "Untitled obligation"),
                "description": ob.get("description"),
                "obligated_party": ob.get("obligated_party", "us"),
                "due_date": ob.get("due_date"),
                "recurring": ob.get("recurring", False),
                "recurrence_rule": ob.get("recurrence_rule"),
                "status": "pending",
                "priority": ob.get("priority", "medium"),
            }
            records.append(record)

        if records:
            self.supabase.table("obligations").insert(records).execute()

        # Schedule reminders for obligations with due dates
        for record in records:
            if record.get("due_date"):
                await self.schedule_reminders(record["id"], record["due_date"], org_id)

        return records

    async def extract_from_document(self, document_id: str, org_id: str) -> list[dict]:
        """Extract obligations from a generated document (NDA/MOU etc).

        Args:
            document_id: Document UUID.
            org_id: Organization ID.

        Returns:
            List of created obligation records.
        """
        document = (
            self.supabase.table("documents")
            .select("generated_content, title")
            .eq("id", document_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        ).data

        if not document or not document.get("generated_content"):
            return []

        obligations = await self.gemini.generate_json(
            OBLIGATION_EXTRACTION_PROMPT + document["generated_content"],
            system_instruction="You are a legal analyst. Return only valid JSON.",
        )

        if not isinstance(obligations, list):
            obligations = [obligations]

        records = []
        for ob in obligations:
            ob_id = str(uuid.uuid4())
            record = {
                "id": ob_id,
                "org_id": org_id,
                "contract_id": None,  # Documents don't have contract_id
                "title": ob.get("title", "Untitled obligation"),
                "description": ob.get("description"),
                "obligated_party": ob.get("obligated_party", "us"),
                "due_date": ob.get("due_date"),
                "recurring": ob.get("recurring", False),
                "recurrence_rule": ob.get("recurrence_rule"),
                "status": "pending",
                "priority": ob.get("priority", "medium"),
                "metadata": {"document_id": document_id},
            }
            records.append(record)

        if records:
            self.supabase.table("obligations").insert(records).execute()

        for record in records:
            if record.get("due_date"):
                await self.schedule_reminders(record["id"], record["due_date"], org_id)

        return records

    async def schedule_reminders(self, obligation_id: str, due_date: str, org_id: str) -> None:
        """Create reminder records for 30d, 7d, and 1d before due date.

        Args:
            obligation_id: Obligation UUID.
            due_date: ISO date string.
            org_id: Organization ID.
        """
        due = datetime.fromisoformat(due_date)
        intervals = [
            (30, "30 days before deadline"),
            (7, "7 days before deadline"),
            (1, "1 day before deadline"),
        ]

        reminders = []
        for days, label in intervals:
            reminder_date = due - timedelta(days=days)
            if reminder_date > datetime.utcnow():
                reminders.append({
                    "id": str(uuid.uuid4()),
                    "org_id": org_id,
                    "reminder_type": "obligation_due",
                    "reference_id": obligation_id,
                    "reference_table": "obligations",
                    "recipient_email": "",  # Filled by Celery task from org settings
                    "subject": f"Obligation reminder: {label}",
                    "body": f"An obligation is due in {days} days.",
                    "scheduled_at": reminder_date.isoformat(),
                    "is_sent": False,
                })

        if reminders:
            self.supabase.table("reminders").insert(reminders).execute()
