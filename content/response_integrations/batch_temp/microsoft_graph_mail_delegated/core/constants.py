from __future__ import annotations
from enum import Enum

INTEGRATION_NAME = "MicrosoftGraphMailDelegated"
VENDOR = "Microsoft"
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"
SEND_THREAD_REPLY = f"{INTEGRATION_NAME} - Send Thread Reply"
FORWARD_EMAIL_SCRIPT_NAME = f"{INTEGRATION_NAME} - Forward Email"
WAIT_FOR_MAIL_FROM_USER_SCRIPT_NAME = f"{INTEGRATION_NAME} - Wait for Email from User"
SEARCH_EMAILS_SCRIPT_NAME = f"{INTEGRATION_NAME} - Search Emails"
SEND_EMAIL_SCRIPT_NAME = f"{INTEGRATION_NAME} - Send Email"
SEND_VOTE_EMAIL_NAME = f"{INTEGRATION_NAME} - Send Vote Email"
SEND_EMAIL_HTML_NAME = f"{INTEGRATION_NAME} - Send Email HTML"
DELETE_EMAIL_SCRIPT_NAME = f"{INTEGRATION_NAME} - Delete Email"
MOVE_EMAIL_TO_FOLDER_SCRIPT_NAME = f"{INTEGRATION_NAME} - Move Email to Folder"
SAVE_EMAIL_TO_CASE_SCRIPT_NAME = f"{INTEGRATION_NAME} - Save Email to Case"
WAIT_FOR_VOTE_EMAIL_RESULTS_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Wait For Vote Email Results"
)
DOWNLOAD_ATTACHMENTS_FROM_EMAIL = (
    f"{INTEGRATION_NAME} - Download Attachments From Email"
)
EXTRACT_EML_DATA_SCRIPT_NAME = f"{INTEGRATION_NAME} - Extract Data from Attached EML"
MARK_EMAIL_AS_JUNK_SCRIPT_NAME = f"{INTEGRATION_NAME} - Mark Email as Junk"
MARK_EMAIL_AS_NOT_JUNK_SCRIPT_NAME = f"{INTEGRATION_NAME} - Mark Email as Not Junk"
RUN_MICROSOFT_SEARCH_QUERY_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Run Microsoft Search Query"
)
GENERATE_TOKEN_SCRIPT_NAME = f"{INTEGRATION_NAME} - Generate Token"
GET_AUTHORIZATION_SCRIPT_NAME = f"{INTEGRATION_NAME} - Get Authorization"
GET_MAILBOX_ACCOUNT_OUT_OF_FACILITY_SETTINGS_SCRIPT_NAME = (
    f"{INTEGRATION_NAME} - Get Mailbox Account Out Of Facility Settings"
)
TOKEN_RENEWAL_SCRIPT_NAME = f"{INTEGRATION_NAME} - Refresh Token Renewal Job"

OAUTH_SCOPE = [
    "mail.read",
    "mail.send",
    "mail.readwrite",
    "mailboxsettings.read",
    "mailboxsettings.readwrite",
    "user.read",
    "directory.read.all",
    "presence.read.all",
    "offline_access",
]
DEFAULT_REDIRECT_URL = "http://localhost"

API_VERSION = "v1.0"
ENDPOINTS = {
    "access_token_url": "{tenant}/oauth2/v2.0/token",
    "authorize_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
    "batch_request": f"{API_VERSION}/$batch",
    "list_users": f"{API_VERSION}/{{tenant}}/users",
    "list_user": f"{API_VERSION}/{{tenant}}/users/{{mail_address}}",
    "create_draft": f"{API_VERSION}/{{tenant}}/users/{{mail_address}}/messages",
    "get_emails_with_filter": f"{API_VERSION}/users/{{mail_address}}/messages",
    "get_folders": f"{API_VERSION}/{{tenant}}/users/{{mail_address}}/mailFolders",
    "get_child_folders": (
        f"{API_VERSION}/{{tenant}}/users/{{mail_address}}/mailFolders/{{folder_id}}"
        "/childFolders"
    ),
    "get_emails": (
        f"{API_VERSION}/{{tenant}}/users/{{mail_address}}/mailFolders/{{folder_id}}"
        "/messages"
    ),
    "relative_email_details": (
        f"{API_VERSION}/{{tenant}}/users/{{mail_address}}/mailFolders/{{folder_id}}"
        "/messages/{email_id}"
    ),
    "send_email": (
        f"{API_VERSION}/{{tenant}}/users/{{mail_address}}/messages/{{email_id}}/send"
    ),
    "move_email_to_folder": (
        f"{API_VERSION}/{{tenant}}/users/{{mail_address}}/mailFolders/{{folder_id}}/"
        "messages/{email_id}/move"
    ),
    "create_forward_draft": (
        f"{API_VERSION}/{{tenant}}/users/{{mail_address}}/messages/{{email_id}}/"
        "createForward"
    ),
    "create_thread_draft": (
        f"{API_VERSION}/{{tenant}}/users/{{mail_address}}/messages/{{email_id}}/"
        "createReply"
    ),
    "get_attachments": (
        f"{API_VERSION}/{{tenant}}/users/{{mail_address}}/mailFolders/{{folder_id}}/"
        "messages/{email_id}"
        "/attachments"
    ),
    "get_attachments_content": (
        f"{API_VERSION}/{{tenant}}/users/{{mail_address}}/mailFolders/{{folder_id}}/"
        "messages/{email_id}/attachments/{attachment_id}/$value"
    ),
    "get_email_content": (
        f"{API_VERSION}/{{tenant}}/users/{{mail_address}}/messages/{{email_id}}/$value"
    ),
    "mark_as_junk": (
        "beta/{tenant}/users/{mail_address}/mailFolders/{folder_name}/"
        "messages/{email_id}/microsoft.graph.markAsJunk"
    ),
    "mark_as_not_junk": (
        "beta/{tenant}/users/{mail_address}/mailFolders/{folder_name}/"
        "messages/{email_id}/microsoft.graph.markAsNotJunk"
    ),
    "get_oof_settings": ("beta/communications/presences/{user_id}"),
    "search_query": f"{API_VERSION}/search/query"
}

