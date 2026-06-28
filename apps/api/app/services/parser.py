import uuid
import pdfplumber
from docx import Document as DocxDocument
from io import BytesIO

from app.services.gemini_client import GeminiClient
from app.utils.supabase_client import get_supabase_client


CLAUSE_CHUNKING_PROMPT = """You are a legal document analyst. Analyze the following contract text and identify each distinct clause.

For each clause, provide:
- clause_type: A category like "indemnification", "termination", "liability", "confidentiality", "payment", "warranties", "force_majeure", "governing_law", "intellectual_property", "data_protection", "non_compete", "assignment", "notices", "definitions", "entire_agreement", etc.
- title: The section heading or a descriptive title
- content: The full text of the clause

Return a JSON array of objects. Example:
[
  {
    "clause_type": "confidentiality",
    "title": "Section 5 - Confidentiality",
    "content": "The full clause text..."
  }
]

Contract text:
"""


class ParserService:
    """Handles contract file upload, text extraction, and AI-powered clause chunking.

    Supports PDF (via pdfplumber) and DOCX (via python-docx).
    Uses Gemini to identify and classify individual clauses.

    To add new document formats:
    1. Add a new extraction method (e.g., _extract_text_from_rtf)
    2. Update the extract_text method to handle the new file type
    """

    def __init__(self):
        self.gemini = GeminiClient()
        self.supabase = get_supabase_client()

    async def upload_and_queue(
        self,
        file_bytes: bytes,
        filename: str,
        file_type: str,
        title: str,
        counterparty: str | None,
        org_id: str,
        user_id: str,
    ) -> dict:
        """Upload a contract file to storage and queue parsing.

        Args:
            file_bytes: Raw file bytes.
            filename: Original filename.
            file_type: 'pdf' or 'docx'.
            title: User-provided title.
            counterparty: Optional counterparty name.
            org_id: Organization ID for multi-tenant isolation.
            user_id: Uploader's user ID.

        Returns:
            Dict with contract id, status, and task_id.
        """
        contract_id = str(uuid.uuid4())
        storage_path = f"{org_id}/{contract_id}/{filename}"

        # Upload to Supabase Storage
        self.supabase.storage.from_("contracts").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": "application/pdf" if file_type == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        )

        # Create contract record
        self.supabase.table("contracts").insert({
            "id": contract_id,
            "org_id": org_id,
            "title": title,
            "file_path": storage_path,
            "file_type": file_type,
            "status": "uploaded",
            "counterparty": counterparty,
            "uploaded_by": user_id,
        }).execute()

        # Queue async parsing task
        from app.tasks.contract_tasks import parse_contract_task
        task = parse_contract_task.delay(contract_id, org_id)

        return {"id": contract_id, "status": "uploaded", "task_id": task.id}

    async def parse_contract(self, contract_id: str, org_id: str) -> list[dict]:
        """Extract text from a contract file and chunk into clauses.

        1. Downloads the file from Supabase Storage
        2. Extracts raw text based on file type
        3. Sends text to Gemini for clause identification
        4. Stores clauses in the database
        5. Updates contract status to 'parsed'

        Args:
            contract_id: The contract UUID.
            org_id: Organization ID.

        Returns:
            List of extracted clause dicts.
        """
        # Get contract metadata
        contract = (
            self.supabase.table("contracts")
            .select("*")
            .eq("id", contract_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        ).data

        # Update status to parsing
        self.supabase.table("contracts").update(
            {"status": "parsing"}
        ).eq("id", contract_id).execute()

        # Download file from storage
        file_bytes = self.supabase.storage.from_("contracts").download(contract["file_path"])

        # Extract text
        raw_text = self.extract_text(file_bytes, contract["file_type"])

        # Store raw text
        self.supabase.table("contracts").update(
            {"raw_text": raw_text}
        ).eq("id", contract_id).execute()

        # Use Gemini to chunk into clauses
        clauses = await self.gemini.generate_json(
            CLAUSE_CHUNKING_PROMPT + raw_text,
            system_instruction="You are a legal document analyst. Return only valid JSON.",
        )

        # Store clauses
        clause_records = []
        for i, clause in enumerate(clauses):
            clause_id = str(uuid.uuid4())
            record = {
                "id": clause_id,
                "org_id": org_id,
                "contract_id": contract_id,
                "clause_type": clause.get("clause_type", "unknown"),
                "title": clause.get("title", f"Clause {i + 1}"),
                "content": clause.get("content", ""),
                "position_start": i * 100,  # Approximate positioning
                "position_end": (i + 1) * 100,
            }
            clause_records.append(record)

        if clause_records:
            self.supabase.table("clauses").insert(clause_records).execute()

        # Update contract status
        self.supabase.table("contracts").update(
            {"status": "parsed"}
        ).eq("id", contract_id).execute()

        return clause_records

    def extract_text(self, file_bytes: bytes, file_type: str) -> str:
        """Extract raw text from a file based on its type.

        Args:
            file_bytes: Raw file content.
            file_type: 'pdf' or 'docx'.

        Returns:
            Extracted text string.
        """
        if file_type == "pdf":
            return self._extract_from_pdf(file_bytes)
        elif file_type == "docx":
            return self._extract_from_docx(file_bytes)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _extract_from_pdf(self, file_bytes: bytes) -> str:
        """Extract text from a PDF using pdfplumber."""
        text_parts = []
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n\n".join(text_parts)

    def _extract_from_docx(self, file_bytes: bytes) -> str:
        """Extract text from a DOCX using python-docx."""
        doc = DocxDocument(BytesIO(file_bytes))
        return "\n\n".join(para.text for para in doc.paragraphs if para.text.strip())
