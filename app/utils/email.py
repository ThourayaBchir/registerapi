"""Utility helpers for email templating and formatting."""

from string import Template

ACTIVATION_SUBJECT_TEMPLATE = Template("Your activation code for User Activation API")
ACTIVATION_BODY_TEMPLATE = Template(
    """
Hello,

Use the code below to activate your account:

    $code

This code expires in $ttl minutes. If you did not request this, please ignore this email.

Regards,
User Activation API
""".strip()
)


def _format_ttl_minutes(ttl_seconds: int) -> str:
    minutes = ttl_seconds / 60
    if minutes.is_integer():
        return f"{int(minutes)}"
    return f"{minutes:.1f}"


def render_activation_email(code: str, ttl_seconds: int) -> tuple[str, str]:
    """Return subject and body for activation email."""
    subject = ACTIVATION_SUBJECT_TEMPLATE.substitute()
    body = ACTIVATION_BODY_TEMPLATE.substitute(code=code, ttl=_format_ttl_minutes(ttl_seconds))
    return subject, body
