"""API client for erovinieta.ro — check Romanian road tax (rovinieta) validity."""

import logging
import time
from typing import Any

import aiohttp

# ddddocr 1.6.0 has a packaging bug: core/ directory shadows core.py,
# breaking the top-level import.  Work around it by patching __init__.py
# in-process before the first import.
try:
    import ddddocr
except ImportError:
    # Attempt to fix the broken __init__.py at the package level.
    # The compat sub-package works fine; only the top-level __init__ is wrong.
    import importlib
    import importlib.util
    import pathlib
    import sys

    _spec = importlib.util.find_spec("ddddocr")
    if _spec is None or _spec.origin is None:
        raise  # genuinely missing
    _init_path = pathlib.Path(_spec.origin)
    _init_path.write_text(
        '# coding=utf-8\nfrom .compat import DdddOcr\n\n__all__ = ["DdddOcr"]\n',
        encoding="utf-8",
    )
    # Remove any cached bytecode so Python re-reads the patched source
    for _pyc in _init_path.parent.glob("__pycache__/__init__.*"):
        _pyc.unlink(missing_ok=True)
    # Drop the partially-loaded module so importlib retries from scratch
    sys.modules.pop("ddddocr", None)
    import ddddocr  # noqa: E402  — should now succeed

from .const import (
    API_URL_CAPTCHA,
    API_URL_GET_ROADTAX,
    MAX_CAPTCHA_RETRIES,
)

_LOGGER = logging.getLogger(__name__)


class ERovignetaAPIError(Exception):
    """Base exception for eRovinieta API errors."""


class CaptchaError(ERovignetaAPIError):
    """Captcha OCR or validation failed."""


class ERovignetaAPI:
    """Async API client for erovinieta.ro."""

    def __init__(self) -> None:
        """Initialize the API client."""
        self._ocr: ddddocr.DdddOcr | None = None

    def _get_ocr(self) -> ddddocr.DdddOcr:
        """Lazy-initialize the OCR engine (heavy import, do once)."""
        if self._ocr is None:
            self._ocr = ddddocr.DdddOcr(show_ad=False)
        return self._ocr

    async def async_get_roadtax(
        self,
        plate_number: str,
        vin: str,
        session: aiohttp.ClientSession | None = None,
    ) -> dict[str, Any]:
        """
        Fetch road tax data for a vehicle.

        Handles captcha solving with retries.

        Args:
            plate_number: Vehicle registration plate (e.g. "B123ABC").
            vin: Full VIN / chassis number.
            session: Optional aiohttp session. Creates one if not provided.

        Returns:
            Dict with the full API response data.

        Raises:
            ERovignetaAPIError: On API failure after all retries.
        """
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()

        try:
            return await self._fetch_with_retries(session, plate_number, vin)
        finally:
            if own_session:
                await session.close()

    async def _fetch_with_retries(
        self,
        session: aiohttp.ClientSession,
        plate_number: str,
        vin: str,
    ) -> dict[str, Any]:
        """Attempt captcha + API call with retries on captcha failure."""
        last_error: Exception | None = None

        for attempt in range(1, MAX_CAPTCHA_RETRIES + 1):
            try:
                return await self._single_attempt(session, plate_number, vin)
            except CaptchaError as err:
                _LOGGER.warning(
                    "Captcha attempt %d/%d failed: %s",
                    attempt,
                    MAX_CAPTCHA_RETRIES,
                    err,
                )
                last_error = err
                continue

        raise ERovignetaAPIError(
            f"Failed after {MAX_CAPTCHA_RETRIES} captcha attempts: {last_error}"
        )

    async def _single_attempt(
        self,
        session: aiohttp.ClientSession,
        plate_number: str,
        vin: str,
    ) -> dict[str, Any]:
        """Single captcha-solve + getRoadtax call."""
        # Step 1: Fetch captcha image (establishes JSESSIONID cookie)
        timestamp = int(time.time() * 1000)
        captcha_url = f"{API_URL_CAPTCHA}?t={timestamp}"

        _LOGGER.debug("Fetching captcha from %s", captcha_url)
        async with session.get(captcha_url) as resp:
            if resp.status != 200:
                raise ERovignetaAPIError(
                    f"Captcha fetch failed: HTTP {resp.status}"
                )
            captcha_image = await resp.read()

        # Step 2: OCR the captcha
        ocr = self._get_ocr()
        captcha_text = ocr.classification(captcha_image)
        _LOGGER.debug("OCR result: %s", captcha_text)

        if not captcha_text or len(captcha_text) < 3:
            raise CaptchaError(f"OCR returned unusable text: '{captcha_text}'")

        # Step 3: Call getRoadtax with the same session (JSESSIONID cookie)
        params = {
            "plateNo": plate_number.upper().strip(),
            "vin": vin.upper().strip(),
            "captcha": captcha_text,
        }
        _LOGGER.debug("Calling getRoadtax for plate=%s", plate_number)

        async with session.get(API_URL_GET_ROADTAX, params=params) as resp:
            if resp.status != 200:
                raise ERovignetaAPIError(
                    f"getRoadtax failed: HTTP {resp.status}"
                )
            data = await resp.json()

        # Check for captcha error
        if not data.get("success"):
            message = data.get("message", "Unknown error")
            if "captcha" in message.lower() or "text" in message.lower():
                raise CaptchaError(f"Bad captcha: {message}")
            raise ERovignetaAPIError(f"API error: {message}")

        return data

    async def async_validate(
        self,
        plate_number: str,
        vin: str,
    ) -> bool:
        """
        Validate that we can successfully query the API for this vehicle.

        Used during config flow to verify user input.

        Returns:
            True if the API call succeeded (even if no active vignette found).

        Raises:
            ERovignetaAPIError: On connection or API failure.
        """
        data = await self.async_get_roadtax(plate_number, vin)
        # success=True means the API call worked (even with 0 results)
        return data.get("success", False)
