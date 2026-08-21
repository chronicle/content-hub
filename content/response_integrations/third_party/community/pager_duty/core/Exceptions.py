from __future__ import annotations


class PagerDutyException(Exception):
    """Base exception for PagerDuty integration."""


class PagerDutyNotFoundError(PagerDutyException):
    """Exception raised when a requested PagerDuty resource is not found."""

