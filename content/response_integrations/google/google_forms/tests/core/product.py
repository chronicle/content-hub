from __future__ import annotations
import abc

from google_forms.core.datamodels import AlertResponse, FormResponse
from google_forms.tests.common import MOCK_DATA


class GoogleForms(abc.ABC):

    def list_users(self) -> dict:
        return MOCK_DATA.get("connectivity")

    def add_user(self):
        return self.list_users

    def get_forms(self) -> AlertResponse:
        return MOCK_DATA.get("get_forms")

    def get_form_details(self) -> FormResponse:
        return FormResponse.from_json(MOCK_DATA.get("get_form_details"))
