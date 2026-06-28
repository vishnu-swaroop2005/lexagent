import uuid
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from app.services.gemini_client import GeminiClient
from app.utils.supabase_client import get_supabase_client


QUESTIONNAIRE_PROMPT = """You are a legal document specialist. Generate a questionnaire for creating a {doc_type}.

The questionnaire should gather all necessary information to draft a legally sound {doc_type}.
Return a JSON object in this format:
{{
  "title": "NDA Questionnaire",
  "fields": [
    {{
      "id": "field_id",
      "label": "Human readable question",
      "type": "text|textarea|select|date|number|email",
      "required": true,
      "options": ["option1", "option2"],  // only for select type
      "placeholder": "Example input",
      "help_text": "Additional context for the user"
    }}
  ]
}}

Make the questions comprehensive but not overwhelming. Include:
- Party information (names, addresses, roles)
- Key terms specific to this document type
- Dates and durations
- Jurisdiction
- Special conditions

For startup-friendly documents, include questions about:
- IP ownership
- Equity considerations (if applicable)
- Revenue sharing (if applicable)
"""

DOCUMENT_DRAFTING_PROMPT = """You are a senior legal document drafter. Draft a professional {doc_type} based on the following information:

{answers_text}

Requirements:
1. Use proper legal formatting with numbered sections
2. Include standard legal clauses appropriate for this document type
3. Use clear, enforceable language
4. Include definitions section
5. Include governing law and dispute resolution
6. Include signature blocks for all parties
7. Mark this document as "AI-Generated Draft - Review Recommended"

The document should be suitable for a startup context - practical, clear, and protective
without being overly complex.

Return the complete document text with proper formatting using markdown."""