HEADERS = {"Content-Type": "application/json"}
GRANT_TYPE = "refresh_token"
SCOPE = "https://graph.microsoft.com/.default"

# Access consts
TOKEN_PAYLOAD_FROM_SECRET = {
    "grant_type": GRANT_TYPE,
    "client_id": "",
    "scope": SCOPE,
    "client_secret": "",
    "refresh_token": ""
}

SUCCESS_STATUS_CODES = [200, 201, 202]
PER_REQUEST_ENTITIES_LIMIT = 10
STORED_IDS_LIMIT = 3000
CASE_NAME_PATTERN = "Microsoft Graph Monitored Mailbox <{}>"
PRIORITY_DEFAULT = 40
PLACEHOLDER_START = "["
PLACEHOLDER_END = "]"
KEYS_TO_EXCEPT_ON_TRANSFORMATION = [
    "device_product",
    "device_vendor",
    "event_name",
    "monitored_mailbox_name",
    "email_folder",
    "original_email_id",
]
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

ASYNC_TIMEOUT_THRESHOLD_IN_MS = 60000
TIMEOUT_SECONDS = 60
TIME_FRAME_THRESHOLD = 0
TIME_INTERVAL = 10
DEFAULT_BATCH_SIZE = 25
CASE_TABLE_NAME = "Matching Mails"
DEFAULT_MAILBOX = "Default Mailbox"
DEFAULT_FOLDER_NAME = "Inbox"
DEFAULT_JUNK_FOLDER_NAME = "Junk Email"
DEFAULT_SENT_FOLDER_NAME = "Sent Items"
DEFAULT_MAIL_CONTENT_TYPE = "Text"
DEFAULT_EMAIL_HTML_TEMPLATE = "Email HTML Template"
DEFAULT_VOTING_OPTION = "Yes/No"
DEFAULT_FILE_LOCATION = "GCP Bucket"
EMPTY_EMAIL_SUBJECT = "Unnamed"
EMPTY_SUBJECT = "Empty subject"
UNKNOWN_SENDER = "Unknown sender"
ID_ERROR = "id is malformed"
NOT_FOUND_ERROR = "the specified object was not found in the store."
FOLDER_ERROR = "Mail folder \"{folder_name}\" does not exist"
MAILBOX_NOT_FOUND_ERROR = (
    "the mailbox is either inactive, soft-deleted, or is hosted on-premise."
)
MAILBOX_DOES_NOT_EXIST_ERROR = (
    "Resource '{mail_address}' does not exist or one of its queried reference-property "
    "objects are not present."
)
MAIL_CONTENT_TYPE = {"Text": "Text", "Html": "Html"}
DOWNLOAD_DESTINATION = ["GCP Bucket", "Local File System"]
REPLY_ALL = "All"

