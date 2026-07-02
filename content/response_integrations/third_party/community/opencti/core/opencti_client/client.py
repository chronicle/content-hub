from typing import Literal, Protocol

from core.datamodels.attack_pattern import AttackPattern
from core.datamodels.campaign import Campaign
from core.datamodels.grouping import Grouping
from core.datamodels.incident import Incident
from core.datamodels.incident_response import IncidentResponse
from core.datamodels.indicator import Indicator
from core.datamodels.intrusion_set import IntrusionSet
from core.datamodels.malware import Malware
from core.datamodels.observable import Observable
from core.datamodels.relationship import Relationship
from core.datamodels.report import Report
from core.datamodels.request_for_information import RequestForInformation
from core.datamodels.request_for_takedown import RequestForTakedown
from core.datamodels.sighting import Sighting
from core.datamodels.threat_actor_group import ThreatActorGroup
from core.datamodels.tool import Tool
from core.datamodels.vulnerability import Vulnerability
from core.opencti_client.enrich_results import (
    IndicatorEnrichmentResult,
    ObservableEnrichmentResult,
)
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
    ObservableJSONResult,
    RelationshipJSONResult,
    ReportJSONResult,
    RequestForInformationJSONResult,
    RequestForTakedownJSONResult,
    SightingJSONResult,
    ThreatActorGroupJSONResult,
    ToolJSONResult,
    VulnerabilityJSONResult,
)
from core.utils import get_hash_type
from pycti import OpenCTIApiClient
from pydantic import ValidationError


class SOAREntity(Protocol):
    """Represent the SOAREntity model."""

    entity_type: str
    original_identifier: str


class OpenCTIClientError(Exception):
    """Represent the OpenCTIClientError model."""

    pass


