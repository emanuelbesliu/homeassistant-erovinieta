"""eRovinieta solver service.

Runs the whole portal.etoll.ro vignette check server-side: opens a session,
fetches the image captcha, solves it with ddddocr, and retries on bad
captchas / rate limiting. The Home Assistant integration only sends the
vehicle data and receives the raw search response.
"""

import asyncio
import json
import logging
import os

import ddddocr
from aiohttp import ClientError, ClientSession, ClientTimeout, web

PORTAL = "https://portal.etoll.ro/web/guest/verificare-rovinieta"
PORTLET = (
    "p_p_id=digitalizeportlet_WAR_digitalizeportlet_INSTANCE_xhif"
    "&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view"
    "&p_p_cacheability=cacheLevelPage"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}
MAX_ATTEMPTS = int(os.environ.get("MAX_ATTEMPTS", "12"))
ATTEMPT_DELAY = float(os.environ.get("ATTEMPT_DELAY", "7"))
RATE_LIMIT_DELAY = float(os.environ.get("RATE_LIMIT_DELAY", "20"))

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)-8s %(message)s",
)
log = logging.getLogger("erovinieta-solver")
ocr = ddddocr.DdddOcr(show_ad=False, beta=os.environ.get("OCR_BETA", "1") == "1")
lock = asyncio.Lock()  # one portal session at a time keeps us under the rate limit


async def check(plate: str, vin: str, series: str) -> tuple[int, dict]:
    """Return (http_status, body) for a vehicle check."""
    last = "no attempts made"
    async with ClientSession(
        headers=HEADERS, timeout=ClientTimeout(total=30)
    ) as session:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                if attempt == 1:
                    async with session.get(PORTAL) as r:
                        await r.read()
                async with session.get(
                    f"{PORTAL}?{PORTLET}&rest_path=/api/captcha&rest_method=GET&lang=ro"
                ) as r:
                    image = await r.read()
                code = await asyncio.to_thread(ocr.classification, image)
                payload = {
                    "licensePlateNumber": plate,
                    "vin": vin,
                    "registrationDocumentSeries": series,
                    "startDate": None,
                    "stopDate": None,
                    "captchaCode": code,
                }
                async with session.post(
                    f"{PORTAL}?{PORTLET}&page=0&size=50"
                    "&rest_path=/vignettes/search&rest_method=POST&lang=ro",
                    json=payload,
                ) as r:
                    text = await r.text()
                    status = r.status
            except (ClientError, asyncio.TimeoutError) as err:
                last = f"network error: {err}"
                log.warning("attempt %d/%d: %s", attempt, MAX_ATTEMPTS, last)
                await asyncio.sleep(ATTEMPT_DELAY)
                continue

            try:
                body = json.loads(text)
            except ValueError:
                body = {"raw": text[:500]}

            if status == 200:
                log.info("attempt %d: OK for %s", attempt, plate)
                return 200, {"success": True, "data": body}
            message = body.get("message", "") if isinstance(body, dict) else ""
            last = f"HTTP {status}: {message}"
            log.info("attempt %d/%d: captcha=%r -> %s", attempt, MAX_ATTEMPTS, code, last)
            if status == 429:
                await asyncio.sleep(RATE_LIMIT_DELAY)
            elif status == 400 and "captcha" in message.lower():
                await asyncio.sleep(ATTEMPT_DELAY)
            else:
                # Captcha was accepted; this is a genuine portal answer.
                return status, {"success": False, "message": message, "body": body}
    return 503, {"success": False, "message": f"captcha not solved: {last}"}


async def handle_check(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        plate = str(data["plate"]).upper().strip()
        vin = str(data["vin"]).upper().strip()
        series = str(data["series"]).upper().strip()
    except (ValueError, KeyError):
        return web.json_response(
            {"success": False, "message": "plate, vin and series required"},
            status=400,
        )
    async with lock:
        status, body = await check(plate, vin, series)
    return web.json_response(body, status=status)


async def handle_health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


app = web.Application()
app.router.add_post("/check", handle_check)
app.router.add_get("/health", handle_health)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8195")), access_log=None)
