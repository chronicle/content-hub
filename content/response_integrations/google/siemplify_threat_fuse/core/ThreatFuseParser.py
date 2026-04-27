from __future__ import annotations
import itertools
from typing import List
from . import consts
from soar_sdk.SiemplifyDataModel import DomainEntityInfo
from .datamodels import (
    Indicator,
    Association,
    Vulnerability,
    JobDetails,
    JobStatus,
    Tag,
    AnalysisLink,
    ActorDetails,
    CampaignDetails,
    IntelDetails,
    IndicatorsGroup,
    SignatureDetails,
    AttackPatternDetails,
    MalwareDetails,
    IncidentDetails,
    IdentityDetails,
    ThreatBulletinsDetails,
    CourseOfActionDetails,
    InfrastructureDetails,
    IntrusionSetDetails,
    ToolDetails,
    TTPDetails,
)
from .utils import slice_list_to_max_sublists

import pandas as pd


class ThreatFuseParser:
    """
    Siemplify Threat Fuse parser
    """

    @staticmethod
    def build_indicator_obj(objects_data, web_root):
        return Indicator(
            raw_data=objects_data,
            severity=objects_data.get("meta", {}).get("severity"),
            tags=[
                ThreatFuseParser.build_tag_obj(tag)
                for tag in (objects_data.pop("tags", []) or [])
            ],
            registrant_address=objects_data.get("meta", {}).get("registrant_address"),
            registration_created=objects_data.get("meta", {}).get(
                "registration_created"
            ),
            registration_updated=objects_data.get("meta", {}).get(
                "registration_updated"
            ),
            web_root=web_root,
            **objects_data
        )

    @staticmethod
    def build_tag_obj(tag_data):
        return Tag(raw_data=tag_data, **tag_data)

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
    def build_analysis_link_objects(analysis_links_data):
        return [
            AnalysisLink(name=key, link=value)
            for key, value in analysis_links_data.items()
        ]

    @staticmethod
    def build_alias_obj(aliases_data):
        return Association.Alias(
            alias_id=aliases_data.get("id"),
            name=aliases_data.get("name"),
            resource_uri=aliases_data.get("resource_uri"),
        )

    @staticmethod
    def build_association_obj(objects_data, web_root):

        aliases_objs = [
            ThreatFuseParser.build_alias_obj(alias)
            for alias in objects_data.get("aliases", [])
            if isinstance(alias, dict)
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
            web_root=web_root,
            **objects_data
        )

    @staticmethod
    def build_vulnerability_obj(objects_data, web_root):
        if isinstance(objects_data.get("status", {}), dict):
            status_display_name = objects_data.get("status", {}).get("display_name", "")
        else:
            status_display_name = ""

        objects_data = ThreatFuseParser.shorten_body_and_description(objects_data)

        return Vulnerability(
            raw_data=objects_data,
            web_root=web_root,
            status_display_name=status_display_name,
            **objects_data
        )

    @staticmethod
    def build_job_status_obj(job_status):
        return JobStatus(
            raw_data=job_status,
            job_id=job_status.get("job_id"),
            success=job_status.get("success", False),
            import_session_id=job_status.get("import_session_id"),
        )

    @staticmethod
    def build_job_details_obj(job_details):
        return JobDetails(raw_data=job_details, **job_details)

    @staticmethod
    def build_actor_details_obj(actor_details, web_root):

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

        actor_details = ThreatFuseParser.shorten_body_and_description(actor_details)

        return ActorDetails(
            raw_data=actor_details,
            sophistication_type_display_name=sophistication_type_display_name,
            actor_motivations=actor_details.get("motivations", []),
            aliases_obj=[
                ThreatFuseParser.build_alias_obj(alias)
                for alias in actor_details.get("aliases", [])
            ],
            web_root=web_root,
            status_display_name=status_display_name,
            **actor_details
        )

    @staticmethod
    def build_campaign_details_obj(campaign_details, web_root):

        if isinstance(campaign_details.get("status", {}), dict):
            status_display_name = campaign_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        campaign_details = ThreatFuseParser.shorten_body_and_description(
            campaign_details
        )

        return CampaignDetails(
            raw_data=campaign_details,
            aliases_obj=[
                ThreatFuseParser.build_alias_obj(alias)
                for alias in campaign_details.get("aliases", [])
            ],
            status_display_name=status_display_name,
            web_root=web_root,
            **campaign_details
        )

    @staticmethod
    def build_signature_details_obj(signature_details, web_root):

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

        signature_details = ThreatFuseParser.shorten_body_and_description(
            signature_details
        )

        return SignatureDetails(
            raw_data=signature_details,
            aliases_obj=[
                ThreatFuseParser.build_alias_obj(alias)
                for alias in signature_details.get("aliases", [])
            ],
            signature_type_name=signature_type_name,
            parent_display_name=parent_display_name,
            web_root=web_root,
            status_display_name=status_display_name,
            **signature_details
        )

    @staticmethod
    def match_entity_to_indicators(
        indicators: List[Indicator], entities: List[DomainEntityInfo]
    ) -> List[IndicatorsGroup]:
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
    def map_observables_to_feed_group(
        observables: List[Indicator],
        max_observables_per_group: int,
        source_feed_grouping: bool,
    ):
        """
        Group observables. Each group will represent an alert of max size <max_observable_per_group>,
        if source_feed_grouping is True alerts will be grouped by the same feed_id.
        :param observables: {[Indicator]} List of observables to group
        :param max_observables_per_group:  {int} max observables per group.
        :param source_feed_grouping: {bool} if True, observables will be grouped by feed_id attribute
        :return: {[[datamodels.Indicator]]} List of sublists of indicators. Each inner list represents observables that will be processed
            in the same alert as events. Max observables per group is defined by the parameter <max_observables_per_group>
        """
        if source_feed_grouping:  # sort observables by feed id
            observable_groups = []
            # split observables into groups with the same feed_d
            for feed_id, group in itertools.groupby(observables, lambda k: k.feed_id):
                # split each group to subgroups with max size <max_observables_per_group>
                for sub_group in slice_list_to_max_sublists(
                    list(group), max_observables_per_group
                ):
                    observable_groups.append(sub_group)

            return observable_groups

        return slice_list_to_max_sublists(observables, max_observables_per_group)

    @staticmethod
    def build_attackpattern_details_obj(attack_pattern_details, web_root):

        if isinstance(attack_pattern_details.get("status", {}), dict):
            status_display_name = attack_pattern_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        attack_pattern_details = ThreatFuseParser.shorten_body_and_description(
            attack_pattern_details
        )

        return AttackPatternDetails(
            raw_data=attack_pattern_details,
            web_root=web_root,
            status_display_name=status_display_name,
            **attack_pattern_details
        )

    @staticmethod
    def build_malware_details_obj(malware_details, web_root):

        if isinstance(malware_details.get("status", {}), dict):
            status_display_name = malware_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        malware_details = ThreatFuseParser.shorten_body_and_description(malware_details)

        return MalwareDetails(
            raw_data=malware_details,
            web_root=web_root,
            status_display_name=status_display_name,
            **malware_details
        )

    @staticmethod
    def build_incident_details_obj(incident_details, web_root):

        if isinstance(incident_details.get("status", {}), dict):
            status_display_name = incident_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        incident_details = ThreatFuseParser.shorten_body_and_description(
            incident_details
        )

        return IncidentDetails(
            raw_data=incident_details,
            web_root=web_root,
            status_display_name=status_display_name,
            **incident_details
        )

    @staticmethod
    def build_threat_bulletins_details_obj(threat_bulletins_details, web_root):
        if isinstance(threat_bulletins_details.get("status", {}), dict):
            status_display_name = threat_bulletins_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        threat_bulletins_details = ThreatFuseParser.shorten_body_and_description(
            threat_bulletins_details
        )

        return ThreatBulletinsDetails(
            raw_data=threat_bulletins_details,
            web_root=web_root,
            status_display_name=status_display_name,
            **threat_bulletins_details
        )

    @staticmethod
    def build_course_of_action_details_obj(course_of_action_details, web_root):
        if isinstance(course_of_action_details.get("status", {}), dict):
            status_display_name = course_of_action_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        course_of_action_details = ThreatFuseParser.shorten_body_and_description(
            course_of_action_details
        )

        return CourseOfActionDetails(
            raw_data=course_of_action_details,
            web_root=web_root,
            status_display_name=status_display_name,
            **course_of_action_details
        )

    @staticmethod
    def build_identity_details_obj(identity_details, web_root):
        if isinstance(identity_details.get("status", {}), dict):
            status_display_name = identity_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        identity_details = ThreatFuseParser.shorten_body_and_description(
            identity_details
        )

        return IdentityDetails(
            raw_data=identity_details,
            web_root=web_root,
            status_display_name=status_display_name,
            **identity_details
        )

    @staticmethod
    def build_infrastructure_details_obj(infrastructure_details, web_root):
        if isinstance(infrastructure_details.get("status", {}), dict):
            status_display_name = infrastructure_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        infrastructure_details = ThreatFuseParser.shorten_body_and_description(
            infrastructure_details
        )

        return InfrastructureDetails(
            raw_data=infrastructure_details,
            web_root=web_root,
            status_display_name=status_display_name,
            **infrastructure_details
        )

    @staticmethod
    def build_intrusionset_details_obj(intrusionset_details, web_root):
        if isinstance(intrusionset_details.get("status", {}), dict):
            status_display_name = intrusionset_details.get("status", {}).get(
                "display_name", ""
            )
        else:
            status_display_name = ""

        intrusionset_details = ThreatFuseParser.shorten_body_and_description(
            intrusionset_details
        )

        return IntrusionSetDetails(
            raw_data=intrusionset_details,
            web_root=web_root,
            status_display_name=status_display_name,
            **intrusionset_details
        )

    @staticmethod
    def build_tool_details_obj(tool_details, web_root):
        if isinstance(tool_details.get("status", {}), dict):
            status_display_name = tool_details.get("status", {}).get("display_name", "")
        else:
            status_display_name = ""

        tool_details = ThreatFuseParser.shorten_body_and_description(tool_details)

        return ToolDetails(
            raw_data=tool_details,
            web_root=web_root,
            status_display_name=status_display_name,
            **tool_details
        )

    @staticmethod
    def build_ttp_details_obj(ttp_details, web_root):
        if isinstance(ttp_details.get("status", {}), dict):
            status_display_name = ttp_details.get("status", {}).get("display_name", "")
        else:
            status_display_name = ""

        ttp_details = ThreatFuseParser.shorten_body_and_description(ttp_details)

        return TTPDetails(
            raw_data=ttp_details,
            web_root=web_root,
            status_display_name=status_display_name,
            **ttp_details
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
                raw_data.get("description", "").split(" ")[
                    : consts.MAX_DESCRIPTION_LENGTH
                ]
            )
            if splitted:
                raw_data["description"] = splitted + "..."
            else:
                raw_data["description"] = ""

        # Shorten raw body
        if isinstance(raw_data.get("body", ""), str):
            splitted = " ".join(
                raw_data.get("body", "").split(" ")[: consts.MAX_BODY_LENGTH]
            )
            if splitted:
                raw_data["body"] = splitted + "..."
            else:
                raw_data["body"] = ""

        return raw_data

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
