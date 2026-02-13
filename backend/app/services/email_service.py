"""Email service for sending report emails via SMTP.

Disabled by default; only active when SMTP_HOST env var is set.
"""

import os
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class EmailService:
    """Async SMTP email service. Disabled if SMTP_HOST is not configured."""

    def __init__(self):
        self.host = os.getenv("SMTP_HOST", "")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.from_addr = os.getenv("SMTP_FROM", self.user)
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    @property
    def is_configured(self) -> bool:
        return bool(self.host)

    async def send_report_email(
        self,
        to_email: str,
        patient_name: str,
        test_type: str,
        pdf_bytes: bytes,
        message: Optional[str] = None,
    ) -> dict:
        """Send a PDF report as an email attachment.

        Returns dict with 'success' bool and 'message' str.
        """
        if not self.is_configured:
            return {"success": False, "message": "SMTP is not configured. Set SMTP_HOST in environment."}

        # Validate email
        try:
            from email_validator import validate_email
            valid = validate_email(to_email, check_deliverability=False)
            to_email = valid.normalized
        except Exception as e:
            return {"success": False, "message": f"Invalid email address: {e}"}

        test_label = {
            "10MWT": "10m Walk Test",
            "TUG": "Timed Up and Go Test",
            "BBS": "Berg Balance Scale",
        }.get(test_type, test_type)

        subject = f"[10M_WT] {patient_name} - {test_label} Report"

        body_lines = [
            f"Patient: {patient_name}",
            f"Test: {test_label}",
            "",
            "Please find the attached PDF report.",
        ]
        if message:
            body_lines.append("")
            body_lines.append(f"Note: {message}")

        body_lines.append("")
        body_lines.append("---")
        body_lines.append("This is an automated email from the 10M Walk Test system.")

        body = "\n".join(body_lines)

        # Build MIME message
        msg = MIMEMultipart()
        msg["From"] = self.from_addr
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Attach PDF
        pdf_attachment = MIMEBase("application", "pdf")
        pdf_attachment.set_payload(pdf_bytes)
        encoders.encode_base64(pdf_attachment)
        filename = f"{patient_name}_{test_type}_report.pdf"
        pdf_attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=filename,
        )
        msg.attach(pdf_attachment)

        # Send
        try:
            import aiosmtplib

            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.user if self.user else None,
                password=self.password if self.password else None,
                start_tls=self.use_tls,
            )
            logger.info(f"Report email sent to {to_email} for patient {patient_name}")
            return {"success": True, "message": f"Email sent to {to_email}"}
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return {"success": False, "message": f"Failed to send email: {e}"}

    async def send_notification_email(
        self,
        to_email: str,
        subject: str,
        body: str,
    ) -> dict:
        """Send a plain text notification email.

        Returns dict with 'success' bool and 'message' str.
        """
        if not self.is_configured:
            return {"success": False, "message": "SMTP is not configured. Set SMTP_HOST in environment."}

        try:
            from email_validator import validate_email
            valid = validate_email(to_email, check_deliverability=False)
            to_email = valid.normalized
        except Exception as e:
            return {"success": False, "message": f"Invalid email address: {e}"}

        msg = MIMEMultipart()
        msg["From"] = self.from_addr
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            import aiosmtplib

            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.user if self.user else None,
                password=self.password if self.password else None,
                start_tls=self.use_tls,
            )
            logger.info(f"Notification email sent to {to_email}: {subject}")
            return {"success": True, "message": f"Email sent to {to_email}"}
        except Exception as e:
            logger.error(f"Failed to send notification to {to_email}: {e}")
            return {"success": False, "message": f"Failed to send email: {e}"}


# Global singleton
email_service = EmailService()
