from __future__ import annotations
from urllib.parse import urljoin
import requests
from .constants import (
    ENDPOINTS,
    STATUS_MAPPING,
    IMPACT_MAPPING,
    URGENCY_MAPPING,
    REPORTED_SOURCE_MAPPING,
    INCIDENT_TYPE_MAPPING,
    PRIORITY_MAPPING,
    INCIDENT_NUMBER_FIELD,
    CLOSED_STATUS,
)
from .UtilsManager import validate_response
from .BMCRemedyITSMParser import BMCRemedyITSMParser


class BMCRemedyITSMManager:
    def __init__(self, api_root, username, password, verify_ssl, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} BMCRemedyITSMManager API root
        :param username: {str} BMCRemedyITSMManager username
        :param password: {str} BMCRemedyITSMManager password
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.parser = BMCRemedyITSMParser()
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update({"Authorization": self.get_auth_token()})

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def get_auth_token(self):
        url = self._get_full_url("login")
        payload = {"username": self.username, "password": self.password}

        response = self.session.post(url, data=payload)
        validate_response(response)
        return response.text

    def logout(self):
        url = self._get_full_url("logout")
        response = self.session.post(url)
        validate_response(response)

    def test_connectivity(self):
        """
        Test connectivity
        """
        url = self._get_full_url("ping")
        response = self.session.get(url)
        validate_response(response)

    def get_templates_by_name(self, template_name):
        """
        Get templates by name
        :param template_name: {str} template name
        :return: {list} list of Template objects
        """
        url = self._get_full_url("get_template")
        params = {"q": f"'Template Name' = \"{template_name}\""}

        response = self.session.get(url, params=params)
        validate_response(response)
        return self.parser.build_template_objects(response.json())

    def create_incident(
        self,
        status,
        impact,
        urgency,
        description,
        company,
        first_name,
        last_name,
        template_id,
        incident_type,
        assigned_group,
        assignee,
        resolution,
        resolution_category_tier_1,
        resolution_category_tier_2,
        resolution_category_tier_3,
        resolution_product_category_tier_1,
        resolution_product_category_tier_2,
        resolution_product_category_tier_3,
        reported_source,
        custom_fields,
    ):
        url = self._get_full_url("create_incident")
        data = {
            "Status": STATUS_MAPPING.get(status),
            "Impact": IMPACT_MAPPING.get(impact),
            "Urgency": URGENCY_MAPPING.get(urgency),
            "Description": description,
            "Contact_Company": company,
            "First_Name": first_name,
            "Last_Name": last_name,
            "TemplateID": template_id,
            "Service_Type": INCIDENT_TYPE_MAPPING.get(incident_type),
            "Assigned Group": assigned_group,
            "Assignee": assignee,
            "Resolution": resolution,
            "Resolution Category Tier 1": resolution_category_tier_1,
            "Resolution Category Tier 2": resolution_category_tier_2,
            "Resolution Category Tier 3": resolution_category_tier_3,
            "Closure Product Category Tier1": resolution_product_category_tier_1,
            "Closure Product Category Tier2": resolution_product_category_tier_2,
            "Closure Product Category Tier3": resolution_product_category_tier_3,
            "Reported Source": REPORTED_SOURCE_MAPPING.get(reported_source),
        }

        data.update(custom_fields)
        values = {key: value for key, value in data.items() if value}
        payload = {"values": values}

        response = self.session.post(url, json=payload)
        validate_response(response)
        return self.parser.build_incident_object(response.json())

    def get_incidents_details(self, incident_ids, fields):
        """
        Get incidents details
        :param incident_ids: {list} Ids of incidents
        :param fields: {str} Fields to return
        :return: {list} list of Incident objects
        """
        url = self._get_full_url("get_incident_details")
        params = {
            "q": " OR ".join(
                [f"'Incident Number' = \"{inc_id}\"" for inc_id in incident_ids]
            )
        }
        if fields:
            params["fields"] = f"values({INCIDENT_NUMBER_FIELD + ',' + fields})"

        response = self.session.get(url, params=params)
        validate_response(response)
        return self.parser.build_incidents_details_list(response.json())

    def get_record_details(self, record_type, record_id, fields):
        """
        Get record details
        :param record_type: {str} Type of the record to return
        :param record_id: {str} Id of record to return
        :param fields: {str} Fields to return
        :return: {RecordDetails}
        """
        url = self._get_full_url(
            "get_record_details", record_type=record_type, record_id=record_id
        )
        params = {}
        if fields:
            params["fields"] = f"values({fields})"

        response = self.session.get(url, params=params)
        validate_response(response)
        return self.parser.build_record_details(response.json())

    def get_worknotes(self, incident_id, limit):
        """
        Get incident worknotes
        :param incident_id: {str} Id of incident
        :return: {list} list of WorkNote objects
        """
        url = self._get_full_url("get_worknotes")
        params = {
            "q": f"'Incident Number' = \"{incident_id}\"",
            "fields": f"values(Submitter,Detailed Description,Work Log Type,Work Log Submit Date)",
            "limit": limit,
        }

        response = self.session.get(url, params=params)
        validate_response(response)
        return self.parser.build_work_notes_list(response.json())

    def get_incident_details(self, incident_id):
        """
        Get incident details by id
        :param incident_id: {str} incident id
        :return: {list} list of Incident objects
        """
        url = self._get_full_url("get_incident_details")
        params = {"q": f"'Incident Number' = \"{incident_id}\""}

        response = self.session.get(url, params=params)
        validate_response(response)
        return self.parser.build_incident_objects(response.json())

    def get_incident_details_by_table(self, table_name, incident_id):
        """
        Get incident details by id and table name
        :param table_name: {str} Name of the table to fetch incident from
        :param incident_id: {str} Incident id
        :return: {list} list of Incident objects
        """
        url = self._get_full_url("get_incident_details_by_table", table_name=table_name)
        params = {"q": f"'Incident Number' = \"{incident_id}\""}

        response = self.session.get(url, params=params)
        validate_response(response)
        return self.parser.build_incident_objects(response.json())

    def update_incident(
        self,
        request_id,
        status,
        status_reason,
        impact,
        urgency,
        description,
        incident_type,
        assigned_group,
        assignee,
        resolution,
        resolution_category_tier_1,
        resolution_category_tier_2,
        resolution_category_tier_3,
        resolution_product_category_tier_1,
        resolution_product_category_tier_2,
        resolution_product_category_tier_3,
        reported_source,
        custom_fields,
    ):
        url = self._get_full_url("update_incident", request_id=request_id)
        data = {
            "Status": STATUS_MAPPING.get(status),
            "Status_Reason": status_reason,
            "Impact": IMPACT_MAPPING.get(impact),
            "Urgency": URGENCY_MAPPING.get(urgency),
            "Priority": PRIORITY_MAPPING.get(
                (URGENCY_MAPPING.get(urgency), IMPACT_MAPPING.get(impact))
            ),
            "Description": description,
            "Service Type": INCIDENT_TYPE_MAPPING.get(incident_type),
            "Assigned Group": assigned_group,
            "Assignee": assignee,
            "Resolution": resolution,
            "Resolution Category": resolution_category_tier_1,
            "Resolution Category Tier 2": resolution_category_tier_2,
            "Resolution Category Tier 3": resolution_category_tier_3,
            "Closure Product Category Tier1": resolution_product_category_tier_1,
            "Closure Product Category Tier2": resolution_product_category_tier_2,
            "Closure Product Category Tier3": resolution_product_category_tier_3,
            "Reported Source": REPORTED_SOURCE_MAPPING.get(reported_source),
        }

        data.update(custom_fields)
        values = {key: value for key, value in data.items() if value}
        payload = {"values": values}

        response = self.session.put(url, json=payload)
        validate_response(response)

    def update_incident_by_table(self, request_id, table_name):
        """
        Update incident in a specific table
        :param request_id: {str} The id of the incident
        :param table_name: {str} The name of the table
        """
        url = self._get_full_url(
            "update_incident_by_table", table_name=table_name, request_id=request_id
        )
        data = {"Status": CLOSED_STATUS, "Resolution": "Closed by Siemplify"}

        payload = {"values": data}

        response = self.session.put(url, json=payload)
        validate_response(response)

    def add_worknote_to_incident(self, incident_id, text):
        """
        Add worknote to incident
        :param incident_id: {str} Id of incident
        :param text: {str} Description for worknote
        """
        url = self._get_full_url("add_worknote_to_incident")
        payload = {
            "values": {
                "Description": text,
                "Incident Number": incident_id,
                "Work Log Type": "Working Log",
            }
        }

        response = self.session.post(url, json=payload)
        validate_response(response)

    def delete_incident(self, entry_id):
        """
        Delete incident by request id
        :param entry_id: {str} incident id
        """
        url = self._get_full_url("delete_incident", entry_id=entry_id)
        response = self.session.delete(url)
        validate_response(response)

    def create_record(self, record_type, record_payload):
        """
        Create records in the BMC Remedy ITSM
        :param record_type {str} Record Type
        :param record_payload {str} Record Payload
        :return: {JSON} Raw response in JSON
        """
        request_url = self._get_full_url("create_record", record_type=record_type)
        payload = {"values": record_payload}

        result = self.session.post(request_url, json=payload)
        validate_response(result)

        return self.parser.build_record_obj(result.json())

    def update_record(self, record_id, record_type, record_payload):
        """
        Create records in the BMC Remedy ITSM
        :param record_id {str} Record ID
        :param record_type {str} Record Type
        :param record_payload {str} Record Payload
        :return: {JSON} Raw response in JSON
        """
        request_url = self._get_full_url(
            "update_record", record_type=record_type, record_id=record_id
        )
        payload = {"values": record_payload}

        result = self.session.put(request_url, json=payload)
        validate_response(result)

    def delete_record(self, record_type, record_id):
        """
        Delete Record
        :param record_type: {str} record type
        :param record_id: {str} record id
        """
        url = self._get_full_url(
            "delete_record", record_type=record_type, record_id=record_id
        )
        response = self.session.delete(url)
        validate_response(response)
