
INTEGRATION_IDENTIFIER: str = "CheckPointHEC"
INTEGRATION_DISPLAY_NAME: str = "Check Point HEC"

SMART_API_VERSION = "v1.0"

# Sectools
ANTI_MALWARE_SAAS_NAME = "checkpoint2"
AVANAN_URL_SAAS_NAME = "avanan_url"
AVANAN_DLP_SAAS_NAME = "avanan_dlp"

# Script names
CREATE_ANOMALY_EXC_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Create Anomaly Exception"
CREATE_AP_EXC_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Create Anti-Phishing Exception"
CREATE_AVDLP_EXC_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Create Avanan DLP Exception"
CREATE_AVURL_EXC_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Create Avanan URL Exception"
CREATE_CP2_EXC_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Create Anti-Malware Exception"
CREATE_CTP_LIST_ITEM_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Create CTP List Item"

DELETE_ANOMALY_EXCS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Delete Anomaly Exceptions"
DELETE_AP_EXC_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Delete Anti-Phishing Exception"
DELETE_AVDLP_EXC_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Delete Avanan DLP Exception"
DELETE_AVDLP_EXCS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Delete Avanan DLP Exceptions"
DELETE_AVURL_EXC_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Delete Avanan URL Exception"
DELETE_AVURL_EXCS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Delete Avanan URL Exceptions"
DELETE_CP2_EXC_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Delete Anti-Malware Exception"
DELETE_CP2_EXCS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Delete Anti-Malware Exceptions"
DELETE_CTP_LIST_ITEM_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Delete CTP List Item"
DELETE_CTP_LIST_ITEMS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Delete CTP List Items"
DELETE_CTP_LISTS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Delete CTP Lists"

DOWNLOAD_EMAIL_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Download Email"
GET_ACTION_RESULT_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get Action Result"

GET_ANOMALY_EXCS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get Anomaly Exceptions"
GET_AP_EXCS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get Anti-Phishing Exceptions"
GET_AVDLP_EXC_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get Avanan DLP Exception"
GET_AVDLP_EXCS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get Avanan DLP Exceptions"
GET_AVURL_EXC_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get Avanan URL Exception"
GET_AVURL_EXCS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get Avanan URL Exceptions"
GET_CP2_EXC_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get Anti-Malware Exception"
GET_CP2_EXCS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get Anti-Malware Exceptions"
GET_CTP_LIST_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get CTP List"
GET_CTP_LIST_ITEM_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get CTP List Item"
GET_CTP_LIST_ITEMS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get CTP List Items"
GET_CTP_LISTS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get CTP Lists"

GET_ENTITY_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get Entity"
GET_EVENTS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get Events"
GET_SCAN_INFO_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Get Scan Info"
PING_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Ping"
REPORT_MIS_CLASSIFICATION_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Report Mis-classification"
SEARCH_EMAILS_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Search Emails"
SEND_ACTION_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Send Action"

UPDATE_AP_EXC_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Update Anti-Phishing Exception"
UPDATE_AVDLP_EXC_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Update Avanan DLP Exception"
UPDATE_AVURL_EXC_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Update Avanan URL Exception"
UPDATE_CP2_EXC_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Update Anti-Malware Exception"
UPDATE_CTP_LIST_ITEM_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Update CTP List Item"

DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# Maps
CP_DETECTION_VALUES = {
    "Phishing": "cp_phishing",
    "Suspected Phishing": "cp_ap_suspicious",
    "Malware": "cp_malicious",
    "Suspected Malware": "cp_av_suspicious",
    "Spam": "cp_spam",
    "Clean": "cp_clean",
    "DLP": "cp_leak",
    "Malicious URL Click": "cp_malicious_url_click",
    "Malicious URL": "cp_malicious_url",
}
MS_DETECTION_VALUES = {
    "Malware": "ms_malware",
    "High Confidence Phishing": "ms_high_confidence_phishing",
    "Phishing": "ms_phishing",
    "High Confidence Spam": "ms_high_confidence_spam",
    "Spam": "ms_spam",
    "Bulk": "ms_bulk",
    "Clean": "ms_clean",
}
CP_QUARANTINED_VALUES = {
    "Quarantined (Any source)": "all",
    "Not Quarantined": "cp_not_quarantined",
    "Quarantined by Check Point": "cp_quarantined_by_cp",
    "Quarantined by CP Analyst": "cp_quarantined_by_analyst",
    "Quarantined by Admin": "cp_quarantined_by_admin",
}
MS_QUARANTINED_VALUES = {
    "Quarantined": "ms_quarantined",
    "Not Quarantined": "ms_not_quarantined",
    "Not Quarantined Delivered to Inbox": "ms_delivered_inbox",
    "Not Quarantined Delivered to Junk": "ms_delivered_junk",
}
MIS_CLASSIFICATION_CONFIDENCE = {
    "Not so sure": "not_so_sure",
    "Medium Confidence": "medium",
    "High Confidence": "very",
}
MIS_CLASSIFICATION_OPTIONS = {
    "Clean Email": "clean",
    "Spam": "spam",
    "Phishing": "phishing",
    "Legit Marketing Email": "marketing_email",
}
SAAS_APPS_TO_SAAS_NAMES = {
    "Microsoft Exchange": "office365_emails",
    "Gmail": "google_mail"
}
SEVERITY_VALUES = {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "low": 2,
    "very low": 1
}
