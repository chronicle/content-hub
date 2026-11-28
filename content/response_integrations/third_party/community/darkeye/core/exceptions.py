from __future__ import annotations


class DarkEyeError(Exception):
    """General exception for DarkEye."""


class DarkEyeConfigurationError(DarkEyeError):
    """Neither product has an API key."""


class DarkEyeInvalidEntityError(DarkEyeError):
    """The entity is not a plain domain name or email address."""


class DarkEyeProductError(DarkEyeError):
    """A product lookup failed. The message is safe to show: it never holds an API key."""

    def __init__(self, product: str, message: str, status_code: int | None = None) -> None:
        super().__init__(f"{product}: {message}")
        self.product: str = product
        self.status_code: int | None = status_code


class DarkEyeAllProductsFailedError(DarkEyeError):
    """No configured product answered for an entity."""
