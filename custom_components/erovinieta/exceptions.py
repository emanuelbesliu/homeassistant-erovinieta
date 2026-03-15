"""Exceptions for the eRovinieta integration."""

from homeassistant.exceptions import HomeAssistantError


class ERovignetaError(HomeAssistantError):
    """Base exception for eRovinieta."""


class ERovignetaAPIError(ERovignetaError):
    """General API error (connection, unexpected response, etc.)."""


class ERovignetaCaptchaError(ERovignetaAPIError):
    """Captcha OCR or server-side captcha validation failed (retriable)."""


class ERovignetaConnectionError(ERovignetaAPIError):
    """Network / HTTP connection error."""
