from __future__ import annotations

import json

import gspread
from google.oauth2.service_account import Credentials


class GoogleSheetFactory:
    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    def __init__(self, json_input: str):
        self.json_input: str = json_input

    def create_client(self) -> gspread.Client:
        credentials = Credentials.from_service_account_info(
            json.loads(self.json_input),
            scopes=self.DEFAULT_SCOPES,
        )

        return gspread.Client(auth=credentials)

    def create_spreadsheet(self, sheet_id: str) -> gspread.Spreadsheet:
        client = self.create_client()
        return client.open_by_key(sheet_id)
