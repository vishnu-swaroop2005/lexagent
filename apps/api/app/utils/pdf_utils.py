from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch


def markdown_to_pdf(content: str, title: str) -> bytes:
    """Convert markdown-formatted text to a PDF document.

    Args:
        content: Markdown text content.
        title: Document title.

    Returns:
        PDF bytes.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Spacer(1, 20))

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            elements.append(Spacer(1, 8))
        elif line.startswith("# "):
            elements.append(Paragraph(line[2:], styles["Heading1"]))
        elif line.startswith("## "):
            elements.append(Paragraph(line[3:], styles["Heading2"]))
        elif line.startswith("### "):
            elements.append(Paragraph(line[4:], styles["Heading3"]))
        else:
            safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            elements.append(Paragraph(safe, styles["Normal"]))

    doc.build(elements)
    return buffer.getvalue()
