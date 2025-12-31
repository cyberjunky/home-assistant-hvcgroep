"""Constants for the HVC Groep integration."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "hvcgroep"

# Configuration keys
CONF_POSTAL_CODE: Final = "postal_code"
CONF_HOUSE_NUMBER: Final = "house_number"

# API URLs
BAGID_URL: Final = "https://apps.hvcgroep.nl/rest/adressen/{0}-{1}"
WASTE_URL: Final = "https://apps.hvcgroep.nl/rest/adressen/{0}/afvalstromen"

# Default scan interval in seconds (1 hour)
DEFAULT_SCAN_INTERVAL: Final = 3600

# Garbage type definitions with HVC API IDs
GARBAGE_TYPES: Final = {
    "gft": {
        "id": 5,
        "icon": "mdi:food-apple-outline",
        "translation_key": "gft",
    },
    "plastic": {
        "id": 6,
        "icon": "mdi:recycle",
        "translation_key": "plastic",
    },
    "papier": {
        "id": 3,
        "icon": "mdi:file",
        "translation_key": "papier",
    },
    "restafval": {
        "id": 2,
        "icon": "mdi:delete-empty",
        "translation_key": "restafval",
    },
    "reiniging": {
        "id": 59,
        "icon": "mdi:liquid-spot",
        "translation_key": "reiniging",
    },
}

# Reverse lookup: API ID to garbage type key
GARBAGE_ID_TO_TYPE: Final = {v["id"]: k for k, v in GARBAGE_TYPES.items()}
