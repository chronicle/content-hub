from __future__ import annotations
import json
from integration_testing.common import get_def_file_content
import pathlib

from TIPCommon.types import SingleJson

from integration_testing.common import get_def_file_content


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)

MOCK_DATA_PATH = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA = get_def_file_content(MOCK_DATA_PATH)

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent

DEFAULT_SA: str = (
    "{\n"
    '  "type": "service_account",\n'
    '  "project_id": "project",\n'
    '  "private_key_id": "c9",\n'
    '  "private_key": "-----BEGIN PRIVATE KEY-----key-----'
    'END PRIVATE KEY-----",\n'
    '  "client_email": "email@domain.iam.gserviceaccount.com",\n'
    '  "client_id": "id",\n'
    '  "auth_uri": "https://accounts.google.com/o/oauth2/auth",\n'
    '  "token_uri": "https://oauth2.googleapis.com/token",\n'
    '  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/'
    'certs",\n'
    '  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/'
    'x509/project.iam.gserviceaccount.com",\n'
    '  "universe_domain": "googleapis.com"\n'
    "}"
)
