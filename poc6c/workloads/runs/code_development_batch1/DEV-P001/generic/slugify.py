"""Small dependency-free text slug utility."""

import re


def slugify(text: str) -> str:
    """Convert text to an ASCII identifier used in article URLs."""

    lowered = text.strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