ATTACHED_EMAIL_EVENT_NAME = "Attached Email File"
DEVICE_PRODUCT = "Graph Mail"
EMAIL_LIST_FIELDS = ["toRecipients", "ccRecipients", "bccRecipients", "replyTo"]
ORIGINAL_EMAIL_EVENT_NAME = "Email Received in Monitoring Mailbox"
MAX_FILE_SIZE = 15_728_640
MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024
MAX_RESULTS_LIMIT = 999
BATCH_RATE_LIMIT = 20
SINGLE_EXTENDED_PROPERTY_VALUE = "String 0x007D"
ETAG_VALUE = "@odata.etag"
CONTEXT_VALUE = "@odata.context"
SRC_FOLDER = "source"
DST_FOLDER = "destination"
UNKNOWN_FILE_NAME: str = "unknown_filename"
DEFAULT_CONTENT_TYPE = "text"
TEXT_CONTENT_TYPE = ["text/plain", DEFAULT_CONTENT_TYPE]
SUBFOLDER_DELIMITER = "/"
SUB_FOLDER_KEY = "childFolderCount"
ENCODED_VOTING_OPTIONS = {
    "Approve/Reject": "AgEGAAAAAAAAAAVSZXBseQhJUE0uTm90ZQdNZXNzYWdlAlJFBQAAAAAAAAAAAQA"
    "AAAAAAAACAAAAZgAAAAIAAAABAAAADFJlcGx5IHRvIEFsbAhJUE0uTm90ZQdNZXNzYWdlAlJFBQAAAAAA"
    "AAAAAQAAAAAAAAACAAAAZwAAAAMAAAACAAAAB0ZvcndhcmQISVBNLk5vdGUHTWVzc2FnZQJGVwUAAAAAAA"
    "AAAAEAAAAAAAAAAgAAAGgAAAAEAAAAAwAAAA9SZXBseSB0byBGb2xkZXIISVBNLlBvc3QEUG9zdAAFAAAA"
    "AAAAAAABAAAAAAAAAAIAAABsAAAACAAAAAQAAAAHQXBwcm92ZQhJUE0uTm90ZQAHQXBwcm92ZQAAAAAAAA"
    "AAAAEAAAACAAAAAgAAAAEAAAD/////BAAAAAZSZWplY3QISVBNLk5vdGUABlJlamVjdAAAAAAAAAAAAAEA"
    "AAACAAAAAgAAAAIAAAD/////BAEFUgBlAHAAbAB5AAJSAEUADFIAZQBwAGwAeQAgAHQAbwAgAEEAbABsAA"
    "JSAEUAB0YAbwByAHcAYQByAGQAAkYAVwAPUgBlAHAAbAB5ACAAdABvACAARgBvAGwAZABlAHIAAAdBAHAA"
    "cAByAG8AdgBlAAdBAHAAcAByAG8AdgBlAAZSAGUAagBlAGMAdAAGUgBlAGoAZQBjAHQA",
    "Yes/No": "AgEGAAAAAAAAAAVSZXBseQhJUE0uTm90ZQdNZXNzYWdlAlJFBQAAAAAAAAAAAQAAAAAAAAA"
    "CAAAAZgAAAAIAAAABAAAADFJlcGx5IHRvIEFsbAhJUE0uTm90ZQdNZXNzYWdlAlJFBQAAAAAAAAAAAQAAA"
    "AAAAAACAAAAZwAAAAMAAAACAAAAB0ZvcndhcmQISVBNLk5vdGUHTWVzc2FnZQJGVwUAAAAAAAAAAAEAAAA"
    "AAAAAAgAAAGgAAAAEAAAAAwAAAA9SZXBseSB0byBGb2xkZXIISVBNLlBvc3QEUG9zdAAFAAAAAAAAAAABA"
    "AAAAAAAAAIAAABsAAAACAAAAAQAAAADWWVzCElQTS5Ob3RlAANZZXMAAAAAAAAAAAABAAAAAgAAAAIAAAA"
    "BAAAA/////wQAAAACTm8ISVBNLk5vdGUAAk5vAAAAAAAAAAAAAQAAAAIAAAACAAAAAgAAAP////8EAQVSA"
    "GUAcABsAHkAAlIARQAMUgBlAHAAbAB5ACAAdABvACAAQQBsAGwAAlIARQAHRgBvAHIAdwBhAHIAZAACRgB"
    "XAA9SAGUAcABsAHkAIAB0AG8AIABGAG8AbABkAGUAcgAAA1kAZQBzAANZAGUAcwACTgBvAAJOAG8A",
}
VOTING_OPTIONS_ID = "Binary {00062008-0000-0000-c000-000000000046} Id 0x8520"

# Consts for siemplify html template parsing
HTML_IMAGE_TAG = "cstimage"
HTML_IMAGE_TAG_NAME_ATTR = "cid"
HTML_IMAGE_TAG_BASE64_ATTR = "base64image"
EMPTY_HTML_CONTENT_BODY = "<html><body></body></html>"

