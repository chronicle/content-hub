from __future__ import annotations
from google_forms.core import datamodels

from TIPCommon.types import SingleJson


class GoogleFormsParser:
    def build_alert_response(
        self,
        raw_data: list[SingleJson],
        form_data: datamodels.FormResponse,
    ) -> list[datamodels.AlertResponse]:
        """Builds a list of AlertResponse objects from JSON data.

        Args:
            raw_data (list[SingleJson]): A list of JSON objects representing
                alert responses.
            form_data (datamodels.FormResponse): The form response data associated
                with the alerts.

        Returns:
            list[datamodels.AlertResponse]: A list of AlertResponse objects constructed
                from the input data.
        """
        return [
            datamodels.AlertResponse.from_json(
                alert_json=alert_json,
                form_json=form_data,
            )
            for alert_json in raw_data
        ]

    def build_form(self, raw_data: SingleJson) -> datamodels.FormResponse:
        """Build an form details object.

        Args:
            raw_data (SingleJson): JSON data for the form from the API response.

        Returns:
            datamodels.Asset: The built form object.
        """
        return datamodels.FormResponse.from_json(raw_data)
