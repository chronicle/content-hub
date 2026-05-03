# ============================================================================#
# title           :SalesforceManager.py
# description     :This Module contain all Salesforce operations functionality
# author          :avital@siemplify.co
# date            :01-07-2018
# python_version  :2.7
# libreries       :simple_salesforce
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #

from __future__ import annotations
import requests
from simple_salesforce import Salesforce
from pypika import Query, Table, Field

from .constants import DEFAULT_API_VERSION

# ============================== CONSTS ===================================== #

HEADERS = {
    "Authorization": None,
    "Accept": "application/json",
    "Content-Type": "application/json",
}

URI_PREFIX = "/services/data/v39.0/"
CASE_PROPERTIES = [
    "ID",
    "CaseNumber",
    "Subject",
    "Description",
    "CreatedDate",
    "ClosedDate",
    "OwnerID",
    "Priority",
    "Origin",
    "Status",
    "Reason",
]
CONTACT_PROPERTIES = [
    "ID",
    "Name",
    "Title",
    "AccountId",
    "Phone",
    "MobilePhone",
    "Email",
    "OwnerId",
]
LEAD_PROPERTIES = [
    "ID",
    "Name",
    "Title",
    "Company",
    "Phone",
    "MobilePhone",
    "Email",
    "Status",
    "OwnerId",
]
TASK_PROPERTIES = ["ID", "Subject", "WhoId", "ActivityDate"]
USER_PROPERTIES = ["ID", "Name", "Title", "Phone", "Email"]
IDS_CHUNK = 50

# ============================= CLASSES ===================================== #


class SalesforceManagerError(Exception):
    """
    General Exception for Salesforce manager
    """

    pass