EML_TYPES = ["application/octet-stream", "message/rfc822"]
VOTING_OPTIONS = ["Yes", "No", "Approve", "Reject"]
URLS_REGEX = (
    r"(?i)\[?(?:(?:(?:http|https)(?:://))|www\.(?!://))(?:[a-zA-Z0-9\-\._~:;/\?#\[\]@!"
    r"\$&'\(\)\*\+,=%])+"
)
DEFAULT_REGEX_MAP = {
    "urls": URLS_REGEX,
    "subject": r"(?<=Subject: ).*",
    "from_list": r"(?<=From: ).*",
    "to": r"(?m)(?<=^To: ).*",
}
DEFAULT_URLS_LIST_DELIMITER = "|"
EAIML_EXTENSION = [".eml", ".ics", ".msg"]
DEFAULT_CHARSET = "utf-8"
DEFAULT_LIST_DELIMITER = ";"
DEFAULT_REGEX_MAP = {
    "urls": URLS_REGEX,
    "subject": r"(?<=Subject: ).*",
    "from_list": r"(?<=From: ).*",
    "to": r"(?m)(?<=^To: ).*",
}
GCP_FILE_NOT_FOUND_ERR = "internal server error for url:"
EML_ATTACHMENT_DESCRIPTION = "This is the original message as EML"
ATTACHMENT_EXTENSION = ".eml"
MESSAGE_ID_PATTERN = r"^[A-Za-z0-9-_=]+$"
ATTACHMENT_SUFFIXES = (".eml", ".msg", ".ics")
LOCALE_TRANSLATIONS = {
    "Inbox": [
        "Posteingang",
        "Inbox",
        "Bandeja de entrada",
        "Boîte de réception",
        "Posta in arrivo",
        "受信トレイ",
        "받은 편지함",
        "Skrzynka odbiorcza",
        "Caixa de entrada",
        "收件箱",
        "收件匣",
    ],
    "Sent Items": [
        "Gesendete Elemente",
        "Sent Items",
        "Elementos enviados",
        "Éléments envoyés",
        "Posta inviata",
        "送信済みアイテム",
        "보낸 편지함",
        "Elementy wysłane",
        "Itens enviados",
        "已发送邮件",
        "寄件備份",
    ],
    "Drafts": [
        "Entwürfe",
        "Drafts",
        "Borradores",
        "Brouillons",
        "Bozze",
        "下書き",
        "임시 보관함",
        "Wersje robocze",
        "Rascunhos",
        "草稿",
        "草稿",
    ],
    "Deleted Items": [
        "Gelöschte Elemente",
        "Deleted Items",
        "Elementos eliminados",
        "Éléments supprimés",
        "Posta indesiderata",
        "削除済みアイテム",
        "삭제된 항목",
        "Elementy usunięte",
        "Itens excluídos",
        "已删除邮件",
        "已刪除的項目",
    ],
    "Junk Email": [
        "unerwünschte E-Mails",
        "Junk Email",
        "Correo no deseado",
        "Courrier indésirable",
        "Posta indesiderata",
        "迷惑メール",
        "스팸 메일",
        "Wiadomości-śmieci",
        "Lixo Eletrônico",
        "垃圾邮件",
        "垃圾郵件",
    ],
}
FILE_ATTACHMENT_ODATA_TYPE = "#microsoft.graph.fileAttachment"
SUPPORTED_ENTITY_TYPES: list[str] = [
    "event",
    "message",
    "driveItem",
    "externalItem",
    "site",
    "list",
    "listItem",
    "drive",
    "chatMessage",
    "person",
    "acronym",
    "bookmark",
]
DELEGATION_PERMISSION_ERR: str = (
    "the specified object was not found in the store., default folder root not found."
)
FAILURE_STATUS_CODE: int = 400
HTTP_STATUS_UNAUTHORIZED: int = 401
DEFAULT_SEARCH_SIZE: int = 25
REFRESH_TOKEN_ERR_CODE: int = 9002313
INVALID_CLIENT_ID_ERR_CODE: int = 70000
INVALID_TENANT_ID_ERR_CODE: int = 90002
INVALID_CLIENT_SECRET_ERR_CODE: int = 7000215
SMIME_ATTACHMENT_CONTENT_TYPES = [
    "application/pkcs7-mime",
    "multipart/signed",
    "application/x-pkcs7-mime",
    "application/pkcs7-signature",
]
EVENT_ATTACHMENT_CONTENT_TYPE_MAP = {
    ".eml": "message/rfc822",
    ".msg": "application/vnd.ms-outlook",
    ".ics": "text/calendar",
}

DEFAULT_MAX_RETRIES: int = 5
DEFAULT_RETRY_AFTER: int = 1
EXPONENTIAL_BACKOFF_BASE: int = 2
SERVICE_UNAVAILABLE: int = 503
DECREMENT: int = 1

HTTP_RETRY_TOTAL: int = 3
HTTP_RETRY_BACKOFF_FACTOR: int = 2
HTTP_RETRY_STATUS_CODES: list[int] = [502, 503, 504]


class SmimeType(Enum):
    ENCRYPTED = "encrypted"
    SIGNED = "signed"
