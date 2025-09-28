"""4-digit activation code generator."""

import secrets


def generate_code() -> str:
    return f"{secrets.randbelow(10000):04d}"
