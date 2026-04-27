from __future__ import annotations
from .datamodels import *
from datetime import datetime
from .consts import THREAT_CONTEXT


class BlueLivParser:

    @staticmethod
    def build_siemplify_comment_object(raw_data):
        timestamp = raw_data.get("creationDate") / 1000  # miliseconds to seconds
        creation_date = datetime.utcfromtimestamp(timestamp).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        return CommentObject(
            raw_data=raw_data,
            comment_row=raw_data.get("row"),
            comment_id=raw_data.get("id"),
            content=raw_data.get("content"),
            creation_date=creation_date,
            commenter=raw_data.get("creationUsername"),
        )

    @staticmethod
    def build_siemplify_label_object(raw_data):

        return [
            LabelsObject(
                raw_data=label,
                label_id=label.get("id"),
                label_name=label.get("label"),
                label_module_id=label.get("moduleId"),
            )
            for label in raw_data
        ]

    def build_all_threats(self, raw_json):
        threats_data = raw_json.get("list", [])
        return [self.build_siemplify_threat_object(data) for data in threats_data]

    def build_siemplify_threat_object(self, threat_data):
        return ThreatObject(
            raw_data=threat_data,
            id=threat_data.get("id"),
            module_id=threat_data.get("module_id"),
            module_type=threat_data.get("module_type"),
            title=threat_data.get("title"),
            module_name=threat_data.get("module_name"),
            created_at=threat_data.get("created_at"),
            changed_at=threat_data.get("changed_at"),
            labels=threat_data.get("labels"),
        )

    def build_siemplify_extradata_object(self, raw_json, module_type):
        return ExtraDataObject(raw_data=raw_json, module_type=module_type)

    def build_siemplify_malware_object(self, malware_data):
        return MalwareObject(
            raw_data=malware_data,
            id=malware_data.get("id"),
            hosts=malware_data.get("malwareExtraInfo", {}).get("hosts", []),
            module_id=malware_data.get("reputationalSearchId"),
            module_type=malware_data.get("moduleType"),
            title=malware_data.get("title"),
            module_name=malware_data.get("moduleName"),
            created_at=malware_data.get("createdAt"),
            changed_at=malware_data.get("changedAt"),
            checked_at=malware_data.get("checkedAt"),
        )

    def build_siemplify_ip_object(self, data, link):
        return IPObject(
            raw_data=data,
            id=data.get("data", {}).get("id"),
            asn_number=data.get("data", {}).get("attributes", {}).get("asn_number"),
            asn_owner=data.get("data", {}).get("attributes", {}).get("asn_owner"),
            latitude=data.get("data", {}).get("attributes", {}).get("latitude"),
            longtitude=data.get("data", {}).get("attributes", {}).get("longitude"),
            tlp=data.get("data", {}).get("attributes", {}).get("tlp"),
            last_seen=data.get("data", {}).get("attributes", {}).get("last_seen"),
            first_seen=data.get("data", {}).get("attributes", {}).get("first_seen"),
            risk=round(data.get("data", {}).get("attributes", {}).get("risk"), 2),
            tags=data.get("data", {}).get("attributes", {}).get("slugs_tags"),
            link=f"{link}{data.get('data',{}).get('id')}",
        )

    def build_siemplify_hash_object(self, data, link):
        return HashObject(
            raw_data=data,
            id=data.get("data", {}).get("id"),
            filetype=data.get("data", {}).get("attributes", {}).get("file_type"),
            subtype=data.get("data", {}).get("attributes", {}).get("subtype"),
            md5=data.get("data", {}).get("attributes", {}).get("md5"),
            sha1=data.get("data", {}).get("attributes", {}).get("sha1"),
            sha256=data.get("data", {}).get("attributes", {}).get("sha256"),
            sha512=data.get("data", {}).get("attributes", {}).get("sha512"),
            sources_representation=(
                ", ".join(
                    data.get("data", {})
                    .get("attributes", {})
                    .get("sources_representation")
                )
                if data.get("data", {})
                .get("attributes", {})
                .get("sources_representation")
                else None
            ),
            tlp=data.get("data", {}).get("attributes", {}).get("tlp"),
            last_seen=data.get("data", {}).get("attributes", {}).get("last_seen"),
            first_seen=data.get("data", {}).get("attributes", {}).get("first_seen"),
            risk=round(data.get("data", {}).get("attributes", {}).get("risk"), 2),
            tags=data.get("data", {}).get("attributes", {}).get("slugs_tags"),
            link=f"{link}{data.get('data',{}).get('id')}",
        )

    def build_siemplify_url_object(self, data, link):
        return URLObject(
            raw_data=data,
            id=data.get("data", {}).get("id"),
            bots_count=data.get("data", {}).get("attributes", {}).get("bots_count"),
            credentials_count=data.get("data", {})
            .get("attributes", {})
            .get("credentials_count"),
            credit_cards_count=data.get("data", {})
            .get("attributes", {})
            .get("credit_cards_count"),
            status=data.get("data", {}).get("attributes", {}).get("status"),
            main_type=data.get("data", {}).get("attributes", {}).get("main_type"),
            tlp=data.get("data", {}).get("attributes", {}).get("tlp"),
            last_seen=data.get("data", {}).get("attributes", {}).get("last_seen"),
            first_seen=data.get("data", {}).get("attributes", {}).get("first_seen"),
            risk=round(data.get("data", {}).get("attributes", {}).get("risk"), 2),
            tags=data.get("data", {}).get("attributes", {}).get("slugs_tags"),
            link=f"{link}{data.get('data',{}).get('id')}",
        )

    def build_siemplify_threat_actor_object(self, data, link):

        return ThreatActorObject(
            raw_data=data,
            id=data.get("data", {}).get("id"),
            active=data.get("data", {}).get("attributes", {}).get("active"),
            aliases=(
                ", ".join(data.get("data", {}).get("attributes", {}).get("aliases"))
                if data.get("data", {}).get("attributes", {}).get("aliases")
                else None
            ),
            country_name=data.get("data", {}).get("attributes", {}).get("country_name"),
            status=data.get("data", {}).get("attributes", {}).get("status"),
            modus_operandi=data.get("data", {})
            .get("attributes", {})
            .get("modus_operandi")
            .strip("<p>")
            .strip("</p>"),
            objective=data.get("data", {})
            .get("attributes", {})
            .get("objective")
            .strip("<p>")
            .strip("</p>"),
            tlp=data.get("data", {}).get("attributes", {}).get("tlp"),
            last_seen=data.get("data", {}).get("attributes", {}).get("last_seen"),
            first_seen=data.get("data", {}).get("attributes", {}).get("first_seen"),
            sophistication=data.get("data", {})
            .get("attributes", {})
            .get("sophistication"),
            types=(
                ", ".join(data.get("data", {}).get("attributes", {}).get("types"))
                if data.get("data", {}).get("attributes", {}).get("types")
                else None
            ),
            link=f"{link}{data.get('data',{}).get('id')}",
        )

    def build_siemplify_threat_object_details_object(self, data):
        return ThreatObjectDetailsObject(
            raw_data=data, id=data.get("data", {})[0].get("id")
        )

    def build_siemplify_threat_campaign_object(self, data, link):
        return ThreatCampaignObject(
            raw_data=data,
            id=data.get("data", {}).get("id"),
            tlp=data.get("data", {}).get("attributes", {}).get("tlp"),
            last_seen=data.get("data", {}).get("attributes", {}).get("last_seen"),
            first_seen=data.get("data", {}).get("attributes", {}).get("first_seen"),
            link=f"{link}{data.get('data',{}).get('id')}",
        )

    def build_siemplify_threat_signature_object(self, data, link):
        return ThreatSignatureObject(
            raw_data=data,
            id=data.get("data", {}).get("id"),
            signature=data.get("data", {}).get("attributes", {}).get("signature"),
            status=data.get("data", {}).get("attributes", {}).get("status"),
            threat_type=data.get("data", {}).get("attributes", {}).get("type"),
            created_at=data.get("data", {}).get("attributes", {}).get("created_at"),
            tlp=data.get("data", {}).get("attributes", {}).get("tlp"),
            link=f"{link}{data.get('data',{}).get('id')}",
            tags=data.get("data", {}).get("attributes", {}).get("slugs_tags"),
        )

    def build_siemplify_cve_object(self, data, link):
        return CVEObject(
            raw_data=data,
            id=data.get("data", {}).get("id"),
            bl_score=data.get("data", {}).get("attributes", {}).get("bl_score"),
            cvss_v2_accessComplexity=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v2", {})
            .get("accessComplexity"),
            cvss_v2_accessVector=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v2", {})
            .get("accessVector"),
            cvss_v2_authentication=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v2", {})
            .get("authentication"),
            cvss_v2_availabilityImpact=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v2", {})
            .get("availabilityImpact"),
            cvss_v2_baseScore=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v2", {})
            .get("baseScore"),
            cvss_v2_confidentialityImpact=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v2", {})
            .get("confidentialityImpact"),
            cvss_v2_integrityImpact=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v2", {})
            .get("integrityImpact"),
            cvss_v2_vectorString=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v2", {})
            .get("vectorString"),
            cvss_v3_accessComplexity=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v3", {})
            .get("accessComplexity"),
            cvss_v3_accessVector=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v3", {})
            .get("accessVector"),
            cvss_v3_privilegesRequired=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v3", {})
            .get("privilegesRequired"),
            cvss_v3_availabilityImpact=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v3", {})
            .get("availabilityImpact"),
            cvss_v3_baseScore=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v3", {})
            .get("baseScore"),
            cvss_v3_baseSeverity=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v3", {})
            .get("baseSeverity"),
            cvss_v3_confidentialityImpact=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v3", {})
            .get("confidentialityImpact"),
            cvss_v3_integrityImpact=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v3", {})
            .get("integrityImpact"),
            cvss_v3_vectorString=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v3", {})
            .get("vectorString"),
            cvss_v3_scope=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v3", {})
            .get("scope"),
            cvss_v3_userInteraction=data.get("data", {})
            .get("attributes", {})
            .get("cvss", {})
            .get("v3", {})
            .get("userInteraction"),
            exploits_name=data.get("data", {})
            .get("attributes", {})
            .get("exploits_name"),
            status=data.get("data", {}).get("attributes", {}).get("status"),
            remote=data.get("data", {}).get("attributes", {}).get("remote"),
            score=data.get("data", {}).get("attributes", {}).get("score"),
            tlp=data.get("data", {}).get("attributes", {}).get("tlp"),
            tags=data.get("data", {}).get("attributes", {}).get("tags_slugs"),
            updated_at=data.get("data", {}).get("attributes", {}).get("updated_at"),
            created_at=data.get("data", {}).get("attributes", {}).get("created_at"),
            link=f"{link}{data.get('data',{}).get('id')}",
        )

    def get_threat_context_id(self, data, module_id=None, module_type=None):

        if module_id is not None and module_type is not None:
            # used for validation of module type and ID
            for bluelive_module in data:
                if (
                    bluelive_module.get("type") == module_type
                    and bluelive_module.get("id") == module_id
                ):
                    return True

        else:
            # used to get the threat context module ID
            for bluelive_module in data:
                if bluelive_module.get("type") == THREAT_CONTEXT:
                    return bluelive_module.get("id")

        return None

    def build_siemplify_entity_object(self, data, module_filter, label_filter):

        entity_objects = []

        for list_item in data.get("list"):

            module_name = list_item.get("module_name")
            labels = [
                label_name.get("name") for label_name in list_item.get("labels", [])
            ]

            # If Module filter is specified but no label filter is specified
            if module_filter is not None and label_filter is None:
                module_filter_list = [
                    module.strip() for module in module_filter.split(",")
                ]

                if module_name not in module_filter_list:
                    continue

            # If label filter is specified but no module filter is specified
            if label_filter is not None and module_filter is None:
                label_filter_list = [label.strip() for label in label_filter.split(",")]
                if len(list(set(labels) & set(label_filter_list))) == 0:
                    continue

            # If label filter is specified and module filter is specified
            if label_filter is not None and module_filter is not None:
                label_filter_list = [label.strip() for label in label_filter.split(",")]
                module_filter_list = [
                    module.strip() for module in module_filter.split(",")
                ]
                if (
                    module_name not in module_filter_list
                    or len(list(set(labels) & set(label_filter_list))) == 0
                ):
                    continue

            entity_objects.append(
                EntityObject(
                    raw_data=list_item,
                    module_name=module_name,
                    url=list_item.get("url"),
                    title=list_item.get("title", {}),
                    labels=",".join(labels),
                    creation_date=list_item.get("created_at", {}),
                )
            )

        return entity_objects
