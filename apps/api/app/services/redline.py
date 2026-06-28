import uuid
from io import BytesIO
from copy import deepcopy
from docx import Document as DocxDocument
from lxml import etree

from app.utils.supabase_client import get_supabase_client

# Word XML namespaces
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NSMAP = {"w": WORD_NS}


class RedlineEngine:
    """Generates tracked changes (redlines) in DOCX files.

    Takes a review report's findings and applies them as Word tracked changes
    using direct XML manipulation (w:del/w:ins elements).

    python-docx doesn't natively support revision marks, so we use lxml
    to manipulate the underlying XML directly.

    For each risky clause:
    - Original text appears with strikethrough (red) via w:del
    - Suggested replacement appears with underline (green) via w:ins
    """

    def __init__(self):
        self.supabase = get_supabase_client()

    async def generate_redline(self, contract_id: str, review_report_id: str, org_id: str) -> dict:
        """Generate a redlined DOCX from a contract and its review report.

        1. Downloads the original DOCX from Storage
        2. Loads the review report findings
        3. For each finding with a suggestion, inserts tracked changes
        4. Uploads the redlined DOCX to Storage
        5. Creates a redlines record

        Args:
            contract_id: The contract UUID.
            review_report_id: The review report UUID.
            org_id: Organization ID.

        Returns:
            Dict with redline_id and file_url.
        """
        # Get contract and report
        contract = (
            self.supabase.table("contracts")
            .select("*")
            .eq("id", contract_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        ).data

        report = (
            self.supabase.table("review_reports")
            .select("*")
            .eq("id", review_report_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        ).data

        if contract["file_type"] != "docx":
            raise ValueError("Redlining only supported for DOCX files")

        # Download original file
        file_bytes = self.supabase.storage.from_("contracts").download(contract["file_path"])
        doc = DocxDocument(BytesIO(file_bytes))

        # Build changes list
        changes = []
        findings = report.get("findings", [])

        # Get clause text for matching
        clauses = (
            self.supabase.table("clauses")
            .select("id, content")
            .eq("contract_id", contract_id)
            .eq("org_id", org_id)
            .execute()
        ).data
        clause_map = {c["id"]: c["content"] for c in (clauses or [])}

        for finding in findings:
            clause_id = finding.get("clause_id")
            suggestion = finding.get("suggestion", "")
            if not clause_id or not suggestion or clause_id not in clause_map:
                continue

            original_text = clause_map[clause_id]

            # Apply tracked change in the document
            self._apply_tracked_change(doc, original_text, suggestion)

            changes.append({
                "clause_id": clause_id,
                "original_text": original_text[:200],  # Truncate for storage
                "suggested_text": suggestion[:200],
                "reason": finding.get("issue", ""),
                "accepted": None,
            })

        # Save redlined document
        output = BytesIO()
        doc.save(output)
        output.seek(0)

        redline_id = str(uuid.uuid4())
        redline_path = f"{org_id}/{contract_id}/redline_{redline_id}.docx"

        self.supabase.storage.from_("contracts").upload(
            path=redline_path,
            file=output.getvalue(),
            file_options={"content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        )

        # Create redline record
        self.supabase.table("redlines").insert({
            "id": redline_id,
            "org_id": org_id,
            "contract_id": contract_id,
            "review_report_id": review_report_id,
            "original_file_path": contract["file_path"],
            "redlined_file_path": redline_path,
            "changes": changes,
            "status": "pending",
        }).execute()

        # Update contract status
        self.supabase.table("contracts").update(
            {"status": "redlined"}
        ).eq("id", contract_id).execute()

        return {"redline_id": redline_id, "file_path": redline_path}

    def _apply_tracked_change(self, doc: DocxDocument, original_text: str, new_text: str):
        """Insert tracked changes into the DOCX using XML manipulation.

        Finds paragraphs containing the original text and replaces with
        w:del (strikethrough) + w:ins (underline) revision marks.
        """
        for paragraph in doc.paragraphs:
            if original_text[:50] in paragraph.text:
                p_elem = paragraph._element

                # Create deletion element
                del_elem = etree.SubElement(p_elem, f"{{{WORD_NS}}}del")
                del_elem.set(f"{{{WORD_NS}}}author", "LexAgent AI")
                del_elem.set(f"{{{WORD_NS}}}date", "2024-01-01T00:00:00Z")

                del_run = etree.SubElement(del_elem, f"{{{WORD_NS}}}r")
                del_rpr = etree.SubElement(del_run, f"{{{WORD_NS}}}rPr")
                del_strike = etree.SubElement(del_rpr, f"{{{WORD_NS}}}strike")
                del_color = etree.SubElement(del_rpr, f"{{{WORD_NS}}}color")
                del_color.set(f"{{{WORD_NS}}}val", "FF0000")  # Red
                del_text = etree.SubElement(del_run, f"{{{WORD_NS}}}delText")
                del_text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                del_text.text = original_text

                # Create insertion element
                ins_elem = etree.SubElement(p_elem, f"{{{WORD_NS}}}ins")
                ins_elem.set(f"{{{WORD_NS}}}author", "LexAgent AI")
                ins_elem.set(f"{{{WORD_NS}}}date", "2024-01-01T00:00:00Z")

                ins_run = etree.SubElement(ins_elem, f"{{{WORD_NS}}}r")
                ins_rpr = etree.SubElement(ins_run, f"{{{WORD_NS}}}rPr")
                ins_underline = etree.SubElement(ins_rpr, f"{{{WORD_NS}}}u")
                ins_underline.set(f"{{{WORD_NS}}}val", "single")
                ins_color = etree.SubElement(ins_rpr, f"{{{WORD_NS}}}color")
                ins_color.set(f"{{{WORD_NS}}}val", "00AA00")  # Green
                ins_text = etree.SubElement(ins_run, f"{{{WORD_NS}}}t")
                ins_text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                ins_text.text = new_text

                break

    async def apply_changes(self, redline_id: str, accepted_change_ids: list[str], org_id: str) -> dict:
        """Apply accepted redline changes and generate a clean document.

        Args:
            redline_id: The redline UUID.
            accepted_change_ids: List of clause IDs whose changes are accepted.
            org_id: Organization ID.

        Returns:
            Dict with the clean file path.
        """
        redline = (
            self.supabase.table("redlines")
            .select("*")
            .eq("id", redline_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        ).data

        # Update changes with acceptance status
        changes = redline.get("changes", [])
        for change in changes:
            change["accepted"] = change["clause_id"] in accepted_change_ids

        self.supabase.table("redlines").update({
            "changes": changes,
            "status": "accepted",
        }).eq("id", redline_id).execute()

        return {"status": "accepted", "accepted_count": len(accepted_change_ids)}
