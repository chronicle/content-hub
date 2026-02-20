"""Utility functions for the NetApp Ransomware Resilience integration."""
from __future__ import annotations

from __future__ import annotations

import hashlib
from typing import Any, Dict
from urllib.parse import urlparse

from TIPCommon.smp_time import unix_now

from .constants import DEFAULT_EXPIRY_SECONDS, EXPIRES_IN_KEY


def compute_expiry(response: Dict[str, Any]) -> int:
    """Calculate token expiration time from OAuth response.

    Args:
        response: OAuth token response dictionary containing 'expires_in' field.

    Returns:
        int: Expiration time in milliseconds since epoch.
    """
    now_ms = unix_now()
    expires_in = response.get(EXPIRES_IN_KEY)
    if expires_in is not None:
        try:
            expires_in_sec = int(expires_in)
            return now_ms + (expires_in_sec * 1000)

        except (TypeError, ValueError):
            pass
    return now_ms + (DEFAULT_EXPIRY_SECONDS * 1000)


def generate_encryption_key(client_id: str, account_domain: str) -> str:
    """Generate an encryption key from existing settings.

    Args:
        client_id: OAuth client ID.
        account_domain: Rubrik account domain.

    Returns:
        str: SHA-256 hash hex string used for token encryption.
    """
    unique_string = f"{client_id}:{account_domain}"
    # Create a SHA-256 hash to ensure consistent length and format
    return hashlib.sha256(unique_string.encode()).hexdigest()


def extract_domain_from_uri(service_url: str) -> str:
    """
    Extract the domain (netloc) from the service_url.

    Args:
        service_url (str): The SaaS service url.

    Returns:
        str: The domain part of the URL (e.g., "api.bluexp.netapp.com")

    Raises:
        ValueError: If the URI is invalid or domain cannot be extracted
    """
    if not service_url or not service_url.strip():
        raise ValueError("access_token_uri not present in the Service Account JSON.")

    parsed_uri = urlparse(service_url.strip())
    domain = parsed_uri.netloc

    if not domain:
        raise ValueError(
            f"Could not extract Rubrik Account domain from service_url: {service_url}"
        )

    return domain


def build_rrs_url(url: str, account_id: str, endpoint: str):
    return f"{url}/{account_id}/{endpoint}"

