from __future__ import annotations
INTEGRATION_NAME = "AWSS3"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
REGEX_BUCKET_PATH = r"^s3://([^/]+)/(.*?([^/]+)/?)$"  # regex for bucket file path
