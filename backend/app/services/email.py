import json
import smtplib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.message import EmailMessage as SmtpEmailMessage
from pathlib import Path
from urllib.parse import urlencode

from app.core.config import get_settings


@dataclass
class EmailMessage:
    to: str
    subject: str
    text: str
    html: str | None = None


def build_password_reset_url(token: str) -> str:
    settings = get_settings()
    separator = "&" if "?" in settings.frontend_origin else "?"
    return f"{settings.frontend_origin.rstrip('/')}/{separator}{urlencode({'reset_token': token})}"


def send_email(message: EmailMessage) -> None:
    settings = get_settings()
    provider = settings.email_provider.lower()
    if provider == "disabled":
        return
    if provider == "smtp":
        _send_smtp(message)
        return
    if provider == "outbox":
        _write_outbox(message)
        return
    raise ValueError(f"Unsupported email provider: {settings.email_provider}")


def send_password_reset_email(to_email: str, token: str) -> None:
    reset_url = build_password_reset_url(token)
    send_email(
        EmailMessage(
            to=to_email,
            subject="Reset your DocIntel password",
            text=(
                "A password reset was requested for your DocIntel account.\n\n"
                f"Open this link to reset your password:\n{reset_url}\n\n"
                "If you did not request this, you can ignore this email."
            ),
            html=(
                "<p>A password reset was requested for your DocIntel account.</p>"
                f'<p><a href="{reset_url}">Reset your password</a></p>'
                "<p>If you did not request this, you can ignore this email.</p>"
            ),
        )
    )


def send_workspace_member_email(to_email: str, workspace_name: str, role: str, actor_email: str) -> None:
    settings = get_settings()
    workspace_url = settings.frontend_origin.rstrip("/")
    send_email(
        EmailMessage(
            to=to_email,
            subject=f"You were added to {workspace_name} on DocIntel",
            text=(
                f"{actor_email} added you to the DocIntel workspace \"{workspace_name}\" as {role}.\n\n"
                f"Open DocIntel to view the workspace:\n{workspace_url}\n\n"
                "If this was unexpected, contact your workspace owner."
            ),
            html=(
                f"<p>{actor_email} added you to the DocIntel workspace "
                f"<strong>{workspace_name}</strong> as <strong>{role}</strong>.</p>"
                f'<p><a href="{workspace_url}">Open DocIntel</a></p>'
                "<p>If this was unexpected, contact your workspace owner.</p>"
            ),
        )
    )


def send_workspace_invitation_email(to_email: str, workspace_name: str, role: str, actor_email: str, token: str) -> None:
    settings = get_settings()
    separator = "&" if "?" in settings.frontend_origin else "?"
    invite_url = f"{settings.frontend_origin.rstrip('/')}/{separator}{urlencode({'invite_token': token})}"
    send_email(
        EmailMessage(
            to=to_email,
            subject=f"You are invited to {workspace_name} on DocIntel",
            text=(
                f"{actor_email} invited you to the DocIntel workspace \"{workspace_name}\" as {role}.\n\n"
                f"Accept the invitation here:\n{invite_url}\n\n"
                "Create or sign in to a DocIntel account with this email address to accept."
            ),
            html=(
                f"<p>{actor_email} invited you to the DocIntel workspace "
                f"<strong>{workspace_name}</strong> as <strong>{role}</strong>.</p>"
                f'<p><a href="{invite_url}">Accept invitation</a></p>'
                "<p>Create or sign in to a DocIntel account with this email address to accept.</p>"
            ),
        )
    )


def _send_smtp(message: EmailMessage) -> None:
    settings = get_settings()
    if not settings.smtp_host:
        raise ValueError("SMTP_HOST is required when EMAIL_PROVIDER=smtp")

    email = SmtpEmailMessage()
    email["From"] = settings.email_from
    email["To"] = message.to
    email["Subject"] = message.subject
    email.set_content(message.text)
    if message.html:
        email.add_alternative(message.html, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(email)


def _write_outbox(message: EmailMessage) -> None:
    settings = get_settings()
    outbox_dir = Path(settings.email_outbox_dir)
    outbox_dir.mkdir(parents=True, exist_ok=True)
    payload = asdict(message) | {"created_at": datetime.now(timezone.utc).isoformat()}
    with (outbox_dir / "emails.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
