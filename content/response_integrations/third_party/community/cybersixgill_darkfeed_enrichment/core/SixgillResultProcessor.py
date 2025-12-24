from __future__ import annotations

import re

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import add_prefix_to_dict

STIX_REGEX_PARSER = re.compile(
    r"([\w-]+?):(\w.+?) (?:[!><]?=|IN|MATCHES|LIKE) '(.*?)' *[OR|AND|FOLLOWEDBY]?",
)


class SixgillActionResultProcessor:
    def __init__(self, siemplify, manager):
        self.siemplify = siemplify
        self.sixgill_manager = manager
        self.faild_entities = []
        self.success_entities = []
        self.no_data_entities = []
        self.filtered_keys = [
            "description",
            "sixgill_feedname",
            "sixgill_source",
            "sixgill_posttitle",
            "sixgill_actor",
            "sixgill_postid",
            "labels",
            "sixgill_confidence",
            "sixgill_severity",
            "created",
            "modified",
            "valid_from",
            "external_reference",
        ]
        self.ext_obj_keys = [
            "positive_rate",
            "url",
            "description",
            "mitre_attack_tactic",
            "mitre_attack_tactic_id",
            "mitre_attack_tactic_url",
            "mitre_attack_technique",
            "mitre_attack_technique_id",
            "mitre_attack_technique_url",
        ]
        self.table_columns = (
            "Description,Sixgill Feed Name,Sixgill Source,Sixgill Post Title,Sixgill Actor,Sixgill Post Id,Labels,"
            "Sixgill Confidence,Sixgill Severity,Created,Modified,Valid From,VirusTotal Positive Rate,VirusTotal Url,"
            "Mitre Description,Mitre Attack Tactic,Mitre Attack Tactic Id,Mitre Attack Tactic Url,Mitre Attack Technique,"
            "Mitre Attack Technique Id,Mitre Attack Technique Url"
        )

    def test_connectivity(self):
        result = False
        try:
            client_obj = self.sixgill_manager.create_sixgill_client()
            if client_obj:
                res = client_obj.enrich_ioc("ip", "8.8.8.8")
                status = EXECUTION_STATE_COMPLETED
                msg = "Successfully Connected to Sixgill"
                result = True
        except Exception as err:
            msg = f"Connectivity Failed Error - {err}"
            status = EXECUTION_STATE_FAILED
            self.siemplify.LOGGER.error(f"test_connectivity Error - {err}")
        return status, msg, result

    def format_output_message(self, output_message):
        try:
            if self.success_entities:
                output_message += f"Successfully Processed Entities - {','.join(self.success_entities)},  "
            if self.no_data_entities:
                output_message += f"Unable to find data for the following Entities - {','.join(self.no_data_entities)},  "
            if self.faild_entities:
                output_message += f"Enrichment failed for the following Entities - {','.join(self.faild_entities)}, "
            if (
                not len(self.success_entities)
                + len(self.faild_entities)
                + len(self.no_data_entities)
            ):
                output_message += "No Entities were Enriched by Action  "
        except Exception as err:
            self.siemplify.LOGGER.error(f"format_output_message Error - {err}")
        return output_message

    def create_link(self, entity, extrnal_links):
        status = False
        try:
            for link in list(set(extrnal_links)):
                self.siemplify.result.add_entity_link(entity.identifier, link)
            status = True
        except Exception as err:
            self.siemplify.LOGGER.error(f"create_link Error - {err}")
        return status

    def get_vt_mitre_obj(self, rec):
        vt_obj = {}
        mitre_obj = {}
        try:
            for item in rec.get("external_reference", []):
                if item.get("source_name") == "VirusTotal":
                    vt_obj = item
                elif item.get("source_name") == "mitre-attack":
                    mitre_obj = item
                else:
                    self.siemplify.LOGGER.warning(
                        f"Unsupported External links - {item.get('source_name', '')}",
                    )
        except Exception as err:
            self.siemplify.LOGGER.error(f"get_vt_mitre_obj Error - {err}")
        return vt_obj, mitre_obj

    def get_external_obj_details(self, entity, rec, insight_record, links, rows):
        status = False
        try:
            vt_obj, mitre_obj = self.get_vt_mitre_obj(rec)
            for key in self.ext_obj_keys:
                if key in ["positive_rate", "url"]:
                    val = vt_obj.get(key, "")
                    if val:
                        insight_record += (
                            f"VirusTotal {key.replace('_', ' ').title()}  :  {val}\n"
                        )
                        if key == "url":
                            links.append(val)
                else:
                    val = mitre_obj.get(key, "")
                    if val:
                        if not key.startswith("mitre"):
                            insight_record += (
                                f"Mitre {key.replace('_', ' ').title()}  :  {val}\n"
                            )
                        else:
                            insight_record += (
                                f"{key.replace('_', ' ').title()}  :  {val}\n"
                            )
                            if key in [
                                "mitre_attack_tactic_url",
                                "mitre_attack_technique_url",
                            ]:
                                links.append(val)
                rows.append(val)
            status = True
        except Exception as err:
            self.siemplify.LOGGER.error(f"get_external_obj_details Error - {err}")
        return status, insight_record, links, rows

    def create_table_insights(self, entity, rec):
        status = False
        insight_record = ""
        links = []
        row_data = ""
        try:
            rows = []
            for key in self.filtered_keys:
                if key == "external_reference":
                    ext_status, insight_record, links, rows = (
                        self.get_external_obj_details(
                            entity,
                            rec,
                            insight_record,
                            links,
                            rows,
                        )
                    )
                elif key == "labels":
                    val = ",".join(rec.get(key, []))
                    insight_record += f"{key.replace('_', ' ').title()}  :  {val}\n"
                    val = "|".join(rec.get(key, []))
                    rows.append(val)
                elif key == "sixgill_postid":
                    val = "https://portal.cybersixgill.com/#/search?q=_id:" + rec.get(
                        key,
                        "",
                    )
                    links.append(val)
                    insight_record += f"{key.replace('_', ' ').title()}  :  {val}\n"
                    rows.append(val)
                else:
                    val = str(rec.get(key, ""))
                    insight_record += f"{key.replace('_', ' ').title()}  :  {val}\n"
                    val = val.replace(",", " ")
                    rows.append(val)
            row_data = ",".join(rows)
            status = True
        except Exception as err:
            self.siemplify.LOGGER.error(f"create_table_insights Error - {err}")
        return status, insight_record, links, row_data

    def get_action_output(self, entity, records):
        status = False
        table = []
        insight = ""
        extrnal_links = []
        try:
            table.append(self.table_columns)
            for rec in records:
                insight_status, insight_record, links, row = self.create_table_insights(
                    entity,
                    rec,
                )
                if insight_status:
                    insight += insight_record + "\n\n\n"
                    table.append(row)
                extrnal_links.extend(links)
            link_status = self.create_link(entity, extrnal_links)
            if insight_status and link_status:
                status = True
        except Exception as err:
            self.siemplify.LOGGER.error(f"get_action_output Error - {err}")
        return status, table, insight

    def entity_data(self, entity_types):
        try:
            enriched_entities = []
            for entity in self.siemplify.target_entities:
                if entity.entity_type.upper() in entity_types:
                    try:
                        data_dict = {}
                        enrich_result = None
                        enrich_status = None
                        if entity.entity_type == EntityTypes.HOSTNAME:
                            enrich_status, enrich_result = (
                                self.sixgill_manager.query_sixgill(
                                    "domain",
                                    entity.identifier,
                                )
                            )
                        elif entity.entity_type == EntityTypes.FILEHASH:
                            enrich_status, enrich_result = (
                                self.sixgill_manager.query_sixgill(
                                    "hash",
                                    entity.identifier,
                                )
                            )
                        elif entity.entity_type == EntityTypes.ADDRESS:
                            enrich_status, enrich_result = (
                                self.sixgill_manager.query_sixgill(
                                    "ip",
                                    entity.identifier,
                                )
                            )
                        elif entity.entity_type.upper() == EntityTypes.URL.upper():
                            enrich_status, enrich_result = (
                                self.sixgill_manager.query_sixgill(
                                    "url",
                                    entity.identifier,
                                )
                            )
                        elif (
                            entity.entity_type.upper()
                            == EntityTypes.THREATACTOR.upper()
                        ):
                            enrich_status, enrich_result = (
                                self.sixgill_manager.query_sixgill(
                                    "actor",
                                    entity.identifier,
                                )
                            )
                        else:
                            self.siemplify.LOGGER.error(
                                f"Invalid Entity Type - {entity.entity_type} ",
                            )
                        if enrich_status and enrich_result:
                            entity_value = entity.identifier.strip()
                            enriched_entities.append(entity)
                            print(entity.identifier)
                            entity.is_enriched = True
                            entity.is_suspicious = True
                            for rec in enrich_result:
                                for (
                                    indicator_type,
                                    sub_type,
                                    value,
                                ) in STIX_REGEX_PARSER.findall(rec.get("pattern", "")):
                                    if indicator_type == "file":
                                        if "MD5" in sub_type:
                                            if value.upper() != entity_value.upper():
                                                data_dict["MD5"] = value
                                        if "SHA-1" in sub_type:
                                            if value.upper() != entity_value.upper():
                                                data_dict["SHA-1"] = value
                                        if "SHA-256" in sub_type:
                                            if value.upper() != entity_value.upper():
                                                data_dict["SHA-256"] = value
                                external_reference = rec.get("external_reference", [])
                                data_dict["Description"] = rec.get("description")
                                data_dict["Feedname"] = rec.get("sixgill_feedname")
                                data_dict["Source"] = rec.get("sixgill_source")
                                data_dict["Post Title"] = rec.get("sixgill_posttitle")
                                data_dict["Actor"] = rec.get("sixgill_actor")
                                data_dict["Post ID"] = (
                                    "https://portal.cybersixgill.com/#/search?q=_id:"
                                    + rec.get("sixgill_postid", "")
                                )
                                data_dict["Labels"] = ",".join(rec.get("labels"))
                                data_dict["Confidence"] = rec.get("sixgill_confidence")
                                data_dict["Severity"] = rec.get("sixgill_severity")
                                data_dict["Created"] = rec.get("created")
                                data_dict["Modified"] = rec.get("modified")
                                data_dict["Valid From"] = rec.get("valid_from")
                                for obj in external_reference:
                                    if obj.get("source_name", "") == "VirusTotal":
                                        data_dict["Virustotal PR"] = obj.get(
                                            "positive_rate",
                                        )
                                        data_dict["Virustotal Url"] = obj.get("url")
                                    if obj.get("source_name", "") == "mitre-attack":
                                        data_dict["Mitre Description"] = obj.get(
                                            "description",
                                        )
                                        data_dict["Mitre Tactic"] = obj.get(
                                            "mitre_attack_tactic",
                                        )
                                        data_dict["Mitre Tactic Id"] = obj.get(
                                            "mitre_attack_tactic_id",
                                        )
                                        data_dict["Mitre Tactic Url"] = obj.get(
                                            "mitre_attack_tactic_url",
                                        )
                            entity_dict = add_prefix_to_dict(data_dict, "Sixgill")
                            entity.additional_properties.update(entity_dict)
                            entity_dict = {}
                    except Exception as err:
                        self.siemplify.LOGGER.error(err)
            self.siemplify.update_entities(enriched_entities)
        except Exception as err:
            self.siemplify.LOGGER.error(err)

    def enrich(self, entity_types):
        result_value = False
        output_message = "Action result :  "
        status = EXECUTION_STATE_FAILED
        try:
            json_result = []
            for entity in self.siemplify.target_entities:
                enriched_entities = {}
                if entity.entity_type.upper() in entity_types:
                    try:
                        enrich_result = None
                        enrich_status = None
                        if entity.entity_type == EntityTypes.HOSTNAME:
                            enrich_status, enrich_result = (
                                self.sixgill_manager.query_sixgill(
                                    "domain",
                                    entity.identifier,
                                )
                            )
                        elif entity.entity_type == EntityTypes.FILEHASH:
                            enrich_status, enrich_result = (
                                self.sixgill_manager.query_sixgill(
                                    "hash",
                                    entity.identifier,
                                )
                            )
                        elif entity.entity_type == EntityTypes.ADDRESS:
                            enrich_status, enrich_result = (
                                self.sixgill_manager.query_sixgill(
                                    "ip",
                                    entity.identifier,
                                )
                            )
                        elif entity.entity_type.upper() == EntityTypes.URL.upper():
                            enrich_status, enrich_result = (
                                self.sixgill_manager.query_sixgill(
                                    "url",
                                    entity.identifier,
                                )
                            )
                        elif (
                            entity.entity_type.upper()
                            == EntityTypes.THREATACTOR.upper()
                        ):
                            enrich_status, enrich_result = (
                                self.sixgill_manager.query_sixgill(
                                    "actor",
                                    entity.identifier,
                                )
                            )
                        else:
                            self.siemplify.LOGGER.error(
                                f"Invalid Entity Type - {entity.entity_type} ",
                            )
                        if enrich_status and enrich_result:
                            self.success_entities.append(entity.identifier)
                            result_value = True
                            enriched_entities["entityIdentifier"] = entity.identifier
                            enriched_entities["entityResult"] = enrich_result
                            json_result.append(enriched_entities)
                            output_status, table, insight = self.get_action_output(
                                entity,
                                enrich_result,
                            )
                            if output_status:
                                self.siemplify.result.add_entity_table(
                                    entity.identifier,
                                    table,
                                )
                                self.siemplify.create_case_insight(
                                    "Sixgill",
                                    entity.identifier,
                                    insight,
                                    entity.identifier,
                                    0,
                                    1,
                                )
                                self.siemplify.result.add_json(
                                    entity.identifier,
                                    enrich_result,
                                )
                        elif enrich_status and not enrich_result:
                            self.no_data_entities.append(entity.identifier)
                    except Exception as err:
                        self.faild_entities.append(entity.identifier)
                        self.siemplify.LOGGER.error(err)
            self.siemplify.result.add_result_json(json_result)
            status = EXECUTION_STATE_COMPLETED
            output_message = self.format_output_message(output_message)
        except Exception as err:
            output_message = f"Action execution failed with Error - {err}"
            self.siemplify.LOGGER.error(f"Enrich Error - {err}")
        self.siemplify.end(output_message, result_value, status)
