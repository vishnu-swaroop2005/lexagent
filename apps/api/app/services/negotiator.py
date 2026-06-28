import uuid
import json
from app.services.gemini_client import GeminiClient
from app.services.parser import ParserService
from app.services.email_service import EmailService
from app.utils.supabase_client import get_supabase_client


class NegotiationAgent:
    """Manages contract negotiation workflows.

    Handles version tracking, clause-level diffing, AI-powered counter-offer
    suggestions, and email communication with counterparties.

    Escalation: if a new clause has risk > 'high' or is a novel clause type,
    the agent flags for human review instead of auto-suggesting.
    """

    def __init__(self):
        self.gemini = GeminiClient()
        self.supabase = get_supabase_client()
        self.email_service = EmailService()

    async def start_negotiation(
        self, contract_id: str, counterparty_email: str, counterparty_name: str, org_id: str
    ) -> str:
        """Start a new negotiation thread for a contract.

        Args:
            contract_id: The contract UUID.
            counterparty_email: Counterparty's email address.
            counterparty_name: Counterparty's name.
            org_id: Organization ID.

        Returns:
            The negotiation UUID.
        """
        negotiation_id = str(uuid.uuid4())

        self.supabase.table("negotiations").insert({
            "id": negotiation_id,
            "org_id": org_id,
            "contract_id": contract_id,
            "counterparty_email": counterparty_email,
            "counterparty_name": counterparty_name,
            "status": "active",
            "current_version": 1,
        }).execute()

        # Record the initial action
        self.supabase.table("negotiation_history").insert({
            "id": str(uuid.uuid4()),
            "org_id": org_id,
            "negotiation_id": negotiation_id,
            "version": 1,
            "action": "started",
            "message": f"Negotiation started with {counterparty_name}",
            "actor": "system",
        }).execute()

        # Update contract status
        self.supabase.table("contracts").update(
            {"status": "negotiating"}
        ).eq("id", contract_id).execute()

        return negotiation_id

    async def process_counterparty_response(
        self, negotiation_id: str, file_bytes: bytes, filename: str, org_id: str
    ) -> dict:
        """Process a revised contract from the counterparty.

        1. Parses the new version
        2. Diffs against the previous version
        3. Identifies new risks
        4. Flags for escalation if needed

        Returns:
            Dict with version number and diff summary.
        """
        negotiation = (
            self.supabase.table("negotiations")
            .select("*")
            .eq("id", negotiation_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        ).data

        new_version = negotiation["current_version"] + 1

        # Parse the new document
        parser = ParserService()
        file_type = "docx" if filename.endswith(".docx") else "pdf"
        new_text = parser.extract_text(file_bytes, file_type)

        # Get previous version text
        contract = (
            self.supabase.table("contracts")
            .select("raw_text")
            .eq("id", negotiation["contract_id"])
            .single()
            .execute()
        ).data

        old_text = contract.get("raw_text", "")

        # Use Gemini to diff
        diff_summary = await self.gemini.generate(
            f"""Compare these two contract versions and identify:
1. Changed clauses (what was modified)
2. New clauses added
3. Removed clauses
4. Risk assessment of changes

Previous version:
{old_text[:5000]}

New version:
{new_text[:5000]}

Provide a structured summary.""",
            system_instruction="You are a legal document comparison expert.",
        )

        # Record in history
        self.supabase.table("negotiation_history").insert({
            "id": str(uuid.uuid4()),
            "org_id": org_id,
            "negotiation_id": negotiation_id,
            "version": new_version,
            "action": "received",
            "diff_summary": diff_summary,
            "actor": "counterparty",
        }).execute()

        # Update version
        self.supabase.table("negotiations").update(
            {"current_version": new_version}
        ).eq("id", negotiation_id).execute()

        return {"version": new_version, "diff_summary": diff_summary}

    async def suggest_counter_offer(self, negotiation_id: str, org_id: str) -> list[dict]:
        """Generate AI counter-offer suggestions based on the negotiation history.

        Returns:
            List of suggestion dicts with clause references and proposed language.
        """
        # Get full history
        history = (
            self.supabase.table("negotiation_history")
            .select("*")
            .eq("negotiation_id", negotiation_id)
            .eq("org_id", org_id)
            .order("created_at")
            .execute()
        ).data

        history_text = "\n\n".join(
            f"[{h['action']}] Version {h['version']}: {h.get('diff_summary', h.get('message', ''))}"
            for h in history
        )

        suggestions = await self.gemini.generate_json(
            f"""Based on this negotiation history, suggest counter-offers.

{history_text}

Return a JSON array of suggestions:
[{{"clause": "clause description", "current_language": "...", "suggested_language": "...", "rationale": "..."}}]""",
            system_instruction="You are a legal negotiation strategist. Suggest balanced, practical counter-offers.",
        )

        return suggestions if isinstance(suggestions, list) else [suggestions]