class DocumentGenerator:
    """AI-powered legal document generation engine.

    Supports: NDA, MOU, Service Agreement, Founder Agreement, Employment Agreement.

    Flow:
    1. Generate dynamic questionnaire based on doc type
    2. Draft document using answers + Gemini
    3. Convert to PDF with proper legal formatting

    To add new document types: no code changes needed. Gemini adapts
    the questionnaire and drafting based on the doc_type string.
    For more control, add templates to the document_templates table.
    """

    def __init__(self):
        self.gemini = GeminiClient()
        self.supabase = get_supabase_client()

    async def generate_questionnaire(self, doc_type: str, org_id: str) -> dict:
        """Generate a dynamic questionnaire for a document type.

        First checks for a saved template. Falls back to AI generation.

        Args:
            doc_type: Document type (e.g., 'nda', 'mou').
            org_id: Organization ID.

        Returns:
            JSON schema for the questionnaire form.
        """
        # Check for existing template
        template = (
            self.supabase.table("document_templates")
            .select("questionnaire_schema")
            .or_(f"org_id.eq.{org_id},is_system.eq.true")
            .eq("doc_type", doc_type)
            .limit(1)
            .execute()
        ).data

        if template and template[0].get("questionnaire_schema"):
            return template[0]["questionnaire_schema"]

        # AI-generate questionnaire
        schema = await self.gemini.generate_json(
            QUESTIONNAIRE_PROMPT.format(doc_type=doc_type),
            system_instruction="You are a legal form designer. Return only valid JSON.",
        )

        return schema

    async def create_and_draft(
        self,
        doc_type: str,
        title: str,
        answers: dict,
        template_id: str | None,
        org_id: str,
        user_id: str,
    ) -> dict:
        """Create a document record and generate its content.

        Args:
            doc_type: Document type.
            title: User-provided title.
            answers: Filled questionnaire answers.
            template_id: Optional template UUID.
            org_id: Organization ID.
            user_id: Creator's user ID.

        Returns:
            The created document record.
        """
        document_id = str(uuid.uuid4())

        # Create initial record
        self.supabase.table("documents").insert({
            "id": document_id,
            "org_id": org_id,
            "template_id": template_id,
            "title": title,
            "doc_type": doc_type,
            "status": "generating",
            "questionnaire_answers": answers,
            "created_by": user_id,
        }).execute()

        # Format answers for the prompt
        answers_text = "\n".join(f"- {k}: {v}" for k, v in answers.items())

        # Generate document content
        content = await self.gemini.generate(
            DOCUMENT_DRAFTING_PROMPT.format(doc_type=doc_type, answers_text=answers_text),
            system_instruction="You are a senior legal document drafter. Produce complete, professional documents.",
        )

        # Update document with generated content
        self.supabase.table("documents").update({
            "generated_content": content,
            "status": "generated",
        }).eq("id", document_id).execute()

        # Create version record
        self.supabase.table("document_versions").insert({
            "id": str(uuid.uuid4()),
            "org_id": org_id,
            "document_id": document_id,
            "version_number": 1,
            "file_path": "",
            "change_summary": "Initial AI-generated draft",
            "created_by": user_id,
        }).execute()

        # Fetch and return the full record
        result = (
            self.supabase.table("documents")
            .select("*")
            .eq("id", document_id)
            .single()
            .execute()
        ).data

        return result

    async def generate_pdf(self, document_id: str, org_id: str) -> str:
        """Generate a PDF from the document's markdown content.

        Uses ReportLab to create a properly formatted legal PDF
        with headers, footers, page numbers, and signature blocks.

        Args:
            document_id: Document UUID.
            org_id: Organization ID.

        Returns:
            Storage path of the generated PDF.
        """
        document = (
            self.supabase.table("documents")
            .select("*")
            .eq("id", document_id)
            .eq("org_id", org_id)
            .single()
            .execute()
        ).data

        content = document.get("generated_content", "")

        # Build PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=inch,
            leftMargin=inch,
            topMargin=inch,
            bottomMargin=inch,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Title"],
            fontSize=18,
            spaceAfter=30,
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontSize=11,
            leading=16,
            spaceAfter=8,
        )
        heading_style = ParagraphStyle(
            "DocHeading",
            parent=styles["Heading2"],
            fontSize=13,
            spaceAfter=12,
            spaceBefore=16,
        )

        elements = []
        elements.append(Paragraph(document["title"], title_style))
        elements.append(Paragraph(
            '<i>[AI-Generated Draft - Review Recommended]</i>',
            ParagraphStyle("Disclaimer", parent=styles["Normal"], fontSize=9, textColor="gray"),
        ))
        elements.append(Spacer(1, 20))

        # Convert markdown-ish content to paragraphs
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                elements.append(Spacer(1, 8))
            elif line.startswith("# "):
                elements.append(Paragraph(line[2:], title_style))
            elif line.startswith("## "):
                elements.append(Paragraph(line[3:], heading_style))
            elif line.startswith("**") and line.endswith("**"):
                elements.append(Paragraph(f"<b>{line[2:-2]}</b>", body_style))
            else:
                # Escape XML special chars for ReportLab
                safe_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                elements.append(Paragraph(safe_line, body_style))

        # Add signature blocks
        elements.append(Spacer(1, 40))
        elements.append(Paragraph("SIGNATURES", heading_style))
        elements.append(Spacer(1, 20))

        parties = (
            self.supabase.table("document_parties")
            .select("name, role")
            .eq("document_id", document_id)
            .order("signing_order")
            .execute()
        ).data

        for party in (parties or []):
            elements.append(Paragraph(f"<b>{party['name']}</b> ({party['role']})", body_style))
            elements.append(Paragraph("Signature: _________________________", body_style))
            elements.append(Paragraph("Date: _________________________", body_style))
            elements.append(Spacer(1, 20))

        doc.build(elements)

        # Upload to storage
        buffer.seek(0)
        pdf_path = f"{org_id}/{document_id}/{document['title'].replace(' ', '_')}.pdf"

        self.supabase.storage.from_("documents").upload(
            path=pdf_path,
            file=buffer.getvalue(),
            file_options={"content-type": "application/pdf"},
        )

        # Update document
        self.supabase.table("documents").update({
            "file_path": pdf_path,
        }).eq("id", document_id).execute()

        return pdf_path
