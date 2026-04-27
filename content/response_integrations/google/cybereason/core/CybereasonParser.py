from __future__ import annotations
from typing import Any

from .constants import BLOCK_ACTION_LIST
from .datamodels import (
    Process,
    MalopProcess,
    Machine,
    File,
    Alert,
    MalopDetails,
    Malop,
    MachineObject,
    Reputation,
    SingleMalopProcess,
    Entity_Details,
    SingleMalopMachine,
    InvestigationSearchItem,
    Sensor,
    MalopSuspeciousDetails,
    RemediateMalop,
)

DEFAULT_ALERT_NAME = "No alert name found"
DEFAULT_RULE_GENERATOR_NAME = "No rule generator found"
DEFAULT_PRODUCT = "Azure Sentinel"
DEFAULT_VENDOR = "Microsoft"


class CybereasonParser:
    def __init__(self, siemplify_logger=None):
        self.siemplify_logger = siemplify_logger

    @staticmethod
    def construct_query_results(data):
        output = {}

        for item_name, item_value in data.get("simpleValues", {}).items():
            if item_value.get("values") and len(item_value.get("values")) == 1:
                output[item_name] = item_value.get("values")[0]

            else:
                output[item_name] = item_value.get("values")

        for item_name, item_value in data.get("elementValues", {}).items():
            output[item_name] = item_value.get("elementValues")

        return output

    @staticmethod
    def get_first_or_empty(lst):
        if not isinstance(lst, list):
            return lst if lst else {}

        if lst:
            return lst[0]

    def build_siemplify_process_obj(self, process_guid, process_data):
        constructed_data = self.construct_query_results(process_data)
        return Process(
            raw_data=process_data,
            constructed_data=constructed_data,
            guid=process_guid,
            element_name=self.get_first_or_empty(
                constructed_data.get("elementDisplayName")
            ),
            creation_time=self.get_first_or_empty(constructed_data.get("creationTime")),
            end_time=self.get_first_or_empty(constructed_data.get("endTime")),
            command=self.get_first_or_empty(constructed_data.get("commandLine")),
            signed_and_verified=self.get_first_or_empty(
                constructed_data.get("isImageFileSignedAndVerified")
            ),
            product_type=self.get_first_or_empty(constructed_data.get("productType")),
            owner_machine=self.get_first_or_empty(
                constructed_data.get("ownerMachine") or [{}]
            ).get("name"),
            user=self.get_first_or_empty(
                constructed_data.get("calculatedUser") or [{}]
            ).get("name"),
            md5=self.get_first_or_empty(constructed_data.get("imageFile.md5String")),
            execution_prevented=self.get_first_or_empty(
                constructed_data.get("executionPrevented")
            ),
            icon_base64=self.get_first_or_empty(constructed_data.get("iconBase64")),
            company_name=self.get_first_or_empty(
                constructed_data.get("imageFile.companyName")
            ),
            malicious_classification_type=self.get_first_or_empty(
                constructed_data.get("imageFile.maliciousClassificationType")
            ),
            product_name=self.get_first_or_empty(
                constructed_data.get("imageFile.productName")
            ),
            sha1_string=self.get_first_or_empty(
                constructed_data.get("imageFile.sha1String")
            ),
            is_white_list_classification=self.get_first_or_empty(
                constructed_data.get("isWhiteListClassification")
            ),
            image_file=self.get_first_or_empty(
                constructed_data.get("imageFile") or [{}]
            ).get("name"),
            parent_process=self.get_first_or_empty(
                constructed_data.get("parentProcess") or [{}]
            ).get("name"),
            children=self.get_first_or_empty(
                constructed_data.get("children") or [{}]
            ).get("name"),
            matched_white_list_rule_ids=self.get_first_or_empty(
                constructed_data.get("matchedWhiteListRuleIds")
            ),
            pid=self.get_first_or_empty(constructed_data.get("pid")),
            ransomware_auto_remediation_suspended=self.get_first_or_empty(
                constructed_data.get("ransomwareAutoRemediationSuspended")
            ),
        )

    def build_siemplify_malop_obj(self, raw_data):
        raw_data = raw_data.get("data", {}).get("resultIdToElementDataMap", {})
        malop_data = list(raw_data.values())[0]
        malop_guid = list(raw_data.keys())[0]
        constructed_data = self.construct_query_results(malop_data)
        return MalopProcess(
            raw_data=malop_data,
            constructed_data=constructed_data,
            guid=malop_guid,
            element_name=self.get_first_or_empty(
                constructed_data.get("elementDisplayName")
            ),
            detection_type=self.get_first_or_empty(
                constructed_data.get("detectionType")
            ),
            malop_activity_types=constructed_data.get("malopActivityTypes"),
            affected_machines=constructed_data.get("affectedMachines"),
            affected_users=constructed_data.get("affectedUsers"),
            root_cause_elements=constructed_data.get("rootCauseElements"),
        )

    def build_siemplify_single_malop_object(self, raw_data):
        return Malop(
            raw_data=raw_data,
            element_name=raw_data.get("displayName"),
            detection_type=raw_data.get("malopDetectionType"),
            malop_activity_types=raw_data.get("malopActivityTypes"),
            affected_machines=raw_data.get("machines", []),
            affected_users=raw_data.get("users", []),
            root_cause_elements_length=raw_data.get("rootCauseElementNamesCount"),
            file_suspects=raw_data.get("fileSuspects", []),
            process_suspects=raw_data.get("processSuspects", []),
            connections=raw_data.get("connections", []),
            timeline_events=raw_data.get("timelineEvents", []),
            updating_time=raw_data.get("lastUpdateTime"),
        )

    def build_siemplify_machine_object(self, raw_data):
        raw_data = raw_data.get("data", {}).get("resultIdToElementDataMap", {})
        machine_data = list(raw_data.values())[0]
        machine_guid = list(raw_data.keys())[0]
        constructed_data = self.construct_query_results(machine_data)
        return MachineObject(
            raw_data=machine_data,
            constructed_data=constructed_data,
            guid=machine_guid,
            is_isolated=True if constructed_data.get("isIsolated") == "true" else False,
            pylum_id=constructed_data.get("pylumId"),
            element_name=self.get_first_or_empty(
                constructed_data.get("elementDisplayName")
            ),
            os_version=self.get_first_or_empty(constructed_data.get("osVersionType")),
            platform_arch=self.get_first_or_empty(
                constructed_data.get("platformArchitecture")
            ),
            uptime=self.get_first_or_empty(constructed_data.get("uptime")),
            is_connected=self.get_first_or_empty(
                constructed_data.get("isActiveProbeConnected")
            ),
            last_seen=self.get_first_or_empty(
                constructed_data.get("lastSeenTimeStamp")
            ),
        )

    def build_siemplify_machine_obj(self, machine_guid, machine_data):
        constructed_data = self.construct_query_results(machine_data)
        return Machine(
            raw_data=machine_data,
            constructed_data=constructed_data,
            guid=machine_guid,
            element_name=self.get_first_or_empty(
                constructed_data.get("elementDisplayName")
            ),
            os_version=self.get_first_or_empty(constructed_data.get("osVersionType")),
            os_type=self.get_first_or_empty(constructed_data.get("osType")),
            dns_hostname=self.get_first_or_empty(constructed_data.get("adDNSHostName")),
            isolated=self.get_first_or_empty(constructed_data.get("isIsolated")),
            users=machine_data.get("elementValues", {})
            .get("users", {})
            .get("totalValues"),
            network_interfaces=machine_data.get("elementValues", {})
            .get("networkInterfaces", {})
            .get("totalValues"),
            logon_sessions=machine_data.get("elementValues", {})
            .get("logonSessions", {})
            .get("totalValues"),
            platform_arch=self.get_first_or_empty(
                constructed_data.get("platformArchitecture")
            ),
            uptime=self.get_first_or_empty(constructed_data.get("uptime")),
            is_connected=self.get_first_or_empty(
                constructed_data.get("isActiveProbeConnected")
            ),
            last_seen=self.get_first_or_empty(
                constructed_data.get("lastSeenTimeStamp")
            ),
            is_malicious=machine_data.get("isMalicious"),
        )

    def build_siemplify_file_obj(self, file_guid, file_data):
        constructed_data = self.construct_query_results(file_data)
        return File(
            raw_data=file_data,
            constructed_data=constructed_data,
            guid=file_guid,
            element_name=self.get_first_or_empty(
                constructed_data.get("elementDisplayName")
            ),
            md5=self.get_first_or_empty(constructed_data.get("md5String")),
            sha1=self.get_first_or_empty(constructed_data.get("sha1String")),
            size=self.get_first_or_empty(constructed_data.get("size")),
            path=self.get_first_or_empty(constructed_data.get("correctedPath")),
            owner_machine=self.get_first_or_empty(
                constructed_data.get("ownerMachine") or [{}]
            ).get("name"),
            is_signed=self.get_first_or_empty(constructed_data.get("isSigned")),
            signature_verified=self.get_first_or_empty(
                constructed_data.get("signatureVerified")
            ),
            malicious_classification_type=self.get_first_or_empty(
                constructed_data.get("maliciousClassificationType")
            ),
            product_name=self.get_first_or_empty(constructed_data.get("productName")),
            product_version=self.get_first_or_empty(
                constructed_data.get("productVersion")
            ),
            company_name=self.get_first_or_empty(constructed_data.get("companyName")),
            internal_name=self.get_first_or_empty(constructed_data.get("internalName")),
            creation_time=self.get_first_or_empty(constructed_data.get("createdTime")),
            modified_time=self.get_first_or_empty(constructed_data.get("modifiedTime")),
            av_remediation_status=self.get_first_or_empty(
                constructed_data.get("avRemediationStatus")
            ),
        )

    def build_all_alerts(self, raw_json):
        return [
            self.build_alert_object(alert_json=alert_data)
            for alert_data in raw_json.get("malops", [])
        ]

    def build_alert_object(self, alert_json):
        return Alert(
            raw_data=alert_json,
            guid=alert_json.get("guid"),
            display_name=alert_json.get("displayName"),
            detection_types=alert_json.get("detectionTypes", []),
            severity=alert_json.get("severity", "N/A"),
            malop_detection_type=alert_json.get("malopDetectionType"),
            creation_time=alert_json.get("creationTime"),
            updating_time=alert_json.get("lastUpdateTime"),
            status=alert_json.get("status"),
            machines=alert_json.get("machines", []),
            users=alert_json.get("users", []),
        )

    def build_malop_details_obj(self, raw_data):
        return MalopDetails(
            raw_data=raw_data,
            element_type=raw_data.get("elementType"),
            name=raw_data.get("name"),
        )

    def build_malop_details_list(self, raw_data, malop_guid):
        main_values = (
            raw_data.get("data", {})
            .get("resultIdToElementDataMap", {})
            .get(malop_guid, {})
            .get("elementValues", {})
        )
        element_values = []
        for key, value in main_values.items():
            for item in value.get("elementValues", []):
                if not next(
                    (
                        val
                        for val in element_values
                        if val.get("name") == item.get("name")
                    ),
                    None,
                ):
                    element_values.append(item)

        return [
            self.build_malop_details_obj(element_value)
            for element_value in element_values
        ]

    def get_outcome_value(self, raw_data):
        return raw_data.get("outcome", "")

    def get_data(self, raw_json):
        return raw_json.get("data") or {}

    def get_result_id_to_element_data_map(self, raw_data):
        return self.get_data(raw_data).get("resultIdToElementDataMap", {})

    def build_siemplify_obj(self, raw_json):
        data = self.get_result_id_to_element_data_map(raw_json)
        return [
            self.build_siemplify_file_obj(file_guid, file_data)
            for file_guid, file_data in data.items()
        ]

    def get_responsne_status(self, raw_data):
        return raw_data.get("status", "")

    def build_siemplify_reputation_obj(self, result):
        return Reputation(
            raw_data=result,
            key=result.get("key"),
            reputation=result.get("reputation"),
            prevent_execution=result.get("prevent execution"),
            comment=result.get("comment"),
            remove=result.get("remove"),
        )

    def get_machine_update_status(self, raw_data, machine_id):
        return raw_data.get(machine_id, "")

    def get_process_suspects(self, raw_json):
        return raw_json.get("processSuspects", []) or []

    def get_machines(self, raw_json):
        return raw_json.get("machines", [])

    def build_siemplify_single_malop_machine_object(self, raw_data):
        return SingleMalopMachine(
            raw_data=raw_data,
            element_name=raw_data.get("displayName", ""),
            os_version=raw_data.get("osType", ""),
            is_connected=raw_data.get("connected", ""),
            last_seen=raw_data.get("lastConnected", ""),
        )

    def build_siemplify_single_malop_process_object(self, raw_data):
        return SingleMalopProcess(
            raw_data=raw_data,
            clas=raw_data.get("@class"),
            first_seen=raw_data.get("firstSeen"),
            last_seen=raw_data.get("lastSeen"),
            counter=raw_data.get("counter"),
            was_ever_detected_in_scan=raw_data.get("wasEverDetectedInScan"),
            was_ever_detected_by_access=raw_data.get("wasEverDetectedByAccess"),
            detection_decision_status=raw_data.get("detectionDecisionStatus"),
            guid=raw_data.get("processGuid"),
            element_display_name=raw_data.get("elementDisplayName"),
            command=raw_data.get("commandLine"),
            creation_time=raw_data.get("creationTime"),
            end_time=raw_data.get("endTime"),
            pid=raw_data.get("pid"),
            owner_machine=raw_data.get("ownerMachine"),
            user=raw_data.get("calculatedUser"),
        )

    def build_siemplify_entity_details_obj(self, raw_json):
        return Entity_Details(
            raw_data=raw_json,
            type=raw_json.get("aggregatedResult", {})
            .get("maliciousClassification", {})
            .get("type"),
        )

    def get_classification_responses(self, raw_json):
        return raw_json.get("classificationResponses", [])

    def build_investigation_search_item_objects(self, raw_data):
        raw_data = list(
            raw_data.get("data", {}).get("resultIdToElementDataMap", {}).values()
        )
        return [self.build_investigation_search_item_object(item) for item in raw_data]

    @staticmethod
    def get_transformed_element_values(element_values_raw_data: dict) -> dict:
        transformed_data = {}

        for key, value in element_values_raw_data.items():
            if isinstance(value, dict):
                element_values = value.get("elementValues", [])
                if element_values:
                    transformed_data[key] = element_values

        return transformed_data

    @classmethod
    def build_investigation_search_item_object(
        cls, raw_data
    ) -> InvestigationSearchItem:
        element_values_raw_data = raw_data.get("elementValues", {})

        transformed_element_values = cls.get_transformed_element_values(
            element_values_raw_data
        )

        return InvestigationSearchItem(
            raw_data=raw_data,
            simple_values=raw_data.get("simpleValues", {}),
            element_values=transformed_element_values,
        )

    def build_siemplify_sensor_obj(self, result):
        sensors = result.get("sensors", [])
        if sensors:
            raw_data = sensors[0]
            return Sensor(
                raw_data=raw_data,
                guid=raw_data.get("guid"),
                status=raw_data.get("status"),
                group_name=raw_data.get("groupName"),
                policy_name=raw_data.get("policyName"),
                isolated=raw_data.get("isolated"),
                pylum_id=raw_data.get("pylumId"),
                internal_ip_address=raw_data.get("internalIpAddress"),
                machine_name=raw_data.get("machineName"),
                fqdn=raw_data.get("fqdn"),
                service_status=raw_data.get("serviceStatus"),
                os_type=raw_data.get("osType"),
                site=raw_data.get("siteName"),
                uptime=raw_data.get("upTime"),
            )

    def build_malop_suspecious_details_obj(self, raw_data):
        return MalopSuspeciousDetails(
            raw_data=raw_data,
            unique_id=raw_data.get("uniqueId"),
            remediation_type=raw_data.get("remediationType"),
            target_name=raw_data.get("targetName"),
            target_id=raw_data.get("targetId"),
            machine_name=raw_data.get("machineName"),
            machine_id=raw_data.get("machineId"),
            **raw_data,
        )

    def get_malop_suspecious_process_details(
        self, raw_data: dict[str, Any], malop_id: str
    ) -> list[MalopSuspeciousDetails]:
        """Get malop suspecious processes with provided malop id.

        Args:
            raw_data (dict[str, Any]): Json data from response.json().
            malop_guid (str): Malop GUID

        Returns:
            list[MalopSuspeciousDetails]: list of MalopSuspeciousDetails object.
        """
        file_data = []
        element_data = raw_data.get("data", {})

        for data in element_data:
            file_data.append(self.build_malop_suspecious_details_obj(data))

        return file_data

    def build_remediate_object(
        self, raw_data: dict[str, Any], remediation_type
    ) -> RemediateMalop:
        """RemediateMalop object creation on the remediate raw json data.

        Args:
            raw_data (dict): Raw json data from response for remediate API.

        Returns:
            Endpoint: datamodle.RemediateMalop object.
        """
        if remediation_type in BLOCK_ACTION_LIST:
            return RemediateMalop(raw_data=raw_data)
        else:
            element_data = raw_data.get("data", [])
            if element_data:
                element_data = element_data[0]
                return RemediateMalop(
                    raw_data=element_data,
                    remediation_id=element_data.get("remediationId"),
                )
