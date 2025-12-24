from __future__ import annotations

import base64
import io
import os
from base64 import b64decode

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload

SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]


class GoogleDriveManager:
    """GoogleDoc Manager"""

    def __init__(self, cred_json_content):
        f = open("credentials.json", "w+")
        f.write(cred_json_content)
        f.close()
        credentials = service_account.Credentials.from_service_account_file(
            "credentials.json",
            scopes=SCOPES,
        )
        self._service = build("drive", "v3", credentials=credentials)

    def test_connectivity(self):
        response = (
            self._service.files()
            .list(
                q="mimeType='image/jpeg'",
                spaces="drive",
                fields="nextPageToken, files(id, name)",
                pageToken=None,
            )
            .execute()
        )

    def create_folder(self, folder_name):
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        data = self._service.files().create(body=file_metadata, fields="*").execute()
        return data

    def list_permissions(self, file_id):
        """Retrieve a list of permissions.

        Args:
          file_id: ID of the file to retrieve permissions for.

        Returns:
          List of permissions.

        """
        permissions = (
            self._service.permissions().list(fileId=file_id, fields="*").execute()
        )
        return permissions["permissions"]

    def export_file(self, file_id, path_to_save, mimetype):
        binary_stream = io.BytesIO()
        request = self._service.files().export_media(fileId=file_id, mimeType=mimetype)
        downloader = MediaIoBaseDownload(binary_stream, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        with open(path_to_save, "wb") as f:
            f.write(binary_stream.getvalue())
        binary_stream.close()

    def _get_binary_stream_from_file(self, file_id, file_metadata_json):
        if file_metadata_json["mimeType"] == "application/vnd.google-apps.document":
            request = self._service.files().export_media(
                fileId=file_id,
                mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        elif (
            file_metadata_json["mimeType"] == "application/vnd.google-apps.presentation"
        ):
            request = self._service.files().export_media(
                fileId=file_id,
                mimeType="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )

        elif (
            file_metadata_json["mimeType"] == "application/vnd.google-apps.spreadsheet"
        ):
            request = self._service.files().export_media(
                fileId=file_id,
                mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        else:
            request = self._service.files().get_media(fileId=file_id)

        binary_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(binary_stream, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

        return binary_stream

    def download_file_to_path(self, file_id, folder_to_save):
        file_metadata_json = (
            self._service.files().get(fileId=file_id, fields="*").execute()
        )

        return_value = {}
        return_value["name"] = file_metadata_json["name"]
        return_value["type"] = file_metadata_json["mimeType"]

        if return_value["type"] == "application/vnd.google-apps.document":
            return_value["type"] = "docx"
            path_to_save = (
                folder_to_save + "/" + return_value["name"] + "." + return_value["type"]
            )

        elif return_value["type"] == "application/vnd.google-apps.presentation":
            return_value["type"] = "pptx"
            path_to_save = (
                folder_to_save + "/" + return_value["name"] + "." + return_value["type"]
            )

        elif return_value["type"] == "application/vnd.google-apps.spreadsheet":
            return_value["type"] = "xlsx"
            path_to_save = (
                folder_to_save + "/" + return_value["name"] + "." + return_value["type"]
            )
        else:
            path_to_save = folder_to_save + "/" + return_value["name"]
            return_value["size"] = file_metadata_json["size"]

        binary_stream = self._get_binary_stream_from_file(file_id, file_metadata_json)

        with open(path_to_save, "wb") as f:
            f.write(binary_stream.getvalue())
        binary_stream.close()
        return_value["saved_to"] = path_to_save
        return return_value

    def download_file_to_base64(self, file_id):
        file_metadata_json = (
            self._service.files().get(fileId=file_id, fields="*").execute()
        )

        return_value = {}
        return_value["name"] = file_metadata_json["name"]
        return_value["type"] = file_metadata_json["mimeType"]

        if return_value["type"] == "application/vnd.google-apps.document":
            return_value["type"] = "docx"

        elif return_value["type"] == "application/vnd.google-apps.presentation":
            return_value["type"] = "pptx"

        elif return_value["type"] == "application/vnd.google-apps.spreadsheet":
            return_value["type"] = "xlsx"
        else:
            return_value["size"] = file_metadata_json["size"]

        binary_stream = self._get_binary_stream_from_file(file_id, file_metadata_json)

        base64_content = str(base64.b64encode(binary_stream.getvalue()).decode())
        return_value["base64"] = base64_content
        return return_value

    def insert_permission(self, file_id, role, emails, sendNotificationEmail=True):
        """Insert a new permission.

        Args:
          file_id: ID of the file to insert permission for.
          emails: User or group e-mail address, domain name or None for 'default' type.
          role: The value 'owner', 'writer' or 'reader'.

        Returns:
          The inserted permission if successful, None otherwise.

        """
        user_permission = {"type": "user", "role": role, "emailAddress": emails}
        res = (
            self._service.permissions()
            .create(
                fileId=file_id,
                body=user_permission,
                fields="id",
                sendNotificationEmail=sendNotificationEmail,
            )
            .execute()
        )
        return res

    def upload_file_from_path(self, file_path):
        head, tail = os.path.split(file_path)

        file_metadata = {"name": tail}
        media = MediaFileUpload(file_path)
        data = (
            self._service.files()
            .create(body=file_metadata, media_body=media, fields="*")
            .execute()
        )

        return data

    def upload_file_from_base64(self, file_name, base64):
        file_metadata = {"name": file_name}
        fh = io.BytesIO(b64decode(base64))
        mime_type = self._mime_content_type(file_name)
        media = MediaIoBaseUpload(fh, mimetype=mime_type)

        data = (
            self._service.files()
            .create(body=file_metadata, media_body=media, fields="*")
            .execute()
        )

        return data

    def copy_file(self, origin_file_id, copy_title):
        """Copy an existing file.

        Args:
          origin_file_id: ID of the origin file to copy.
          copy_title: Title of the copy.

        Returns:
          The copied file if successful, None otherwise.

        """
        copied_file = {"title": copy_title}
        res = (
            self._service.files()
            .copy(fileId=origin_file_id, fields="*", body=copied_file)
            .execute()
        )
        return res

    def delete_file(self, file_id):
        """Permanently delete a file, skipping the trash.

        Args:
          file_id: ID of the file to delete.

        """
        self._service.files().delete(fileId=file_id).execute()

    def remove_permission(self, file_id, permission_id):
        """Remove a permission.

        Args:
          file_id: ID of the file to remove the permission for.
          permission_id: ID of the permission to remove.

        """
        self._service.permissions().delete(
            fileId=file_id,
            permissionId=permission_id,
        ).execute()

    def get_file_metadata(self, file_id):
        """Get a file's metadata.

        Args:
          file_id: ID of the file to print metadata for.

        """
        resource_metadata_json = (
            self._service.files().get(fileId=file_id, fields="*").execute()
        )

        return resource_metadata_json

    def _mime_content_type(self, file_name):
        """Get mime type
        :param filename: str
        :type filename: str
        :rtype: str
        """
        mime_types = dict(
            txt="text/plain",
            htm="text/html",
            html="text/html",
            php="text/html",
            css="text/css",
            js="application/javascript",
            json="application/json",
            xml="application/xml",
            swf="application/x-shockwave-flash",
            flv="video/x-flv",
            # images
            png="image/png",
            jpe="image/jpeg",
            jpeg="image/jpeg",
            jpg="image/jpeg",
            gif="image/gif",
            bmp="image/bmp",
            ico="image/vnd.microsoft.icon",
            tiff="image/tiff",
            tif="image/tiff",
            svg="image/svg+xml",
            svgz="image/svg+xml",
            # archives
            zip="application/zip",
            rar="application/x-rar-compressed",
            exe="application/x-msdownload",
            msi="application/x-msdownload",
            cab="application/vnd.ms-cab-compressed",
            # audio/video
            mp3="audio/mpeg",
            ogg="audio/ogg",
            qt="video/quicktime",
            mov="video/quicktime",
            # adobe
            pdf="application/pdf",
            psd="image/vnd.adobe.photoshop",
            ai="application/postscript",
            eps="application/postscript",
            ps="application/postscript",
            # ms office
            doc="application/msword",
            rtf="application/rtf",
            xls="application/vnd.ms-excel",
            ppt="application/vnd.ms-powerpoint",
            # open office
            odt="application/vnd.oasis.opendocument.text",
            ods="application/vnd.oasis.opendocument.spreadsheet",
        )

        ext = os.path.splitext(file_name)[1][1:].lower()
        if ext in mime_types:
            return mime_types[ext]
        return "application/octet-stream"
