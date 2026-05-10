import re

UZ_MOBILE_PREFIXES = {"90", "91", "93", "94", "95", "97", "98", "99", "88", "33"}


def normalize_uz_phone(phone_text: str) -> str | None:
    cleaned = re.sub(r"[\s\-()]", "", phone_text.strip())
    if not cleaned:
        return None

    if cleaned.startswith("+"):
        if cleaned.count("+") > 1:
            return None
        digits = cleaned[1:]
    else:
        digits = cleaned

    if not digits.isdigit():
        return None

    if cleaned.startswith("+998") and len(cleaned) == 13:
        return cleaned
    if digits.startswith("998") and len(digits) == 12:
        return f"+{digits}"
    if len(digits) == 9 and digits[:2] in UZ_MOBILE_PREFIXES:
        return f"+998{digits}"
    return None


def is_valid_uz_phone(phone_text: str) -> bool:
    return normalize_uz_phone(phone_text) is not None
