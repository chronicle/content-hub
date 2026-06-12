from core.datamodels.incident import Incident
from core.opencti_client.json_results import (
    IncidentJSONResult,
)
from pycti import OpenCTIApiClient
from pydantic import ValidationError


class OpenCTIClientError(Exception):
    pass


class OpenCTIClient:
    def __init__(self, base_url: str, api_token: str, ssl_verify: bool = True) -> None:
        try:
            # Note: a health check is performed during OpenCTIApiClient initialization
            self._api_client = OpenCTIApiClient(
                base_url,
                api_token,
                ssl_verify=ssl_verify,
            )
        except ValueError as e:
            raise OpenCTIClientError(
                f"Failed to establish connection with OpenCTI: {str(e)}"
            ) from e

    def _upsert_vocabulary_entries(self, category: str, *values: str | None) -> None:
        if not category or not values:
            return

        try:
            for value in values:
                if value:
                    self._api_client.vocabulary.create(category=category, name=value)
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to upsert entries in {category} in OpenCTI: {str(e)}"
            ) from e

    def _upsert_labels(self, labels: list[str] | None) -> None:
        if not labels:
            return

        try:
            for label in labels:
                self._api_client.label.create(value=label)
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to upsert labels in OpenCTI: {str(e)}"
            ) from e

    def create_incident(self, incident: Incident) -> IncidentJSONResult:
        try:
            incident_args = incident.to_input_variables()
            information_types = incident_args.get("information_types") or []
            priority = incident_args.get("priority")
            severity = incident_args.get("severity")
            self._upsert_vocabulary_entries("incident_type_ov", *information_types)
            self._upsert_vocabulary_entries("case_priority_ov", priority)
            self._upsert_vocabulary_entries("case_severity_ov", severity)

            labels = incident_args.get("objectLabel")
            self._upsert_labels(labels)
            data = self._api_client.case_incident.create(**incident_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create Incident."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to create Incident in OpenCTI: {str(e)}"
            ) from e

        try:
            return IncidentJSONResult(**data)
        except ValidationError as e:
            raise OpenCTIClientError(
                f"Unexpected OpenCTI response for Incident creation: {str(e)}"
            ) from e
