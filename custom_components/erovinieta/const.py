"""Constants for the eRovinieta integration."""

DOMAIN = "erovinieta"

# Configuration keys
CONF_PLATE_NUMBER = "plate_number"
CONF_VIN = "vin"
CONF_SERIES = "registration_series"
CONF_SOLVER_URL = "solver_url"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_EXPIRY_WARNING_DAYS = "expiry_warning_days"

# Defaults
DEFAULT_UPDATE_INTERVAL = 86400  # 24 hours in seconds (once daily)
MIN_UPDATE_INTERVAL = 3600  # 1 hour
MAX_UPDATE_INTERVAL = 604800  # 7 days
DEFAULT_EXPIRY_WARNING_DAYS = 14

DEFAULT_SOLVER_URL = "http://10.0.102.10:8195"
SOLVER_TIMEOUT = 300  # solver retries captchas internally and can take minutes

# Event name
EVENT_EXPIRING_SOON = "erovinieta_expiring_soon"

# Attribution
ATTRIBUTION = "Data provided by portal.etoll.ro (CNAIR Romania)"
