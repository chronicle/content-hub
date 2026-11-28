from __future__ import annotations

import re
import unicodedata
from typing import Any

from .exceptions import DarkEyeInvalidEntityError

# Both APIs treat * and ? as wildcards, so only plain domain names and addresses are queried.
DOMAIN_REGEX: re.Pattern[str] = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")
EMAIL_LOCAL_PART_REGEX: re.Pattern[str] = re.compile(r"^[a-z0-9._%+-]+$")
# Characters that would make a match part of a longer address: any other character allowed
# in a local part before it, and another address part after it.
ADDRESS_BEFORE: str = ".+%@-!#$&'*/=?^`{|}~"
ADDRESS_AFTER: str = "@+-"


def clean(value: Any) -> str:  # noqa: ANN401
    """Return NFKC-normalized single-line text, or "" for values that are not text or numbers.

    Some group and source names use styled Unicode characters and irregular spacing.

    Args:
        value: The value read from an API response.

    Returns:
        str: The cleaned text.
    """
    if isinstance(value, bool) or not isinstance(value, str | int):
        return ""
    text: str = unicodedata.normalize("NFKC", str(value))
    text = "".join(char for char in text if unicodedata.category(char) not in ("Cc", "Cf"))
    return " ".join(text.split())


def normalize_domain(value: str) -> str:
    """Lower-case a domain and check it is a plain domain name.

    Args:
        value: The entity identifier.

    Returns:
        str: The domain in ASCII form.

    Raises:
        DarkEyeInvalidEntityError: If the value is not a plain domain name.
    """
    domain: str = str(value).strip().lower().rstrip(".")
    try:
        domain = domain.encode("idna").decode("ascii")
    except UnicodeError:
        pass
    if not DOMAIN_REGEX.match(domain) or domain.rsplit(".", 1)[-1].isdigit():
        msg: str = f"{value} is not a plain domain name."
        raise DarkEyeInvalidEntityError(msg)
    return domain


def normalize_email(value: str) -> str:
    """Lower-case an email address and check it is a plain address.

    Args:
        value: The entity identifier.

    Returns:
        str: The address with its domain in ASCII form.

    Raises:
        DarkEyeInvalidEntityError: If the value is not a plain email address.
    """
    address: str = str(value).strip().lower()
    local_part, separator, domain = address.rpartition("@")
    if not separator or not EMAIL_LOCAL_PART_REGEX.match(local_part):
        msg: str = f"{value} is not a plain email address."
        raise DarkEyeInvalidEntityError(msg)
    try:
        domain = normalize_domain(domain)
    except DarkEyeInvalidEntityError:
        msg = f"{value} is not a plain email address."
        raise DarkEyeInvalidEntityError(msg) from None
    return f"{local_part}@{domain}"


def is_email(value: str) -> bool:
    """Tell whether an entity identifier is a plain email address.

    Args:
        value: The entity identifier.

    Returns:
        bool: True for a plain email address.
    """
    try:
        normalize_email(value)
    except DarkEyeInvalidEntityError:
        return False
    return True


def is_about_domain(website: str, title: str, domain: str) -> bool:
    """Tell whether a Breach House record is about the domain, not only near it.

    The Breach House search matches free text. With a website, it must be the domain or one of
    its subdomains. Without one, the domain must stand alone as a hostname in the title: not
    inside notexample.com or example.com.other.org, but still as mail.example.com.

    Args:
        website: The website of the record.
        title: The title of the record.
        domain: The normalized domain that was searched.

    Returns:
        bool: True when the record is about the domain.
    """
    website = website.lower().rstrip(".")
    if website:
        return website == domain or website.endswith(f".{domain}")
    pattern: str = rf"(?<![\w-]){re.escape(domain)}(?![\w-]|\.\w)"
    return bool(title) and re.search(pattern, title.lower()) is not None


def mentions_email(address: str, *fields: str) -> bool:
    """Tell whether the exact email address appears in any of the fields.

    The address has to stand alone: "bob@example.com" is not in "rob.bob@example.com" or
    "bob@example.com.au", which are other addresses.

    Args:
        address: The normalized email address.
        *fields: Text fields of the record.

    Returns:
        bool: True when one of the fields holds the address.
    """
    pattern: str = (
        rf"(?<![\w{re.escape(ADDRESS_BEFORE)}]){re.escape(address)}"
        rf"(?![\w{re.escape(ADDRESS_AFTER)}]|\.\w)"
    )
    return any(re.search(pattern, field.lower()) is not None for field in fields if field)


def has_next_page(data: dict[str, Any]) -> bool:
    """Read the next-page flag of a HaveIBeenRansom page.

    Args:
        data: The JSON page.

    Returns:
        bool: True when another page follows.
    """
    pagination: Any = data.get("pagination")
    if isinstance(pagination, dict) and "has_next" in pagination:
        return bool(pagination.get("has_next"))
    return bool(data.get("has_next"))


def status_message(status_code: int) -> str:
    """Describe a failed HTTP status without echoing the response body.

    Args:
        status_code: The HTTP status code.

    Returns:
        str: The message.
    """
    if status_code in (401, 403):
        return "authentication failed or the plan does not allow this request; check the API key."
    if status_code == 429:
        return "quota or rate limit reached; retry later."
    return f"returned HTTP {status_code}."
