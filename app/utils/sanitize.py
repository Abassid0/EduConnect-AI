import re
from html import escape


def strip_html(value: str) -> str:
    """Remove all HTML tags from a string, then escape any remaining entities."""
    if not value:
        return value
    cleaned = re.sub(r"<[^>]*>", "", value)
    return escape(cleaned, quote=True)


def sanitize_text(value: str) -> str:
    """Strip HTML, collapse whitespace, and trim."""
    if not value:
        return value
    text = strip_html(value)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sanitize_phone(value: str) -> str:
    """Keep only digits, plus, hyphens, and spaces."""
    if not value:
        return value
    return re.sub(r"[^\d\s+\-]", "", value).strip()