class OpenCTIClient:
    """Represent the OpenCTIClient model."""

    def __init__(self, base_url: str, api_token: str, ssl_verify: bool = True) -> None:
        """Initialize the instance.

        Args:
            base_url: str value.
            api_token: str value.
            ssl_verify: bool value.
        """
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
        """Ensure vocabulary entries exist in OpenCTI for the provided category values.

        Args:
            category: OpenCTI vocabulary category name.
            *values: Candidate values to create when missing.
        """
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
        """Ensure all provided labels exist in OpenCTI before object creation.

        Args:
            labels: Labels to upsert, or None when no labels are provided.
        """
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
        """Create incident in OpenCTI and return the normalized API response.

        Args:
            incident: Incident to create in OpenCTI.

        Returns:
            IncidentJSONResult: Parsed response model for the created incident.
        """
        try:
            incident_args = incident.to_input_variables()

            incident_type = incident_args.get("incident_type")
            priority = incident_args.get("priority")
            severity = incident_args.get("severity")
            self._upsert_vocabulary_entries("incident_type_ov", incident_type)
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
        """Create incident response in OpenCTI and return the normalized API response.

        Args:
            incident_response: IncidentResponse to create in OpenCTI.

        Returns:
            IncidentResponseJSONResult: Parsed response model for the created incident response.
        """
        try:
            incident_response_args = incident_response.to_input_variables()

            response_types = incident_response_args.get("response_types") or []
            priority = incident_response_args.get("priority")
            severity = incident_response_args.get("severity")
            self._upsert_vocabulary_entries(
                "incident_response_types_ov", *response_types
            )
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
        """Create request for information in OpenCTI and return the normalized API response.

        Args:
            request_for_information: RequestForInformation to create in OpenCTI.

        Returns:
            RequestForInformationJSONResult: Parsed response model for the created request for information.
        """
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
        """Create request for takedown in OpenCTI and return the normalized API response.

        Args:
            request_for_takedown: RequestForTakedown to create in OpenCTI.

        Returns:
            RequestForTakedownJSONResult: Parsed response model for the created request for takedown.
        """
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
        """Create observable in OpenCTI and return the normalized API response.

        Args:
            observable: Observable to create in OpenCTI.

        Returns:
            ObservableJSONResult: Parsed response model for the created observable.
        """
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
        """Create report in OpenCTI and return the normalized API response.

        Args:
            report: Report to create in OpenCTI.

        Returns:
            ReportJSONResult: Parsed response model for the created report.
        """
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
        """Create grouping in OpenCTI and return the normalized API response.

        Args:
            grouping: Grouping to create in OpenCTI.

        Returns:
            GroupingJSONResult: Parsed response model for the created grouping.
        """
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
        """Create relationship in OpenCTI and return the normalized API response.

        Args:
            relationship: Relationship to create in OpenCTI.

        Returns:
            RelationshipJSONResult: Parsed response model for the created relationship.
        """
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

    def create_vulnerability(
        self, vulnerability: Vulnerability
    ) -> VulnerabilityJSONResult:
        """Create vulnerability in OpenCTI and return the normalized API response.

        Args:
            vulnerability: Vulnerability to create in OpenCTI.

        Returns:
            VulnerabilityJSONResult: Parsed response model for the created vulnerability.
        """
        try:
            vulnerability_args = vulnerability.to_input_variables()

            labels = vulnerability_args.get("objectLabel")
            self._upsert_labels(labels)

            data = self._api_client.vulnerability.create(**vulnerability_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create the "
                    "vulnerability (some arguments may be missing or invalid)."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to create Vulnerability in OpenCTI: {str(e)}"
            ) from e

        try:
            return VulnerabilityJSONResult(**data)
        except ValidationError as e:
            raise OpenCTIClientError(
                f"Unexpected OpenCTI response for Vulnerability creation: {str(e)}"
            ) from e

    def create_malware(self, malware: Malware) -> MalwareJSONResult:
        """Create malware in OpenCTI and return the normalized API response.

        Args:
            malware: Malware to create in OpenCTI.

        Returns:
            MalwareJSONResult: Parsed response model for the created malware.
        """
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

    def create_threat_actor_group(
        self, threat_actor_group: ThreatActorGroup
    ) -> ThreatActorGroupJSONResult:
        """Create threat actor group in OpenCTI and return the normalized API response.

        Args:
            threat_actor_group: ThreatActorGroup to create in OpenCTI.

        Returns:
            ThreatActorGroupJSONResult: Parsed response model for the created threat actor group.
        """
        try:
            threat_actor_group_args = threat_actor_group.to_input_variables()

            threat_actor_types = threat_actor_group_args.get("threat_actor_types") or []
            self._upsert_vocabulary_entries(
                "threat_actor_group_type_ov",
                *threat_actor_types,
            )

            labels = threat_actor_group_args.get("objectLabel")
            self._upsert_labels(labels)

            data = self._api_client.threat_actor_group.create(**threat_actor_group_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create the threat actor group "
                    "(some arguments may be missing or invalid)."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to create Threat Actor Group in OpenCTI: {str(e)}"
            ) from e

        try:
            return ThreatActorGroupJSONResult(**data)
        except ValidationError as e:
            raise OpenCTIClientError(
                "Unexpected OpenCTI response for Threat Actor Group creation: "
                f"{str(e)}"
            ) from e

    def create_intrusion_set(
        self, intrusion_set: IntrusionSet
    ) -> IntrusionSetJSONResult:
        """Create intrusion set in OpenCTI and return the normalized API response.

        Args:
            intrusion_set: IntrusionSet to create in OpenCTI.

        Returns:
            IntrusionSetJSONResult: Parsed response model for the created intrusion set.
        """
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
        """Create campaign in OpenCTI and return the normalized API response.

        Args:
            campaign: Campaign to create in OpenCTI.

        Returns:
            CampaignJSONResult: Parsed response model for the created campaign.
        """
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

    def create_tool(self, tool: Tool) -> ToolJSONResult:
        """Create tool in OpenCTI and return the normalized API response.

        Args:
            tool: Tool to create in OpenCTI.

        Returns:
            ToolJSONResult: Parsed response model for the created tool.
        """
        try:
            tool_args = tool.to_input_variables()

            tool_types = tool_args.get("tool_types") or []
            self._upsert_vocabulary_entries("tool_types_ov", *tool_types)

            labels = tool_args.get("objectLabel")
            self._upsert_labels(labels)

            data = self._api_client.tool.create(**tool_args)
            if data is None:
                raise OpenCTIClientError(
                    "pycti could not perform the request to create the tool "
                    "(some arguments may be missing or invalid)."
                )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to create Tool in OpenCTI: {str(e)}"
            ) from e

        try:
            return ToolJSONResult(**data)
        except ValidationError as e:
            raise OpenCTIClientError(
                f"Unexpected OpenCTI response for Tool creation: {str(e)}"
            ) from e

    def create_attack_pattern(
        self, attack_pattern: AttackPattern
    ) -> AttackPatternJSONResult:
        """Create attack pattern in OpenCTI and return the normalized API response.

        Args:
            attack_pattern: AttackPattern to create in OpenCTI.

        Returns:
            AttackPatternJSONResult: Parsed response model for the created attack pattern.
        """
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
        """Create indicator in OpenCTI and return the normalized API response.

        Args:
            indicator: Indicator to create in OpenCTI.

        Returns:
            IndicatorJSONResult: Parsed response model for the created indicator.
        """
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
        """Create sighting in OpenCTI and return the normalized API response.

        Args:
            sighting: Sighting to create in OpenCTI.

        Returns:
            SightingJSONResult: Parsed response model for the created sighting.
        """
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
        """Attach an existing STIX object or relationship to a supported container.

        Args:
            container_type: Target OpenCTI container type.
            container_id: Identifier of the destination container.
            object_id: Identifier of the object or relationship to attach.

        Returns:
            AddObjectToContainerJSONResult: Summary of the container-object linkage.
        """
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

    def _fetch_relationships(self, entity_id: str) -> list[dict]:
        """Fetch and normalize OpenCTI relationships for a given entity.

        Args:
            entity_id: OpenCTI identifier of the source entity.

        Returns:
            A list of relationship dictionaries. Each dictionary includes:
                - relationship_type
                - related_entity_type
                - related_entity_name

        Raises:
            OpenCTIClientError: If the relationship query fails.
        """
        try:
            raw_relations = self._api_client.stix_core_relationship.list(
                fromOrToId=entity_id,
                getAll=True,
            )
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to fetch relations from OpenCTI: {str(e)}"
            ) from e

        relationships: list[dict] = []
        for rel in raw_relations or []:
            relationship_type = rel.get("relationship_type", "")
            # Determine the "other" side of the relationship
            from_node = rel.get("from") or {}
            to_node = rel.get("to") or {}
            if from_node.get("id") == entity_id:
                other = to_node
            else:
                other = from_node
            relationships.append(
                {
                    "relationship_type": relationship_type,
                    "related_entity_type": other.get("entity_type"),
                    "related_entity_name": other.get("name")
                    or other.get("value")
                    or other.get("observable_value"),
                }
            )
        return relationships

    def enrich_observable(
        self, soar_entity: SOAREntity
    ) -> ObservableEnrichmentResult | None:
        """Enrich a SOAR observable with OpenCTI metadata and relationships.

        Args:
            soar_entity: SOAR entity containing the type and identifier to enrich.

        Returns:
            ObservableEnrichmentResult when a matching observable is found.
            None when the entity type is unsupported or no observable matches.

        Raises:
            OpenCTIClientError: If the OpenCTI lookup fails.
        """
        entity_type = soar_entity.entity_type
        identifier = soar_entity.original_identifier

        if entity_type == "FILEHASH":
            hash_type = get_hash_type(identifier)
            # Maps hash algorithm names (from get_hash_type) to the pycti filter key.
            filter_key_by_hash_type = {
                "md5": "hashes.MD5",
                "sha1": "hashes.SHA-1",
                "sha256": "hashes.SHA-256",
                "sha512": "hashes.SHA-512",
            }
            filter_key = filter_key_by_hash_type.get(hash_type or "")
        else:
            filter_key = "value"

        try:
            data = self._api_client.stix_cyber_observable.read(
                filters={
                    "mode": "and",
                    "filters": [{"key": filter_key, "values": [identifier]}],
                    "filterGroups": [],
                }
            )
            if not data:
                return None
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to enrich Observable in OpenCTI: {str(e)}"
            ) from e

        entity_id = data["id"]
        link = f"{self._api_client.api_url}/dashboard/id/{entity_id}"
        relationships = self._fetch_relationships(entity_id)

        return ObservableEnrichmentResult(
            **data,
            link=link,
            relationships=relationships,
        )

    def enrich_indicator(
        self, soar_entity: SOAREntity
    ) -> IndicatorEnrichmentResult | None:
        """Enrich a SOAR indicator with OpenCTI metadata and relationships.

        Args:
            soar_entity: SOAR entity whose identifier is used as indicator name.

        Returns:
            IndicatorEnrichmentResult when a matching indicator is found.
            None when no indicator matches the provided identifier.

        Raises:
            OpenCTIClientError: If the OpenCTI lookup fails.
        """
        try:
            data = self._api_client.indicator.read(
                filters={
                    "mode": "and",
                    "filters": [
                        {"key": "name", "values": [soar_entity.original_identifier]}
                    ],
                    "filterGroups": [],
                }
            )
            if not data:
                return None
        except Exception as e:
            raise OpenCTIClientError(
                f"Failed to enrich Indicator in OpenCTI: {str(e)}"
            ) from e

        entity_id = data["id"]
        link = f"{self._api_client.api_url}/dashboard/id/{entity_id}"
        relationships = self._fetch_relationships(entity_id)

        return IndicatorEnrichmentResult(
            **data,
            link=link,
            relationships=relationships,
        )
