"""Constants for the easyVerein integration."""

from datetime import timedelta

DOMAIN = "easyverein"
BASE_URL = "https://easyverein.com/api/v3.0/"

UPDATE_INTERVAL = timedelta(minutes=30)
# Tokens expire after 30 days; the server only rotates them in the second half of their lifetime
# and otherwise returns the same key, so refreshing daily is safe.
TOKEN_REFRESH_INTERVAL = timedelta(days=1)

# custom-filter `model` -> API endpoint. Mirrors `filtersToEndpoint` in easyverein-core.
# Filters of any other model (statistics, opos, logs, ...) are skipped.
MODEL_ENDPOINTS = {
    "userFilter": "member",
    "bookingFilter": "booking",
    "addressFilter": "contact-details",
    "invoiceFilter": "invoice",
    "eventFilter": "event",
    "inventoryFilter": "inventory-object",
    "taskFilter": "task",
}
