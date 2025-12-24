from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyDataModel import EntityTypes


class SixgillActionResultProcessor:
    def __init__(self, siemplify, manager):
        self.siemplify = siemplify
        self.sixgill_manager = manager
        self.table_columns = (
            "Description, Created, Modified, Sixgill DVE Score Current,"
            "Sixgill DVE Score Highest Ever Date, Sixgill DVE Score Highest Ever, Sixgill Previously Exploited Probability,"
            "Event Name, Event Type, NVD Link, NVD Last Modified Date, NVD Publication Date,"
            "CVSS 2_0 Score, CVSS 2_0 Severity, NVD Vector V2_0, CVSS 3_1 Score, CVSS 3_1 Severity, NVD Vector V3_1"
        )

    def create_insights(self, event_obj):
        insight_record = ""
        try:
            x_sixgill_info = event_obj.get("x_sixgill_info", {})
            sixgill_nvd = x_sixgill_info.get("nvd", {})
            desc = event_obj.get("description", "")
            insight_record += f"Description: {desc}\n"
            cre = event_obj.get("created", "")
            insight_record += f"Created: {cre}\n"
            mod = sixgill_nvd.get("modified", "")
            insight_record += f"Modified: {mod}\n"
            current = x_sixgill_info.get("score", {}).get("current", "")
            insight_record += f"Sixgill DVE Score Current: {current}\n"
            high_date = (
                x_sixgill_info.get("score", {}).get("highest", {}).get("date", "")
            )
            insight_record += f"Sixgill DVE Score Highest Ever Date: {high_date}\n"
            high_val = (
                x_sixgill_info.get("score", {}).get("highest", {}).get("value", "")
            )
            insight_record += f"Sixgill DVE Score Highest Ever: {high_val}\n"
            prev_exp = x_sixgill_info.get("score", {}).get("previouslyExploited", "")
            insight_record += f"Sixgill Previously Exploited Probability: {prev_exp}\n"
            eve_name = event_obj.get("name", "")
            insight_record += f"Event Name: {eve_name}\n"
            eve_type = event_obj.get("type", "")
            insight_record += f"Event Type: {eve_type}\n"
            nvd_link = x_sixgill_info.get("nvd", {}).get("link", "")
            insight_record += f"NVD Link: {nvd_link}\n"
            nvd_mod = sixgill_nvd.get("modified", "")
            insight_record += f"NVD Last Modified Date: {nvd_mod}\n"
            nvd_pub = sixgill_nvd.get("published", "")
            insight_record += f"NVD Publication Date: {nvd_pub}\n"
            cv2_score = sixgill_nvd.get("v2", {}).get("exploitabilityScore", "")
            insight_record += f"CVSS 2.0 Score: {cv2_score}\n"
            cv2_severity = sixgill_nvd.get("v2", {}).get("severity", "")
            insight_record += f"CVSS 2.0 Severity: {cv2_severity}\n"
            nvd_vectorv2 = sixgill_nvd.get("v2", {}).get("vector", "")
            insight_record += f"NVD Vector V2.0: {nvd_vectorv2}\n"
            cv3_score = sixgill_nvd.get("v3", {}).get("exploitabilityScore", "")
            insight_record += f"CVSS 2.0 Score: {cv3_score}\n"
            cv3_severity = sixgill_nvd.get("v3", {}).get("severity", "")
            insight_record += f"CVSS 2.0 Severity: {cv3_severity}\n"
            nvd_vectorv3 = sixgill_nvd.get("v3", {}).get("vector", "")
            insight_record += f"NVD Vector V2.0: {nvd_vectorv3}\n"
        except Exception as err:
            self.siemplify.LOGGER.error(err)
        return insight_record

    def entity_data(self, stix_obj):
        indicator = {}
        try:
            ext_obj = stix_obj.get("external_references", [])
            event_obj = stix_obj.get("x_sixgill_info", {}).get("event", {})
            nvd_obj = stix_obj.get("x_sixgill_info", {}).get("nvd", {})
            nvd_obj_v2 = stix_obj.get("x_sixgill_info", {}).get("nvd", {}).get("v2", {})
            nvd_obj_v3 = stix_obj.get("x_sixgill_info", {}).get("nvd", {}).get("v3", {})
            score_obj = stix_obj.get("x_sixgill_info", {}).get("score", {})
            indicator["value"] = ext_obj[0].get("external_id")
            indicator["Description"] = stix_obj.get("description", "")
            indicator["Created"] = stix_obj.get("created", "")
            indicator["Modified"] = stix_obj.get("modified", "")
            indicator["Cybersixgill_DVE_score_current"] = score_obj.get("current", "")
            indicator["Cybersixgill_DVE_score_highest_ever_date"] = score_obj.get(
                "highest",
                {},
            ).get("date", "")
            indicator["Cybersixgill_DVE_score_highest_ever"] = score_obj.get(
                "highest",
                {},
            ).get("value", "")
            indicator["Cybersixgill_Previously_exploited_probability"] = score_obj.get(
                "previouslyExploited",
                "",
            )
            indicator["Previous_Level"] = event_obj.get("prev_level", "")
            indicator["CVSS_3_1_score"] = nvd_obj_v3.get("exploitabilityScore", "")
            indicator["CVSS_3_1_severity"] = nvd_obj_v3.get("severity", "")
            indicator["NVD_Link"] = nvd_obj.get("link", "")
            indicator["NVD_last_modified_date"] = nvd_obj.get("modified", "")
            indicator["NVD_publication_date"] = nvd_obj.get("published", "")
            indicator["CVSS_2_0_score"] = nvd_obj_v2.get("exploitabilityScore", "")
            indicator["CVSS_2_0_severity"] = nvd_obj_v2.get("severity", "")
            indicator["NVD_Vector_V2_0"] = nvd_obj_v2.get("vector", "")
            indicator["NVD_Vector_V3_1"] = nvd_obj_v3.get("vector", "")
        except Exception as err:
            self.siemplify.LOGGER.error(err)
        return indicator

    def create_table(self, stix_obj):
        table_data = []
        table_data.append(self.table_columns)
        try:
            x_sixgill_info = stix_obj.get("x_sixgill_info", {})
            sixgill_nvd = x_sixgill_info.get("nvd", {})
            table_rows = []
            row_data = ""
            table_rows.append(stix_obj.get("description", ""))
            table_rows.append(stix_obj.get("created", ""))
            table_rows.append(sixgill_nvd.get("modified", ""))
            currentScore = x_sixgill_info.get("score", {}).get("current", "")
            table_rows.append(str(currentScore))
            table_rows.append(
                x_sixgill_info.get("score", {}).get("highest", {}).get("date", ""),
            )
            highestEverValue = (
                x_sixgill_info.get("score", {}).get("highest", {}).get("value", "")
            )
            table_rows.append(str(highestEverValue))
            exploitabilityScore = x_sixgill_info.get("score", {}).get(
                "previouslyExploited",
                "",
            )
            table_rows.append(str(exploitabilityScore))
            table_rows.append(stix_obj.get("name", ""))
            table_rows.append(stix_obj.get("type", ""))
            table_rows.append(sixgill_nvd.get("link", ""))
            table_rows.append(sixgill_nvd.get("modified", ""))
            table_rows.append(sixgill_nvd.get("published", ""))
            v2score = sixgill_nvd.get("v2", {}).get("exploitabilityScore", "")
            table_rows.append(str(v2score))
            table_rows.append(sixgill_nvd.get("v2", {}).get("severity", ""))
            table_rows.append(sixgill_nvd.get("v2", {}).get("vector", ""))
            v3score = sixgill_nvd.get("v3", {}).get("exploitabilityScore", "")
            table_rows.append(str(v3score))
            table_rows.append(sixgill_nvd.get("v3", {}).get("severity", ""))
            table_rows.append(sixgill_nvd.get("v3", {}).get("vector", ""))
            row_data = ",".join(table_rows)
            table_data.append(row_data)
        except Exception as err:
            self.siemplify.LOGGER.error(err)
        return table_data

    def entity_enrich(self):
        for entity in self.siemplify.target_entities:
            try:
                if entity.entity_type == EntityTypes.CVE:
                    enrich_result = self.sixgill_manager.query_sixgill(
                        entity.identifier,
                    )
                else:
                    self.siemplify.LOGGER.error(
                        f"Invalid Entity Type - {entity.entity_type} ",
                    )
                if enrich_result:
                    entity_dict = self.entity_data(enrich_result)
                    print(entity_dict)
            except Exception as err:
                self.siemplify.LOGGER.error(err)
            return entity_dict

    def enrich(self):
        result_value = False
        output_message = "Action result :  "
        status = EXECUTION_STATE_FAILED
        json_result = []
        enriched_entities = {}
        for entity in self.siemplify.target_entities:
            try:
                enrich_result = None
                if entity.entity_type == EntityTypes.CVE:
                    enrich_result = self.sixgill_manager.query_sixgill(
                        entity.identifier,
                    )
                else:
                    self.siemplify.LOGGER.error(
                        f"Invalid Entity Type - {entity.entity_type} ",
                    )
                if enrich_result:
                    entity_dict = self.entity_data(enrich_result)
                    enriched_entities["entityIdentifier"] = entity.identifier
                    enriched_entities["entityResult"] = enrich_result
                    json_result.append(enriched_entities)
                    insight = self.create_insights(enrich_result)
                    final_table = self.create_table(enrich_result)
                    self.siemplify.create_case_insight(
                        "Cybersixgill",
                        entity.identifier,
                        insight,
                        entity.identifier,
                        0,
                        1,
                    )
                    self.siemplify.result.add_entity_table(
                        entity.identifier,
                        final_table,
                    )
                    self.siemplify.result.add_json(entity.identifier, enrich_result)
                self.siemplify.result.add_result_json(json.dumps(json_result))
                status = EXECUTION_STATE_COMPLETED
                output_message = "Entity Successfully Enriched"
                result_value = True
            except Exception as err:
                self.siemplify.LOGGER.error(err)
        self.siemplify.end(output_message, result_value, status)
