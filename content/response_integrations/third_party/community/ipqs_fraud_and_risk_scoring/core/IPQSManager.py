from __future__ import annotations

import re

import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import add_prefix_to_dict

PROVIDER = "IPQS Fraud and Risk Scoring"
BASE_URL = "https://ipqualityscore.com/api/json/"
IP_ENDPOINT = "ip"
URL_ENDPOINT = "url"
EMAIL_ENDPOINT = "email"
PHONE_ENDPOINT = "phone"
EMAIL_REGEX = r"\b[^@]{1,64}@[^@]{1,253}\.[^@]+\b"


class IPQSManager:
    def __init__(self, siemplify, api_key, data_json):
        self.api_key = api_key
        self.data_json = data_json
        self.siemplify = siemplify
        self.failed_entities = []
        self.success_entities = []
        self.no_data_entities = []
        self.ipqs_con_issues = []
        self.clean = "CLEAN"
        self.low = "LOW RISK"
        self.medium = "MODERATE RISK"
        self.high = "HIGH RISK"
        self.critical = "CRITICAL"
        self.invalid = "INVALID"
        self.suspicious = "SUSPICIOUS"
        self.malware = "CRITICAL"
        self.phishing = "CRITICAL"
        self.disposable = "CRITICAL"
        self.is_suspicious = False
        self.ip_data_items = [
            "fraud_score",
            "country_code",
            "region",
            "city",
            "zip_code",
            "ISP",
            "ASN",
            "organization",
            "is_crawler",
            "timezone",
            "mobile",
            "host",
            "proxy",
            "vpn",
            "tor",
            "active_vpn",
            "active_tor",
            "recent_abuse",
            "bot_status",
            "connection_type",
            "abuse_velocity",
            "latitude",
            "longitude",
        ]
        self.ip_table_columns = (
            "Fraud Score, Country Code, Region, City, Zip Code, ISP, ASN, Organization, Is Crawler, Timezone,"
            "Mobile, Host, Proxy, VPN, TOR, Active VPN, Active TOR, Recent Abuse, Bot Status, Connection Type,"
            "Abuse Velocity, Latitude, Longitude"
        )
        self.url_data_items = [
            "unsafe",
            "domain",
            "ip_address",
            "server",
            "domain_rank",
            "dns_valid",
            "parking",
            "spamming",
            "malware",
            "phishing",
            "suspicious",
            "adult",
            "risk_score",
            "category",
            "domain_age",
        ]
        self.url_table_columns = (
            "Unsafe, Domain, IP Address, Server, Domain Rank, DNS Valid, Parking, Spamming,"
            "Malware, Phishing, Suspicious, Adult, Risk Score, Category, Domain Age Human, "
            "Domain Age Timestamp, Domain Age ISO"
        )
        self.email_data_items = [
            "valid",
            "disposable",
            "smtp_score",
            "overall_score",
            "first_name",
            "generic",
            "common",
            "dns_valid",
            "honeypot",
            "deliverability",
            "frequent_complainer",
            "spam_trap_score",
            "catch_all",
            "timed_out",
            "suspect",
            "recent_abuse",
            "fraud_score",
            "suggested_domain",
            "leaked",
            "sanitized_email",
            "domain_age",
            "first_seen",
        ]
        self.email_table_columns = (
            "Valid, Disposable, SMTP Score, Overall Score, First Name, Generic, Common,"
            "DNS Valid, Honeypot, Deliverability, Frequent Complainer, Spam Trap Score,"
            "Catch All, Timed Out, Suspect, Recent Abuse, Fraud Score,"
            "Suggested Domain, Leaked, Sanitized Email, Domain Age Human, Domain Age Timestamp,"
            "Domain Age ISO, First Seen Human, First Seen Timestamp, First Seen ISO"
        )

        self.phone_data_items = [
            "formatted",
            "local_format",
            "valid",
            "fraud_score",
            "recent_abuse",
            "VOIP",
            "prepaid",
            "risky",
            "active",
            "carrier",
            "line_type",
            "country",
            "city",
            "zip_code",
            "region",
            "dialing_code",
            "active_status",
            "leaked",
            "name",
            "timezone",
            "do_not_call",
        ]

        self.phone_table_columns = (
            "Formatted, Local Format, Valid, Fraud Score, Recent Abuse, VOIP, Prepaid, Risky, "
            "Active, Carrier, Line Type, Country, City, Zip Code, Region, Dialing Code,"
            "Active Status, Leaked, Name, Timezone, Do Not Call"
        )
        self.timestamp_data_items = ["domain_age", "first_seen"]
        self.timestamp_items = ["human", "timestamp", "iso"]

    def query_ipqs(self, entity_type):
        status = False
        query_headers = {"IPQS-KEY": self.api_key}
        url = f"{BASE_URL}{entity_type}"
        response = requests.post(
            url=url,
            headers=query_headers,
            data=self.data_json,
        ).json()

        if not response["success"]:
            pass
        else:
            status = True
        return status, response

    def format_output_message(self, output_message):
        try:
            if self.success_entities:
                output_message += f"Successfully Processed Entities - {','.join(self.success_entities)},  "
            if self.no_data_entities:
                output_message += f"Unable to find data for the following Entities - {','.join(self.no_data_entities)},"
            if self.failed_entities:
                output_message += f"Enrichment failed for the following Entities - {','.join(self.failed_entities)}, "
            if self.ipqs_con_issues:
                output_message += f"Enrichment failed for the following Entities - {','.join(self.failed_entities)}, "
            if (
                not len(self.success_entities)
                + len(self.failed_entities)
                + len(self.no_data_entities)
            ):
                output_message += "No Entities were Enriched by Action  "
        except Exception as err:
            self.siemplify.LOGGER.error(f"format_output_message Error - {err}")
        return output_message

    def get_action_output(self, response, enrich_type=None):
        if enrich_type == URL_ENDPOINT:
            return self.url_action_output(response)
        if enrich_type == IP_ENDPOINT:
            return self.ip_action_output(response)
        if enrich_type == EMAIL_ENDPOINT:
            return self.email_action_output(response)
        if enrich_type == PHONE_ENDPOINT:
            return self.phone_action_output(response)

    def ip_action_output(self, response):
        table = []
        insight_record = ""
        rows = []
        data_dict = {}
        fraud_score = 0
        table.append(self.ip_table_columns)
        try:
            for data_item in self.ip_data_items:
                val = ""
                if data_item in response:
                    val = str(response[data_item])
                    key = data_item.replace("_", " ").title()
                    data_dict[key] = val
                    rows.append(val)
                    if data_item == "fraud_score":
                        fraud_score = int(val)
                else:
                    rows.append(val)
            row_data = ",".join(rows)
            table.append(row_data)
            insight_record += self.ip_address_risk_scoring(fraud_score)
        except Exception as err:
            self.siemplify.LOGGER.error(f"ip_action_output Error - {err}")
        return table, insight_record, data_dict

    def ip_address_risk_scoring(self, score):
        """Method to create calculate verdict for IP Address"""
        risk_criticality = ""
        if score == 100:
            risk_criticality = self.critical
            self.is_suspicious = True
        elif 85 <= score <= 99:
            risk_criticality = self.high
            self.is_suspicious = True
        elif 75 <= score <= 84:
            risk_criticality = self.medium
            self.is_suspicious = True
        elif 60 <= score <= 74:
            risk_criticality = self.suspicious
            self.is_suspicious = True
        elif score <= 59:
            risk_criticality = self.clean
        return f'IPQS VERDICT : "{risk_criticality}"'

    def email_action_output(self, response):
        table = []
        insight_record = ""
        rows = []
        data_dict = {}
        disposable = False
        valid = False
        fraud_score = 0
        table.append(self.email_table_columns)
        try:
            for data_item in self.email_data_items:
                val = ""
                if data_item in response:
                    if data_item in self.timestamp_data_items:
                        for time_stamp_item in self.timestamp_items:
                            key = (
                                data_item.replace("_", " ").title()
                                + " "
                                + time_stamp_item.replace("_", " ").title()
                            )
                            val = str(response[data_item][time_stamp_item])
                            rows.append(val)
                            data_dict[key] = val
                            # insight_record += f"{key}  :  {val}\n"
                    else:
                        key = data_item.replace("_", " ").title()
                        val = str(response[data_item])
                        data_dict[key] = val
                        rows.append(val)
                        # insight_record += f"{key}  :  {val}\n"
                    if data_item == "disposable":
                        disposable = val
                    if data_item == "valid":
                        valid = val
                    if data_item == "fraud_score":
                        fraud_score = int(val)
                else:
                    rows.append(val)
            row_data = ",".join(rows)
            table.append(row_data)
            insight_record += self.email_address_risk_scoring(
                fraud_score,
                disposable,
                valid,
            )
        except Exception as err:
            self.siemplify.LOGGER.error(f"email_action_output Error - {err}")
        return table, insight_record, data_dict

    def email_address_risk_scoring(self, score, disposable, valid):
        """Method to create calculate verdict for IP Address"""
        risk_criticality = ""
        if disposable == "True":
            risk_criticality = self.disposable
            self.is_suspicious = True
        elif valid == "False":
            risk_criticality = self.invalid
            self.is_suspicious = True
        elif score == 100:
            risk_criticality = self.high
            self.is_suspicious = True
        elif 88 <= score <= 99:
            risk_criticality = self.medium
            self.is_suspicious = True
        elif 80 <= score <= 87:
            risk_criticality = self.low
            self.is_suspicious = True
        elif score <= 79:
            risk_criticality = self.clean
        return f'IPQS VERDICT : "{risk_criticality}"'

    def url_action_output(self, response):
        table = []
        insight_record = ""
        rows = []
        data_dict = {}
        malware = False
        phishing = False
        risk_score = 0
        table.append(self.url_table_columns)
        try:
            for data_item in self.url_data_items:
                val = ""
                if data_item in response:
                    if data_item in self.timestamp_data_items:
                        for time_stamp_item in self.timestamp_items:
                            key = (
                                data_item.replace("_", " ").title()
                                + " "
                                + time_stamp_item.replace("_", " ").title()
                            )
                            val = str(response[data_item][time_stamp_item])
                            rows.append(val)
                            data_dict[key] = val
                            # insight_record += f"{key}  :  {val}\n"
                    else:
                        key = data_item.replace("_", " ").title()
                        val = str(response[data_item])
                        data_dict[key] = val
                        rows.append(val)
                        # insight_record += f"{key}  :  {val}\n"
                    if data_item == "malware":
                        malware = val
                    if data_item == "phishing":
                        phishing = val
                    if data_item == "risk_score":
                        risk_score = int(val)
                else:
                    rows.append(val)
            row_data = ",".join(rows)
            table.append(row_data)
            insight_record += self.url_risk_scoring(risk_score, malware, phishing)
        except Exception as err:
            self.siemplify.LOGGER.error(f"email_action_output Error - {err}")
        return table, insight_record, data_dict

    def url_risk_scoring(self, score, malware, phishing):
        """Method to create calculate verdict for IP Address"""
        risk_criticality = ""
        if malware == "True":
            risk_criticality = self.malware
            self.is_suspicious = True
        elif phishing == "True":
            risk_criticality = self.phishing
            self.is_suspicious = True
        elif score >= 90:
            risk_criticality = self.high
            self.is_suspicious = True
        elif 80 <= score <= 89:
            risk_criticality = self.medium
            self.is_suspicious = True
        elif 70 <= score <= 79:
            risk_criticality = self.low
            self.is_suspicious = True
        elif 55 <= score <= 69:
            risk_criticality = self.suspicious
            self.is_suspicious = True
        elif score <= 54:
            risk_criticality = self.clean
        return f'IPQS VERDICT : "{risk_criticality}"'

    def phone_action_output(self, response):
        table = []
        insight_record = ""
        rows = []
        data_dict = {}
        valid = False
        active = False
        fraud_score = 0
        table.append(self.phone_table_columns)
        try:
            for data_item in self.phone_data_items:
                val = ""
                if data_item in response:
                    if data_item in self.timestamp_data_items:
                        for time_stamp_item in self.timestamp_items:
                            key = (
                                data_item.replace("_", " ").title()
                                + " "
                                + time_stamp_item.replace("_", " ").title()
                            )
                            val = str(response[data_item][time_stamp_item])
                            rows.append(val)
                            data_dict[key] = val
                            # insight_record += f"{key}  :  {val}\n"
                    else:
                        key = data_item.replace("_", " ").title()
                        val = str(response[data_item])
                        data_dict[key] = val
                        rows.append(val)
                        # insight_record += f"{key}  :  {val}\n"
                    if data_item == "active":
                        active = val
                    if data_item == "valid":
                        valid = val
                    if data_item == "fraud_score":
                        fraud_score = int(val)
                else:
                    rows.append(val)
            row_data = ",".join(rows)
            table.append(row_data)
            insight_record += self.phone_risk_scoring(fraud_score, valid, active)
        except Exception as err:
            self.siemplify.LOGGER.error(f"email_action_output Error - {err}")
        return table, insight_record, data_dict

    def phone_risk_scoring(self, score, valid, active):
        """Method to create calculate verdict for IP Address"""
        risk_criticality = ""
        if valid == "False" or active == "False":
            risk_criticality = self.medium
            self.is_suspicious = True
        elif 90 <= score <= 100:
            risk_criticality = self.high
            self.is_suspicious = True
        elif 80 <= score <= 89:
            risk_criticality = self.low
            self.is_suspicious = True
        elif 50 <= score <= 79:
            risk_criticality = self.suspicious
            self.is_suspicious = True
        elif score <= 49:
            risk_criticality = self.clean
        return f'IPQS VERDICT : "{risk_criticality}"'

    def enrich(self, entity_types):
        result_value = False
        output_message = "Action result :  "
        status = EXECUTION_STATE_FAILED
        try:
            json_result = []
            enrichment_entities = []
            for entity in self.siemplify.target_entities:
                enriched_entities = {}
                if entity.entity_type in entity_types:
                    try:
                        enrich_result = None
                        enrich_status = None
                        enrich_type = None
                        if entity.entity_type == EntityTypes.HOSTNAME:
                            enrich_type = URL_ENDPOINT
                            self.data_json[enrich_type] = entity.identifier
                            enrich_status, enrich_result = self.query_ipqs(enrich_type)
                        elif entity.entity_type == EntityTypes.ADDRESS:
                            enrich_type = IP_ENDPOINT
                            self.data_json[enrich_type] = entity.identifier
                            enrich_status, enrich_result = self.query_ipqs(enrich_type)
                        elif entity.entity_type.upper() == EntityTypes.URL.upper():
                            enrich_type = URL_ENDPOINT
                            self.data_json[enrich_type] = entity.identifier
                            enrich_status, enrich_result = self.query_ipqs(enrich_type)
                        elif entity.entity_type == EntityTypes.USER:
                            if re.match(EMAIL_REGEX, entity.identifier):
                                enrich_type = EMAIL_ENDPOINT
                                self.data_json[enrich_type] = entity.identifier
                                enrich_status, enrich_result = self.query_ipqs(
                                    enrich_type,
                                )
                        elif entity.entity_type == EntityTypes.PHONENUMBER:
                            enrich_type = PHONE_ENDPOINT
                            self.data_json[enrich_type] = entity.identifier
                            enrich_status, enrich_result = self.query_ipqs(enrich_type)
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
                            table, insight, data_dict = self.get_action_output(
                                enrich_result,
                                enrich_type,
                            )
                            self.siemplify.result.add_entity_table(
                                entity.identifier,
                                table,
                            )
                            self.siemplify.create_case_insight(
                                "IPQualityScore",
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

                            # Enrichment Code
                            entity_dict = add_prefix_to_dict(
                                data_dict,
                                "IPQualityScore",
                            )
                            entity.additional_properties.update(entity_dict)
                            entity.is_enriched = True
                            if self.is_suspicious:
                                entity.is_suspicious = self.is_suspicious
                            enrichment_entities.append(entity)
                        elif not enrich_status:
                            ipqs_message = str(enrich_result["message"])
                            output_message = (
                                f"Action execution failed with Error - {ipqs_message}"
                            )
                            self.siemplify.LOGGER.error(
                                f"Enrich Error - {ipqs_message}",
                            )
                    except Exception as err:
                        self.failed_entities.append(entity.identifier)
                        self.siemplify.LOGGER.error(err)
            self.siemplify.update_entities(enrichment_entities)
            self.siemplify.result.add_result_json(json_result)
            status = EXECUTION_STATE_COMPLETED
            output_message = self.format_output_message(output_message)
        except Exception as err:
            output_message = f"Action execution failed with Error - {err}"
            self.siemplify.LOGGER.error(f"Enrich Error - {err}")
        self.siemplify.end(output_message, result_value, status)
