from __future__ import annotations
SCOPE = (
    "https://www.googleapis.com/auth/devstorage.full_control",
    "https://www.googleapis.com/auth/devstorage.read_only",
    "https://www.googleapis.com/auth/devstorage.read_write",
)

INTEGRATION_NAME = "GoogleCloudStorage"
INTEGRATION_DISPLAY_NAME = "Google Cloud Storage"

#  Actions names
PING = "Ping"
LIST_BUCKETS = "List Buckets"
GET_BUCKETS_ACLS = "Get a Bucket’s Access Control List"
LIST_BUCKET_OBJECTS = "List Bucket Objects"
UPDATE_AN_ACL_ENTRY_ON_BUCKET = "Update an ACL entry on Bucket"
DOWNLOAD_OBJECT_FROM_BUCKET = "Download an Object From a Bucket"
UPLOAD_OBJECT_TO_BUCKET = "Upload an Object To a Bucket"
REMOVE_PUBLIC_ACCESS_FROM_BUCKET = "Remove Public Access From Bucket"

#  HTTP responses codes
SUCCESS_REQUEST = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404

DEFAULT_PAGE_SIZE = 50
MIN_LIST_SIZE = 1

ROLES_MAPPER = {"OWNER": "grant_owner", "WRITER": "grant_write", "READER": "grant_read"}

OWNER = "OWNER"
WRITER = "WRITER"
READER = "READER"

ROLES_LEVEL = {"OWNER": 2, "WRITER": 1, "READER": 0}

REVERSE_ROLES_LEVEL = {2: "OWNER", 1: "WRITER", 0: "READER"}

# Entities
USER = "user-"
GROUP = "group-"
ALL_USERS = "allUsers"
ALL_AUTHENTICATED_USER = "allAuthenticatedUsers"

DEFAULT_PATH = "/{folder_1}/{folder_2}/{filename}"
PUBLIC_ACCESS_PRINCIPALS = [ALL_USERS, ALL_AUTHENTICATED_USER]
