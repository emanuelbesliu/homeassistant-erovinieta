"""API client for eRovinieta (portal.etoll.ro).

The portal protects its public vignette search with a rotated, distorted
captcha. Solving it needs OCR that is too heavy for Home Assistant, so the
work is delegated to the ``erovinieta-solver`` service (see ``solver-service/``).
"""

import logging
from typing import Any

import aiohttp

from .const import SOLVER_TIMEOUT
from .exceptions import (
    ERovignetaAPIError,
    ERovignetaCaptchaError,
    ERovignetaConnectionError,
)

_LOGGER = logging.getLogger(__name__)

# Keep backward-compatible alias so existing imports still work
CaptchaError = ERovignetaCaptchaError


class ERovignetaAPI:
    """Async client for the erovinieta solver service."""

    def __init__(self, solver_url: str) -> None:
        """Initialize with the solver service base URL."""
        self._solver_url = solver_url.rstrip("/")

    async def async_get_roadtax(
        self,
        plate_number: str,
        vin: str,
        series: str,
        session: aiohttp.ClientSession | None = None,
    ) -> dict[str, Any]:
        """Fetch vignette data for a vehicle.

        Raises:
            ERovignetaConnectionError: solver unreachable or captcha not solved.
            ERovignetaAPIError: the portal rejected the vehicle data.
        """
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()

        payload = {
            "plate": plate_number.upper().strip(),
            "vin": vin.upper().strip(),
            "series": series.upper().strip(),
        }
        try:
            async with session.post(
                f"{self._solver_url}/check",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=SOLVER_TIMEOUT),
            ) as resp:
                try:
                    data = await resp.json(content_type=None)
                except ValueError:
                    data = {}
                if resp.status == 200 and data.get("success"):
                    return data
                message = data.get("message") or f"HTTP {resp.status}"
                if resp.status in (429, 503):
                    raise ERovignetaConnectionError(message)
                raise ERovignetaAPIError(message)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise ERovignetaConnectionError(
                f"Solver service unreachable at {self._solver_url}: {err}"
            ) from err
        finally:
            if own_session:
                await session.close()

    async def async_validate(self, plate_number: str, vin: str, series: str) -> bool:
        """Validate the vehicle data against the portal (used by the config flow)."""
        data = await self.async_get_roadtax(plate_number, vin, series)
        return data.get("success", False)
