"""Utility functions for Cylus integration."""

from TIPCommon.extraction import extract_configuration_param


def get_integration_params(siemplify):
    """Extract integration parameters from configuration.

    Args:
        siemplify: SiemplifyAction instance

    Returns:
        tuple: (api_root, api_key, verify_ssl)
    """
    api_root = extract_configuration_param(
        siemplify,
        provider_name="CylusOne",
        param_name="Base URL",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name="CylusOne",
        param_name="Cylus API Key",
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name="CylusOne",
        param_name="Verify SSL",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )
    return api_root, api_key, verify_ssl


def validate_ip_address(ip_address):
    """Validate IP address format.

    Args:
        ip_address (str): IP address to validate

    Returns:
        bool: True if valid IP address format
    """
    import re

    ipv4_pattern = (
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    )
    return bool(re.match(ipv4_pattern, ip_address))


def sanitize_url(url):
    """Sanitize and format URL.

    Args:
        url (str): URL to sanitize

    Returns:
        str: Sanitized URL
    """
    if not url:
        return ""

    # Remove trailing slashes
    url = url.rstrip("/")

    # Ensure protocol is present
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    return url
