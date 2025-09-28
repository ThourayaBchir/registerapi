"""Utility helpers for email templating and formatting."""

from string import Template


ACTIVATION_TEMPLATE = Template("Your activation code is: $code")


def render_activation_email(code: str) -> str:
    return ACTIVATION_TEMPLATE.substitute(code=code)
