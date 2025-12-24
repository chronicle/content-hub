from __future__ import annotations

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GoogleDocsManager:
    """GoogleDocs Manager."""

    def __init__(self, cred_json_content):
        f = open("credentials.json", "w+")
        f.write(cred_json_content)
        f.close()
        credentials = service_account.Credentials.from_service_account_file(
            "credentials.json",
            scopes=SCOPES,
        )
        self._doc_service = build("docs", "v1", credentials=credentials)
        self._drive_service = build("drive", "v3", credentials=credentials)

    def test_connectivity(self):
        _ = (
            self._drive_service.files()
            .list(
                q="mimeType='image/jpeg'",
                spaces="drive",
                fields="nextPageToken, files(id, name)",
                pageToken=None,
            )
            .execute()
        )

    def __insert_permission__(self, file_id, role, user_emails_to_add):
        emails = user_emails_to_add.split(";")
        for email in emails:
            user_permission = {"type": "user", "role": role, "emailAddress": email}
            self._drive_service.permissions().create(
                fileId=file_id,
                body=user_permission,
                fields="id",
                sendNotificationEmail=False,
            ).execute()

    def create_document(self, title, role, emails):
        body = {"title": title}
        res = self._doc_service.documents().create(body=body, fields="*").execute()
        file_id = res["documentId"]
        self.__insert_permission__(file_id, role, emails)
        file_metadata_json = (
            self._drive_service.files().get(fileId=file_id, fields="*").execute()
        )
        return file_metadata_json

    def execute_request(self, document_id, requests_obj):
        result = (
            self._doc_service.documents()
            .batchUpdate(documentId=document_id, body={"requests": requests_obj})
            .execute()
        )
        return result
