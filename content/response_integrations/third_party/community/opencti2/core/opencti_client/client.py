from typing import Literal

from core.datamodels.attack_pattern import AttackPattern
from core.datamodels.campaign import Campaign
from core.datamodels.grouping import Grouping
from core.datamodels.incident import Incident
from core.datamodels.incident_response import IncidentResponse
from core.datamodels.indicator import Indicator
from core.datamodels.intrusion_set import IntrusionSet
from core.datamodels.malware import Malware
from core.datamodels.relationship import Relationship
from core.datamodels.sighting import Sighting
from core.datamodels.observable import Observable
from core.datamodels.report import Report
from core.datamodels.request_for_information import RequestForInformation
from core.datamodels.request_for_takedown import RequestForTakedown
from core.opencti_client.json_results import (
    AddObjectToContainerJSONResult,
    AttackPatternJSONResult,
    CampaignJSONResult,
    GroupingJSONResult,
    IncidentJSONResult,
    IncidentResponseJSONResult,
    IndicatorJSONResult,
    IntrusionSetJSONResult,
    MalwareJSONResult,
    RelationshipJSONResult,
    SightingJSONResult,
    ObservableJSONResult,
    ReportJSONResult,
    RequestForInformationJSONResult,
    RequestForTakedownJSONResult,
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
            data = self._api_client.incident.create(**incident_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create the "
                    "incident (some arguments may be missing or invalid)."
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

    def create_incident_response(
        self, incident_response: IncidentResponse
    ) -> IncidentResponseJSONResult:
        try:
            incident_response_args = incident_response.to_input_variables()
            information_types = incident_response_args.get("information_types") or []
            priority = incident_response_args.get("priority")
            severity = incident_response_args.get("severity")
            self._upsert_vocabulary_entries("incident_type_ov", *information_types)
            self._upsert_vocabulary_entries("case_priority_ov", priority)
            self._upsert_vocabulary_entries("case_severity_ov", severity)

            labels = incident_response_args.get("objectLabel")
            self._upsert_labels(labels)
            data = self._api_client.case_incident.create(**incident_response_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create the "
                    "incident response (some arguments may be missing or invalid)."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to create IncidentResponse in OpenCTI: {str(e)}"
            ) from e

        try:
            return IncidentResponseJSONResult(**data)
        except ValidationError as e:
            raise OpenCTIClientError(
                "Unexpected OpenCTI response for IncidentResponse creation: "
                f"{str(e)}"
            ) from e

    def create_request_for_information(
        self, request_for_information: RequestForInformation
    ) -> RequestForInformationJSONResult:
        try:
            rfi_args = request_for_information.to_input_variables()
            information_types = rfi_args.get("information_types") or []
            priority = rfi_args.get("priority")
            severity = rfi_args.get("severity")
            self._upsert_vocabulary_entries(
                "request_for_information_types_ov", *information_types
            )
            self._upsert_vocabulary_entries("case_priority_ov", priority)
            self._upsert_vocabulary_entries("case_severity_ov", severity)

            labels = rfi_args.get("objectLabel")
            self._upsert_labels(labels)
            data = self._api_client.case_rfi.create(**rfi_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create the "
                    "request for information (some arguments may be missing or invalid)."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to create Request for Information in OpenCTI: {str(e)}"
            ) from e

        try:
            return RequestForInformationJSONResult(**data)
        except ValidationError as e:
            raise OpenCTIClientError(
                f"Unexpected OpenCTI response for RFI creation: {str(e)}"
            ) from e

    def create_request_for_takedown(
        self, request_for_takedown: RequestForTakedown
    ) -> RequestForTakedownJSONResult:
        try:
            rft_args = request_for_takedown.to_input_variables()
            takedown_types = rft_args.get("takedown_types") or []
            priority = rft_args.get("priority")
            severity = rft_args.get("severity")
            self._upsert_vocabulary_entries(
                "request_for_takedown_types_ov", *takedown_types
            )
            self._upsert_vocabulary_entries("case_priority_ov", priority)
            self._upsert_vocabulary_entries("case_severity_ov", severity)

            labels = rft_args.get("objectLabel")
            self._upsert_labels(labels)
            data = self._api_client.case_rft.create(**rft_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create the "
                    "request for takedown (some arguments may be missing or invalid)."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to create Request for Takedown in OpenCTI: {str(e)}"
            ) from e

        try:
            return RequestForTakedownJSONResult(**data)
        except ValidationError as e:
            raise OpenCTIClientError(
                f"Unexpected OpenCTI response for RFT creation: {str(e)}"
            ) from e

    def create_observable(self, observable: Observable) -> ObservableJSONResult:
        try:
            observable_args = observable.to_input_variables()
            self._upsert_labels(observable_args.get("objectLabel"))
            data = self._api_client.stix_cyber_observable.create(**observable_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create the "
                    "observable (some arguments may be missing or invalid)."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to create Observable in OpenCTI: {str(e)}"
            ) from e

        try:
            return ObservableJSONResult(**data)
        except ValidationError as e:
            raise OpenCTIClientError(
                f"Unexpected OpenCTI response for Observable creation: {str(e)}"
            ) from e

    def create_report(self, report: Report) -> ReportJSONResult:
        try:
            report_args = report.to_input_variables()
            self._upsert_vocabulary_entries(
                "report_types_ov", *(report_args.get("report_types") or [])
            )
            labels = report_args.get("objectLabel")
            self._upsert_labels(labels)
            data = self._api_client.report.create(**report_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create the "
                    "report (some arguments may be missing or invalid)."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to create Report in OpenCTI: {str(e)}"
            ) from e

        try:
            return ReportJSONResult(**data)
        except ValidationError as e:
            raise OpenCTIClientError(
                f"Unexpected OpenCTI response for Report creation: {str(e)}"
            ) from e

    def create_grouping(self, grouping: Grouping) -> GroupingJSONResult:
        try:
            grouping_args = grouping.to_input_variables()
            context = grouping_args.get("context")
            self._upsert_vocabulary_entries("grouping_context_ov", context)

            labels = grouping_args.get("objectLabel")
            self._upsert_labels(labels)
            data = self._api_client.grouping.create(**grouping_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create the "
                    "grouping (some arguments may be missing or invalid)."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to create Grouping in OpenCTI: {str(e)}"
            ) from e

        try:
            return GroupingJSONResult(**data)
        except ValidationError as e:
            raise OpenCTIClientError(
                f"Unexpected OpenCTI response for Grouping creation: {str(e)}"
            ) from e

    def create_relationship(self, relationship: Relationship) -> RelationshipJSONResult:
        try:
            relationship_args = relationship.to_input_variables()
            data = self._api_client.stix_core_relationship.create(**relationship_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create the relationship "
                    "(some arguments may be missing or invalid)."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to create Relationship in OpenCTI: {str(e)}"
            ) from e

        try:
            return RelationshipJSONResult(**data)
        except ValidationError as e:
            raise OpenCTIClientError(
                f"Unexpected OpenCTI response for Relationship creation: {str(e)}"
            ) from e

    def create_malware(self, malware: Malware) -> MalwareJSONResult:
        try:
            malware_args = malware.to_input_variables()
            malware_types = malware_args.get("malware_types") or []
            self._upsert_vocabulary_entries("malware_type_ov", *malware_types)

            labels = malware_args.get("objectLabel")
            self._upsert_labels(labels)
            data = self._api_client.malware.create(**malware_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create the malware "
                    "(some arguments may be missing or invalid)."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to create Malware in OpenCTI: {str(e)}"
            ) from e

        try:
            return MalwareJSONResult(**data)
        except ValidationError as e:
            raise OpenCTIClientError(
                f"Unexpected OpenCTI response for Malware creation: {str(e)}"
            ) from e

    def create_intrusion_set(self, intrusion_set: IntrusionSet) -> IntrusionSetJSONResult:
        try:
            intrusion_set_args = intrusion_set.to_input_variables()
            self._upsert_labels(intrusion_set_args.get("objectLabel"))
            data = self._api_client.intrusion_set.create(**intrusion_set_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create the intrusion set "
                    "(some arguments may be missing or invalid)."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to create Intrusion Set in OpenCTI: {str(e)}"
            ) from e

        try:
            return IntrusionSetJSONResult(**data)
        except ValidationError as e:
            raise OpenCTIClientError(
                f"Unexpected OpenCTI response for Intrusion Set creation: {str(e)}"
            ) from e

    def create_campaign(self, campaign: Campaign) -> CampaignJSONResult:
        try:
            campaign_args = campaign.to_input_variables()
            self._upsert_labels(campaign_args.get("objectLabel"))
            data = self._api_client.campaign.create(**campaign_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create the campaign "
                    "(some arguments may be missing or invalid)."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to create Campaign in OpenCTI: {str(e)}"
            ) from e

        try:
            return CampaignJSONResult(**data)
        except ValidationError as e:
            raise OpenCTIClientError(
                f"Unexpected OpenCTI response for Campaign creation: {str(e)}"
            ) from e

    def create_attack_pattern(self, attack_pattern: AttackPattern) -> AttackPatternJSONResult:
        try:
            attack_pattern_args = attack_pattern.to_input_variables()
            self._upsert_labels(attack_pattern_args.get("objectLabel"))
            data = self._api_client.attack_pattern.create(**attack_pattern_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create the attack pattern "
                    "(some arguments may be missing or invalid)."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to create Attack Pattern in OpenCTI: {str(e)}"
            ) from e

        try:
            return AttackPatternJSONResult(**data)
        except ValidationError as e:
            raise OpenCTIClientError(
                f"Unexpected OpenCTI response for Attack Pattern creation: {str(e)}"
            ) from e

    def create_indicator(self, indicator: Indicator) -> IndicatorJSONResult:
        try:
            indicator_args = indicator.to_input_variables()
            pattern_types = indicator_args.get("pattern_type") or []
            self._upsert_vocabulary_entries("pattern_type_ov", *pattern_types)

            labels = indicator_args.get("objectLabel")
            self._upsert_labels(labels)
            data = self._api_client.indicator.create(**indicator_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create the indicator "
                    "(some arguments may be missing or invalid)."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to create Indicator in OpenCTI: {str(e)}"
            ) from e

        try:
            return IndicatorJSONResult(**data)
        except ValidationError as e:
            raise OpenCTIClientError(
                f"Unexpected OpenCTI response for Indicator creation: {str(e)}"
            ) from e

    def create_sighting(self, sighting: Sighting) -> SightingJSONResult:
        try:
            sighting_args = sighting.to_input_variables()
            self._upsert_labels(sighting_args.get("objectLabel"))
            data = self._api_client.stix_sighting_relationship.create(**sighting_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create the sighting relationship "
                    "(some arguments may be missing or invalid)."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to create Sighting in OpenCTI: {str(e)}"
            ) from e

        try:
            return SightingJSONResult(**data)
        except ValidationError as e:
            raise OpenCTIClientError(
                f"Unexpected OpenCTI response for Sighting creation: {str(e)}"
            ) from e

    def add_object_to_container(
        self,
        container_type: Literal[
            "Report", "Case-Incident", "Case-Rfi", "Case-Rft", "Grouping"
        ],
        container_id: str,
        object_id: str,
    ) -> AddObjectToContainerJSONResult:
        add_methods = {
            "Report": self._api_client.report.add_stix_object_or_stix_relationship,
            "Case-Incident": self._api_client.case_incident.add_stix_object_or_stix_relationship,
            "Case-Rfi": self._api_client.case_rfi.add_stix_object_or_stix_relationship,
            "Case-Rft": self._api_client.case_rft.add_stix_object_or_stix_relationship,
            "Grouping": self._api_client.grouping.add_stix_object_or_stix_relationship,
        }

        try:
            add_method = add_methods[container_type]
        except KeyError as e:
            raise OpenCTIClientError(
                f"Unsupported container type: {container_type}"
            ) from e

        try:
            data = add_method(
                id=container_id,
                stixObjectOrStixRelationshipId=object_id,
            )
            if data is False:
                raise OpenCTIClientError(
                    "pycti could not perform the request to add object to "
                    f"{container_type} (some arguments may be missing or invalid)."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to add object to {container_type} in OpenCTI: {str(e)}"
            ) from e

        return AddObjectToContainerJSONResult(
            container_entity_type=container_type,
            container_id=container_id,
            object_id=object_id,
        )
