from __future__ import annotations
INTEGRATION_IDENTIFIER = "VaronisDataSecurityPlatform"

UPDATE_ALERT_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Update Alert"
STORED_IDS_LIMIT = 3000
VENDOR_NAME = "Varonis"
PRODUCT_NAME = "Data Security Platform"
ALERT_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
EVENT_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
SEVERITY_MAPIING = {"Low": 40, "Medium": 60, "High": 80}
LAST_DAYS = "lastdays"
ALERT_SEQ_ID_DEFAULT = 0
ALERT_SEQ_ID_WITH_TIME = "alertseqid"
ALERT_SEQ_ID_INDEX = 0
ALERT_TIMESTAMP_INDEX = 1
ALERT_DAY_FORMAT = "%Y%m%d"
