from __future__ import annotations
class CloudflareException(Exception):
    """
    General exception for Cloudflare
    """

    pass


class ZoneNotFoundException(Exception):
    pass


class AccountNotFoundException(Exception):
    pass


class RuleListNotFoundException(Exception):
    pass
