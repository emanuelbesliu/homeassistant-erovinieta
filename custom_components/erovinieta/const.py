"""Constants for the eRovinieta integration."""

DOMAIN = "erovinieta"

# API
API_BASE_URL = "https://erovinieta.ro/vignettes-portal-web"
API_URL_CAPTCHA = f"{API_BASE_URL}/rest/anonymous/generateCaptchaImage"
API_URL_GET_ROADTAX = f"{API_BASE_URL}/rest/anonymous/roadTax/getRoadtax"

# Configuration keys
CONF_PLATE_NUMBER = "plate_number"
CONF_VIN = "vin"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_EXPIRY_WARNING_DAYS = "expiry_warning_days"

# Defaults
DEFAULT_UPDATE_INTERVAL = 86400  # 24 hours in seconds (once daily)
MIN_UPDATE_INTERVAL = 3600  # 1 hour
MAX_UPDATE_INTERVAL = 604800  # 7 days
DEFAULT_EXPIRY_WARNING_DAYS = 14

# Captcha
MAX_CAPTCHA_RETRIES = 5

# Event name
EVENT_EXPIRING_SOON = "erovinieta_expiring_soon"

# Attribution
ATTRIBUTION = "Data provided by erovinieta.ro (CNAIR Romania)"
