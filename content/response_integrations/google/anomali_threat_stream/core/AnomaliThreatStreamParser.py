from __future__ import annotations

from typing import Any

from .datamodels import *
from .constants import CLASSNAME_MAPPER, MAX_DESCRIPTION_LENGTH, MAX_BODY_LENGTH
import pandas as pd


class ThreatStreamParser:
    """
    Siemplify Threat Fuse parser
    """

    @staticmethod
    def build_indicator_obj(objects_data: dict[str, Any], web_root: str) -> Indicator:
        return Indicator(
            raw_data=objects_data,
            severity=objects_data.get("meta", {}).get("severity"),
            tags=[
                ThreatStreamParser.build_tag_obj(tag)
                for tag in (objects_data.pop("tags", []) or [])
            ],
            registrant_address=objects_data.get("meta", {}).get("registrant_address"),
            registration_created=objects_data.get("meta", {}).get(
                "registration_created"
            ),
            registration_updated=objects_data.get("meta", {}).get(
                "registration_updated"
            ),
            web_root=web_root
        )

    @staticmethod
    def build_tag_obj(tag_data: dict[str, Any]) -> Tag:
        return Tag(raw_data=tag_data)

    @staticmethod
    def match_entity_to_indicators(indicators, entities):
        """
        Match entities with their indicators
        :param indicators: {[Indicator]} List of indicators to match to the entities
        :param entities: {[DomainEntityInfo]} List of entities to match the indicator to
        :return: {[IndicatorsGroup]} List of indicators groups that represent matching of entity and its indicators
        """
        indicator_groups = []

        for entity in entities:
            indicator_group = IndicatorsGroup(entity=entity)

            for indicator in indicators:
                if str(indicator.value).lower() == entity.identifier.lower():
                    indicator_group.add_indicator(indicator)

            indicator_groups.append(indicator_group)

        return indicator_groups

    @staticmethod
    def build_analysis_link_objects(analysis_links_data):
        return [
            AnalysisLink(name=key, link=value)
            for key, value in analysis_links_data.items()
        ]

    @staticmethod
    def build_intel_details_objects(intel_details_data):
        return IntelDetails(
            raw_data=intel_details_data,
            virus_total_classification=intel_details_data.get("VirusTotal", {}).get(
                "Classification"
            ),
            domain_tools_classification=intel_details_data.get("Domain Tools", {}).get(
                "Classification"
            ),
            google_safe_browsing_classification=intel_details_data.get(
                "Google Safe Browsing", {}
            ).get("Classification"),
            ipvoid_classification=intel_details_data.get("IPVoid", {}).get(
                "Classification"
            ),
            honeypot_classification=intel_details_data.get("Project Honey Pot", {}).get(
                "Classification"
            ),
            web_of_trust_classification=intel_details_data.get("Web of Trust", {}).get(
                "Classification"
            ),
            ipvoid_detections=intel_details_data.get("IPVoid", {}).get("Detections"),
        )

    @staticmethod
    def build_job_status_obj(job_status: dict[str, Any]) -> JobStatus:
        return JobStatus(
            raw_data=job_status,
            job_id=job_status.get("job_id"),
            success=job_status.get("success", False),
            import_session_id=job_status.get("import_session_id"),
        )

    @staticmethod
    def build_job_details_obj(job_details: dict[str, Any]) -> JobDetails:
        return JobDetails(raw_data=job_details)

    @staticmethod
    def build_association_obj(
            objects_data: dict[str, Any],
            web_root: str
    ) -> Association:
        """
        Builds an association object.

        Args:
            objects_data(dict): raw response
            web_root(str): Web root of the Anomali Threat Stream API

        Returns:
            Association: Association object
        """
        aliases_objs = [
            ThreatStreamParser.build_alias_obj(alias)
            for alias in objects_data.get("aliases", [])
        ]

        if isinstance(objects_data.get("status", {}), dict):
            status_display_name = objects_data.get("status", {}).get("display_name", "")
        else:
            status_display_name = ""

        if objects_data.get("parent", None):
            parent_name = objects_data.get("parent").get("name")
        else:
            parent_name = ""

        return Association(
            raw_data=objects_data,
            aliases_objs=aliases_objs,
            status_display_name=status_display_name,
            parent_name=parent_name,
            web_root=web_root
        )

    @staticmethod
    def build_alias_obj(aliases_data: dict[str, Any]) -> Alias:
        return Alias(
            alias_id=aliases_data.get("id"),
            name=aliases_data.get("name"),
            resource_uri=aliases_data.get("resource_uri"),
        )

    @staticmethod
    def shorten_body_and_description(raw_data):
        """
        Function shortens 'body' and 'description' fields of raw response
        :param raw_data: {json} of raw response
        :return: {dict} of raw data with the fields 'body' and 'description' shortened
        """
        # Shorten raw description
        if isinstance(raw_data.get("description", ""), str):
            splitted = " ".join(
                raw_data.get("description", "").split(" ")[:MAX_DESCRIPTION_LENGTH]
            )
            if splitted:
                raw_data["description"] = splitted + "..."
            else:
                raw_data["description"] = ""

        # Shorten raw body
        if isinstance(raw_data.get("body", ""), str):
            splitted = " ".join(raw_data.get("body", "").split(" ")[:MAX_BODY_LENGTH])
            if splitted:
                raw_data["body"] = splitted + "..."
            else:
                raw_data["body"] = ""

        return raw_data

    @staticmethod
    def build_association_details_object(raw_json, web_root, association_type):
        if isinstance(raw_json.get("status", {}), dict):
            status_display_name = raw_json.get("status", {}).get("display_name", "")
        else:
            status_display_name = raw_json.get("status", "")

        class_name = CLASSNAME_MAPPER.get(association_type)

        return eval(
            class_name(
                raw_data=raw_json,
                status_display_name=status_display_name,
                web_root=web_root,
                **raw_json
            )
        )

    @staticmethod
    def build_threat_bulletins_details_obj(
            threat_bulletins_details: dict[str, Any],
            web_root: str
    ) -> ThreatBulletinsDetails:
        """
        Builds a threat bulletins details object.

        Args:
            threat_bulletins_details(dict): raw response
            web_root(str): Web root of the Anomali Threat Stream API

        Returns:
            ThreatBulletinsDetails: ThreatBulletinsDetails object
        """
        if isinstance(threat_bulletins_details.get("status", {}), dict):
            status_display_name = threat_bulletins_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        threat_bulletins_details = ThreatStreamParser.shorten_body_and_description(
            threat_bulletins_details
        )

        return ThreatBulletinsDetails(
            raw_data=threat_bulletins_details,
            web_root=web_root,
            status_display_name=status_display_name,
        )

    @staticmethod
    def build_actor_details_obj(
            actor_details: dict[str, Any],
            web_root: str
    ) -> ActorDetails:
        """
        Builds an actor details object.

        Args:
            actor_details(dict): raw response
            web_root(str): Web root of the Anomali Threat Stream API

        Returns:
            ActorDetails: ActorDetails object
        """
        if actor_details.get("soph_type", {}):  # check if not None
            sophistication_type_display_name = actor_details.get("soph_type", {}).get(
                "display_name"
            )
        else:
            sophistication_type_display_name = ""

        if isinstance(actor_details.get("status", {}), dict):
            status_display_name = actor_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        actor_details = ThreatStreamParser.shorten_body_and_description(actor_details)

        return ActorDetails(
            raw_data=actor_details,
            sophistication_type_display_name=sophistication_type_display_name,
            actor_motivations=actor_details.get("motivations", []),
            aliases_obj=[
                ThreatStreamParser.build_alias_obj(alias)
                for alias in actor_details.get("aliases", [])
            ],
            web_root=web_root,
            status_display_name=status_display_name
        )

    @staticmethod
    def build_attackpattern_details_obj(
            attack_pattern_details: dict[str, Any],
            web_root: str
    ) -> AttackPatternDetails:
        """
        Builds an attack pattern details object.

        Args:
            attack_pattern_details(dict): raw response
            web_root(str): Web root of the Anomali Threat Stream API

        Returns:
            AttackPatternDetails: AttackPatternDetails object
        """
        if isinstance(attack_pattern_details.get("status", {}), dict):
            status_display_name = attack_pattern_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        attack_pattern_details = ThreatStreamParser.shorten_body_and_description(
            attack_pattern_details
        )

        return AttackPatternDetails(
            raw_data=attack_pattern_details,
            web_root=web_root,
            status_display_name=status_display_name,
        )

    @staticmethod
    def build_campaign_details_obj(
            campaign_details: dict[str, Any],
            web_root: str
    ) -> CampaignDetails:
        """
        Builds a campaign details object.

        Args:
            campaign_details(dict): raw response
            web_root(str): Web root of the Anomali Threat Stream API

        Returns:
            CampaignDetails: CampaignDetails object
        """
        if isinstance(campaign_details.get("status", {}), dict):
            status_display_name = campaign_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        campaign_details = ThreatStreamParser.shorten_body_and_description(
            campaign_details
        )

        return CampaignDetails(
            raw_data=campaign_details,
            aliases_obj=[
                ThreatStreamParser.build_alias_obj(alias)
                for alias in campaign_details.get("aliases", [])
            ],
            status_display_name=status_display_name,
            web_root=web_root,
        )

    @staticmethod
    def build_course_of_action_details_obj(
            course_of_action_details: dict[str, Any],
            web_root: str
    ) -> CourseOfActionDetails:
        """
        Builds a course of action details object.

        Args:
            course_of_action_details(dict): raw response
            web_root(str): Web root of the Anomali Threat Stream API

        Returns:
            CourseOfActionDetails: CourseOfActionDetails object
        """
        if isinstance(course_of_action_details.get("status", {}), dict):
            status_display_name = course_of_action_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        course_of_action_details = ThreatStreamParser.shorten_body_and_description(
            course_of_action_details
        )

        return CourseOfActionDetails(
            raw_data=course_of_action_details,
            web_root=web_root,
            status_display_name=status_display_name,
        )

    @staticmethod
    def build_identity_details_obj(
            identity_details: dict[str, Any],
            web_root: str
    ) -> IdentityDetails:
        """
        Builds an identity details object.

        Args:
            identity_details(dict): raw response
            web_root(str): Web root of the Anomali Threat Stream API

        Returns:
            IdentityDetails: IdentityDetails object
        """
        if isinstance(identity_details.get("status", {}), dict):
            status_display_name = identity_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        identity_details = ThreatStreamParser.shorten_body_and_description(
            identity_details
        )

        return IdentityDetails(
            raw_data=identity_details,
            web_root=web_root,
            status_display_name=status_display_name,
        )

    @staticmethod
    def build_incident_details_obj(
            incident_details: dict[str, Any],
            web_root: str
    ) -> IncidentDetails:
        """
        Builds an incident details object.

        Args:
            incident_details(dict): raw response
            web_root(str): Web root of the Anomali Threat Stream API

        Returns:
            IncidentDetails: IncidentDetails object
        """
        if isinstance(incident_details.get("status", {}), dict):
            status_display_name = incident_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        incident_details = ThreatStreamParser.shorten_body_and_description(
            incident_details
        )

        return IncidentDetails(
            raw_data=incident_details,
            web_root=web_root,
            status_display_name=status_display_name,
        )

    @staticmethod
    def build_infrastructure_details_obj(
            infrastructure_details: dict[str, Any],
            web_root: str
    ) -> InfrastructureDetails:
        """
        Builds an infrastructure details object.

        Args:
            infrastructure_details(dict): raw response
            web_root(str): Web root of the Anomali Threat Stream API

        Returns:
            InfrastructureDetails: InfrastructureDetails object
        """
        if isinstance(infrastructure_details.get("status", {}), dict):
            status_display_name = infrastructure_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        infrastructure_details = ThreatStreamParser.shorten_body_and_description(
            infrastructure_details
        )

        return InfrastructureDetails(
            raw_data=infrastructure_details,
            web_root=web_root,
            status_display_name=status_display_name,
        )

    @staticmethod
    def build_intrusionset_details_obj(
            intrusionset_details: dict[str, Any],
            web_root: str
    ) -> IntrusionSetDetails:
        """
        Builds an intrusionset details object.

        Args:
            intrusionset_details(dict): raw response
            web_root(str): Web root of the Anomali Threat Stream API

        Returns:
            IntrusionSetDetails: IntrusionSetDetails object
        """
        if isinstance(intrusionset_details.get("status", {}), dict):
            status_display_name = intrusionset_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        intrusionset_details = ThreatStreamParser.shorten_body_and_description(
            intrusionset_details
        )

        return IntrusionSetDetails(
            raw_data=intrusionset_details,
            web_root=web_root,
            status_display_name=status_display_name,
        )

    @staticmethod
    def build_malware_details_obj(
            malware_details: dict[str, Any],
            web_root: str
    ) -> MalwareDetails:
        """
        Builds a malware details object.

        Args:
            malware_details(dict): raw response
            web_root(str): Web root of the Anomali Threat Stream API

        Returns:
            MalwareDetails: MalwareDetails object
        """
        if isinstance(malware_details.get("status", {}), dict):
            status_display_name = malware_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        malware_details = ThreatStreamParser.shorten_body_and_description(
            malware_details
        )

        return MalwareDetails(
            raw_data=malware_details,
            web_root=web_root,
            status_display_name=status_display_name,
        )

    @staticmethod
    def build_signature_details_obj(
            signature_details: dict[str, Any],
            web_root: str
    ) -> SignatureDetails:
        """
        Builds a signature details object.

        Args:
            signature_details(dict): raw response
            web_root(str): Web root of the Anomali Threat Stream API

        Returns:
            SignatureDetails: SignatureDetails object
        """
        if signature_details.get("parent", {}):  # check if not None
            parent_display_name = signature_details.get("parent", {}).get("name")
        else:
            parent_display_name = ""

        if signature_details.get("s_type", {}):  # check if not None
            signature_type_name = signature_details.get("s_type", {}).get(
                "display_name"
            )
        else:
            signature_type_name = ""

        if isinstance(signature_details.get("status", {}), dict):
            status_display_name = signature_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        signature_details = ThreatStreamParser.shorten_body_and_description(
            signature_details
        )

        return SignatureDetails(
            raw_data=signature_details,
            aliases_obj=[
                ThreatStreamParser.build_alias_obj(alias)
                for alias in signature_details.get("aliases", [])
            ],
            signature_type_name=signature_type_name,
            parent_display_name=parent_display_name,
            web_root=web_root,
            status_display_name=status_display_name,
        )

    @staticmethod
    def build_tool_details_obj(
            tool_details: dict[str, Any],
            web_root: str
    ) -> ToolDetails:
        """
        Builds a tool details object.

        Args:
            tool_details(dict): raw response
            web_root(str): Web root of the Anomali Threat Stream API

        Returns:
            ToolDetails: ToolDetails object
        """
        if isinstance(tool_details.get("status", {}), dict):
            status_display_name = tool_details.get("status", {}).get("display_name", "")
        else:
            status_display_name = ""

        tool_details = ThreatStreamParser.shorten_body_and_description(tool_details)

        return ToolDetails(
            raw_data=tool_details,
            web_root=web_root,
            status_display_name=status_display_name,
        )

    @staticmethod
    def build_ttp_details_obj(ttp_details: dict[str, Any], web_root: str) -> TTPDetails:
        """
        Builds a ttp details object.

        Args:
            ttp_details(dict): raw response
            web_root(str): Web root of the Anomali Threat Stream API

        Returns:
            TTPDetails: TTPDetails object
        """
        if isinstance(ttp_details.get("status", {}), dict):
            status_display_name = ttp_details.get("status", {}).get("display_name", "")
        else:
            status_display_name = ""

        ttp_details = ThreatStreamParser.shorten_body_and_description(ttp_details)

        return TTPDetails(
            raw_data=ttp_details,
            web_root=web_root,
            status_display_name=status_display_name,
        )

    @staticmethod
    def build_vulnerability_obj(
            objects_data: dict[str, Any],
            web_root: str
    ) -> Vulnerability:
        """
        Builds a vulnerability details object.

        Args:
            objects_data(dict): raw response
            web_root(str): Web root of the Anomali Threat Stream API

        Returns:
            Vulnerability: Vulnerability object
        """
        if isinstance(objects_data.get("status", {}), dict):
            status_display_name = objects_data.get("status", {}).get("display_name", "")
        else:
            status_display_name = ""

        objects_data = ThreatStreamParser.shorten_body_and_description(objects_data)

        return Vulnerability(
            raw_data=objects_data,
            web_root=web_root,
            status_display_name=status_display_name,
        )

    @staticmethod
    def build_attribute_statistics_obj(raw_data, meta_total_count, limit=None):
        """
        Function that aggregates the associations
        :param raw_data: {json} of raw response
        :param meta_total_count: {str} Total Count from meta data
        :param limit: {int} Limit of number of top values to return
        :return: {dict} Aggregated results
        """
        objects = pd.DataFrame.from_dict(raw_data)
        stats_json = {}
        objects = objects.fillna("N/A")

        country_stats = (
            objects.groupby(["country"], as_index=False)
            .size()
            .rename(columns={"country": "name", "size": "count"})
            .sort_values(["count"], ascending=False)
            .replace("", "N/A")
            .to_dict(orient="records")
        )
        type_stats = (
            objects.groupby(["type"], as_index=False)
            .size()
            .rename(columns={"type": "name", "size": "count"})
            .sort_values(["count"], ascending=False)
            .replace("", "N/A")
            .to_dict(orient="records")
        )
        threat_type_stats = (
            objects.groupby(["threat_type"], as_index=False)
            .size()
            .rename(columns={"threat_type": "name", "size": "count"})
            .sort_values(["count"], ascending=False)
            .replace("", "N/A")
            .to_dict(orient="records")
        )
        source_stats = (
            objects.groupby(["source"], as_index=False)
            .size()
            .rename(columns={"source": "name", "size": "count"})
            .sort_values(["count"], ascending=False)
            .replace("", "N/A")
            .to_dict(orient="records")
        )
        status_stats = (
            objects.groupby(["status"], as_index=False)
            .size()
            .rename(columns={"status": "name", "size": "count"})
            .sort_values(["count"], ascending=False)
            .replace("", "N/A")
            .to_dict(orient="records")
        )
        severity_stats = (
            pd.DataFrame([v for k, v in objects["meta"].items()])
            .groupby(["severity"], as_index=False)
            .size()
            .rename(columns={"severity": "name", "size": "count"})
            .sort_values(["count"], ascending=False)
            .replace("", "N/A")
            .to_dict(orient="records")
        )
        org_stats = (
            objects.groupby(["org"], as_index=False)
            .size()
            .rename(columns={"org": "name", "size": "count"})
            .sort_values(["count"], ascending=False)
            .replace("", "N/A")
            .to_dict(orient="records")
        )

        if limit is not None:
            country_stats = country_stats[:limit]
            type_stats = type_stats[:limit]
            source_stats = source_stats[:limit]
            severity_stats = severity_stats[:limit]
            threat_type_stats = threat_type_stats[:limit]
            org_stats = org_stats[:limit]
            status_stats = status_stats[:limit]

        stats_json["statistics"] = {}
        stats_json["statistics"]["total"] = meta_total_count
        stats_json["statistics"]["top_countries"] = country_stats
        stats_json["statistics"]["top_types"] = type_stats
        stats_json["statistics"]["top_sources"] = source_stats
        stats_json["statistics"]["top_severities"] = severity_stats
        stats_json["statistics"]["top_threat_types"] = threat_type_stats
        stats_json["statistics"]["top_orgs"] = org_stats
        stats_json["statistics"]["top_status"] = status_stats

        return stats_json