class SalesforceManager:
    """
    Salesforce Manager
    """

    def __init__(
        self, username, password, security_token, server_addr=None, verify_ssl=False
    ):
        session = requests.Session()
        session.verify = verify_ssl
        self.sf = Salesforce(
            instance_url=server_addr,
            username=username,
            password=password,
            security_token=security_token,
            session=session,
            version = DEFAULT_API_VERSION
        )

    def test_connectivity(self):
        """
        Test connectivity to Salesforce
        :return: {bool} True if successful, exception otherwise.
        """
        self.get_cases()
        return True

    def get_case_by_number(self, case_number):
        """
        Get a case by CaseNumber
        :param case_number: {str} The case's CaseNumber
        :return: {dict} The case info
        """
        _table = Table("Case")
        query = Query.from_(_table)
        for case_property in CASE_PROPERTIES:
            query = query.select(Field(case_property))
        query = query.where(_table.CaseNumber == case_number)
        case = self.run_query(query.get_sql(quote_char=""))

        if not case:
            raise SalesforceManagerError(f"Case {case_number} was not found.")

        return case[0]

    def get_case_by_id(self, case_id):
        """
        Get a case by id
        :param case_id: {str} The case id
        :return: {dict} The case info
        """
        _table = Table("Case")
        query = Query.from_(_table)
        for case_property in CASE_PROPERTIES:
            query = query.select(Field(case_property))
        query = query.where(_table.Id == case_id)
        case = self.run_query(query.get_sql(quote_char=""))

        if not case:
            raise SalesforceManagerError(f"Case {case_id} was not found.")

        return case[0]

    def get_cases(self):
        """
        Get all cases
        :return: {list} List of the cases
        """
        _table = Table("Case")
        query = Query.from_(_table)
        for case_property in CASE_PROPERTIES:
            query = query.select(Field(case_property))
        return self.run_query(query.get_sql(quote_char=""))

    def close_case(self, case_id):
        """
        Close a case
        :param case_id: {str} The case's id
        :return: {bool} True if successful, exception otherwise.
        """
        self.update_case(case_id, status="Closed")
        return True

    def create_case(
        self,
        subject,
        status="New",
        description=None,
        origin=None,
        priority="Low",
        case_type=None,
    ):
        """
        Create a case
        :param subject: {str} The case's subject
        :param description: {str} The description of the subject
        :param status: {str} The case's status. Valid values:
            - New
            - On Hold
            - Closed
            - Escalated
        :param origin: {str} The origin of the case. Valid values:
            - Email
            - Phone
            - Web
        :param priority: {str} The case's priority. Valid values:
            - Low
            - Medium
            - High
        :param case_type: {str} The case type. Valid values:
            - Question
            - Problem
            - Feature Request
        :return: {dict} The details of the new case
        """
        case = self.sf.Case.create(
            {
                "Subject": subject,
                "Description": description,
                "Status": status,
                "Origin": origin,
                "Priority": priority,
                "Type": case_type,
            }
        )

        self.validate_response(case, "Unable to create case")
        return self.get_case_by_id(case.get("id"))

    def update_case(
        self,
        case_id,
        subject=None,
        description=None,
        status=None,
        origin=None,
        priority=None,
        case_type=None,
    ):
        """
        Update a case
        :param case_id: {str} The case id
        :param subject: {str} The case's subject
        :param description: {str} The description of the subject
        :param status: {str} The case's status. Valid values:
            - New
            - On Hold
            - Closed
            - Escalated
        :param origin: {str} The origin of the case. Valid values:
            - Email
            - Phone
            - Web
        :param priority: {str} The case's priority. Valid values:
            - Low
            - Medium
            - High
        :param case_type: {str} The case type. Valid values:
            - Question
            - Problem
            - Feature Request
        :return: {bool} True if successful, exception otherwise.
        """
        self.sf.Case.update(
            case_id,
            {
                "Subject": subject,
                "Description": description,
                "Status": status,
                "Origin": origin,
                "Priority": priority,
                "Type": case_type,
            },
        )

        return True

    def search(self, search_term):
        """
        Search records that contain values with given pattern.
        :param search_term: {str} The pattern to search for
        :return: {list} The found results
        """
        hits = self.sf.search(f"FIND {{{search_term}}}").get("searchRecords", [])

        result_ids = {
            "cases": [],
            "contacts": [],
            "leads": [],
            "tasks": [],
            "users": [],
        }

        for hit in hits:
            if hit.get("attributes"):
                if hit.get("attributes", {}).get("type") == "Case":
                    result_ids["cases"].append(hit.get("Id"))
                elif hit.get("attributes", {}).get("type") == "Contact":
                    result_ids["contacts"].append(hit.get("Id"))
                elif hit.get("attributes", {}).get("type") == "Lead":
                    result_ids["leads"].append(hit.get("Id"))
                elif hit.get("attributes", {}).get("type") == "Task":
                    result_ids["tasks"].append(hit.get("Id"))
                elif hit.get("attributes", {}).get("type") == "User":
                    result_ids["users"].append(hit.get("Id"))

        results = {}

        if result_ids["cases"]:
            results["Cases"] = []

            for case_ids in self.chunks(result_ids["cases"], IDS_CHUNK):
                _table = Table("Case")
                query = Query.from_(_table)
                for case_property in CASE_PROPERTIES:
                    query = query.select(Field(case_property))
                query = query.where(
                    _table.Id.isin([f"{obj_id}" for obj_id in case_ids])
                )
                results["Cases"].extend(self.run_query(query.get_sql(quote_char="")))

        if result_ids["contacts"]:
            results["Contacts"] = []

            for case_ids in self.chunks(result_ids["contacts"], IDS_CHUNK):
                _table = Table("Contact")
                query = Query.from_(_table)
                for contact_property in CONTACT_PROPERTIES:
                    query = query.select(Field(contact_property))
                query = query.where(
                    _table.Id.isin([f"{obj_id}" for obj_id in case_ids])
                )
                results["Contacts"].extend(self.run_query(query.get_sql(quote_char="")))

        if result_ids["leads"]:
            results["Leads"] = []

            for case_ids in self.chunks(result_ids["leads"], IDS_CHUNK):
                _table = Table("Lead")
                query = Query.from_(_table)

                for lead_property in LEAD_PROPERTIES:
                    query = query.select(Field(lead_property))
                query = query.where(
                    _table.Id.isin([f"{obj_id}" for obj_id in case_ids])
                )
                results["Leads"].extend(self.run_query(query.get_sql(quote_char="")))

        if result_ids["users"]:
            results["Users"] = []

            for case_ids in self.chunks(result_ids["users"], IDS_CHUNK):
                _table = Table("User")
                query = Query.from_(_table)

                for user_property in USER_PROPERTIES:
                    query = query.select(Field(user_property))
                query = query.where(
                    _table.Id.isin([f"{obj_id}" for obj_id in case_ids])
                )
                results["Users"].extend(self.run_query(query.get_sql(quote_char="")))

        if result_ids["tasks"]:
            results["Tasks"] = []

            for case_ids in self.chunks(result_ids["tasks"], IDS_CHUNK):
                _table = Table("Task")
                query = Query.from_(_table)
                for task_property in TASK_PROPERTIES:
                    query = query.select(Field(task_property))
                query = query.where(
                    _table.Id.isin([f"{obj_id}" for obj_id in case_ids])
                )
                results["Tasks"].extend(self.run_query(query.get_sql(quote_char="")))

        return results

    def add_comment(self, case_id, title, body):
        """
        Add a comment to a case
        :param case_id: {str} The case id
        :param title: {str} The comment title
        :param body: {str} The comment's body
        :return: {bool} True if successful, exception otherwise.
        """
        comment_body:str = f"{title} : {body}"
        result = self.sf.CaseComment.create(
            {"CommentBody": comment_body, "ParentId": case_id}
        )

        self.validate_response(result, f"Unable to add comment to case {case_id}")
        return True

    def run_query(self, query, delete_attributes=True):
        results = self.sf.query(query)

        records = results.get("records", [])
        done = results.get("done")

        while not done:
            results = self.sf.query_more(results.get("nextRecordsUrl"), True)
            records.extend(results.get("records", []))
            done = results.get("done")

        if delete_attributes:
            for record in records:
                if record.get("attributes"):
                    # Irrelevant data
                    del record["attributes"]

        return records

    @staticmethod
    def validate_response(result, error_msg):
        """
        Validate the response of the Salesforce API
        :param result: {dict} The action response
        :param error_msg: {str} Error message to display on failure
        :return: {bool} True if response is valid, exception otherwise.
        """
        if not result.get("success"):
            raise SalesforceManagerError(
                f"{error_msg}: {', '.join(result.get('errors', []))}"
            )

        return True

    @staticmethod
    def chunks(l, n):
        # For item i in a range that is a length of l,
        for i in range(0, len(l), n):
            # Create an index range for l of n items:
            yield l[i : i + n]
