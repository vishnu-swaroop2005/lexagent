import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from app.config import get_settings


class EmailService:
    """Handles all outbound email communication.

    Used for: signing requests, signed copies, obligation reminders,
    negotiation messages.

    Connects via SMTP (Gmail by default). To swap provider,
    change SMTP settings in .env.
    """

    def __init__(self):
        self.settings = get_settings()

    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        attachment_bytes: bytes | None = None,
        attachment_filename: str | None = None,
    ) -> bool:
        """Send an email via SMTP.

        Args:
            to: Recipient email address.
            subject: Email subject.
            html_body: HTML email body.
            attachment_bytes: Optional file attachment bytes.
            attachment_filename: Name for the attachment file.

        Returns:
            True if sent successfully.
        """
        msg = MIMEMultipart()
        msg["From"] = self.settings.smtp_from
        msg["To"] = to
        msg["Subject"] = subject

        msg.attach(MIMEText(html_body, "html"))

        if attachment_bytes and attachment_filename:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment_bytes)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={attachment_filename}")
            msg.attach(part)

        await aiosmtplib.send(
            msg,
            hostname=self.settings.smtp_host,
            port=self.settings.smtp_port,
            username=self.settings.smtp_user,
            password=self.settings.smtp_password,
            use_tls=True,
        )

        return True

    async def send_signing_request(
        self, to: str, recipient_name: str, document_title: str, signing_url: str, sender_name: str
    ) -> bool:
        """Send a signing request email with the signing link.

        Args:
            to: Signer's email.
            recipient_name: Signer's name.
            document_title: Title of the document.
            signing_url: URL to the signing page.
            sender_name: Name of the sender.
        """
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a1a2e;">Document Signature Request</h2>
            <p>Dear {recipient_name},</p>
            <p>You have been requested to review and sign the following document:</p>
            <div style="background: #f5f5f5; padding: 16px; border-radius: 8px; margin: 16px 0;">
                <strong>{document_title}</strong>
            </div>
            <p>Please review the document and provide your digital signature at your convenience.</p>
            <a href="{signing_url}"
               style="display: inline-block; background: #1a1a2e; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 6px; margin: 16px 0;">
                Review & Sign Document
            </a>
            <p style="color: #666; font-size: 12px; margin-top: 24px;">
                This document was sent by {sender_name} via LexAgent.
                If you have questions, please contact them directly.
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin-top: 24px;">
            <p style="color: #999; font-size: 11px;">
                [AI-Generated Communication] - Powered by LexAgent
            </p>
        </div>
        """
        return await self.send_email(to, f"Signature Required: {document_title}", html)

    async def send_signed_copy(
        self, to: str, document_title: str, pdf_bytes: bytes
    ) -> bool:
        """Send a copy of the fully signed document."""
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a1a2e;">Document Fully Signed</h2>
            <p>All parties have signed <strong>{document_title}</strong>.</p>
            <p>A copy of the signed document is attached for your records.</p>
            <hr style="border: none; border-top: 1px solid #eee; margin-top: 24px;">
            <p style="color: #999; font-size: 11px;">Powered by LexAgent</p>
        </div>
        """
        return await self.send_email(
            to, f"Signed: {document_title}", html,
            attachment_bytes=pdf_bytes,
            attachment_filename=f"{document_title.replace(' ', '_')}_signed.pdf",
        )

    async def send_reminder(self, to: str, subject: str, body: str) -> bool:
        """Send a generic reminder email."""
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1a1a2e;">Reminder</h2>
            <p>{body}</p>
            <hr style="border: none; border-top: 1px solid #eee; margin-top: 24px;">
            <p style="color: #999; font-size: 11px;">Powered by LexAgent</p>
        </div>
        """
        return await self.send_email(to, subject, html)
