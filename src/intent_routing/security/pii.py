"""PII masking helpers."""

import re


def mask_pii(text: str) -> str:
    """Mask supported Korean personal data patterns in text."""
    masked = re.sub(r"(\d{6})-([1-4])\d{6}", r"\1-\2******", text)
    masked = re.sub(r"(\d{3})-(\d{2})-(\d{5})", r"\1-\2-*****", masked)
    return re.sub(r"(010)-(\d{3,4})-(\d{4})", r"\1-****-\3", masked)
