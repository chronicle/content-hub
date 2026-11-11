# ==============================================================================
# title           :ConnectWiseManager.py
# description     :This Module contain all ConnectWise operations functionality
# author          :zdemoniac@gmail.com
# date            :12-28-17
# python_version  :2.7
# libraries       :base64, requests
# requirements    :
# product_version :
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import base64
from datetime import datetime
import copy
import json
import urllib.parse
import requests
from connect_wise.core.ConnectWiseParser import ConnectWiseParser

# =====================================
#             CONSTANTS               #
# =====================================
HEADERS = {
    "Authorization": "Basic {0}",
    "Content-Type": "application/json",
    "Accept": "application/json; application/vnd.connectwise.com+json;",
}

CW_DATETIME_STR_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
PAGE_SIZE = 1000
SUMMARY_CHAR_COUNT = 100

# URLs
CONNECTIVITY_TEST_URL = "service/boards/count"
GET_STATUS_URL = "service/boards/{0}/statuses/"  # Board ID.
GET_BOARD_URL = "service/boards"
GET_PRIORITY_URL = "service/priorities"
GET_MEMBERS_URL = "system/members"
CREATE_TICKET_URL = "service/tickets"
UPDATE_TICKET_URL = "service/tickets/{0}"  # Ticket ID.
ADD_TICKET_COMMENT_URL = "service/tickets/{0}/notes"  # Ticket ID.
GET_TICKET_TIME_ENTIRES = "time/entries/"
ADD_ATTACHMENT_URL = "system/documents"


# =====================================
#              CLASSES                #
# =====================================
# Docs: https://developer.connectwise.com/Documentation
class ConnectWiseManagerError(Exception):
    """
    General Exception for ConnectWise manager
    """

    pass


class ConnectWiseBadRequestError(Exception):
    pass


class ConnectWiseManager:
    """
    Responsible for all ConnectWise system operations functionality
    """

    def __init__(
        self,
        company_url,
        company_name,
        public_key,
        private_key,
        client_id,
        page_size=50,
    ):
        self._url = company_url
        self._date_format = CW_DATETIME_STR_FORMAT
        self._page_size = page_size
        self.parser = ConnectWiseParser()

        # Create sesson.
        self.session = requests.session()
        self.session.headers = copy.deepcopy(HEADERS)
        # Create token and insert it to the header.
        self.session.headers["Authorization"] = self.session.headers[
            "Authorization"
        ].format(
            base64.b64encode(
                f"{company_name}+{public_key}:{private_key}".encode("utf-8")
            ).decode("utf-8")
        )
        self.session.headers["clientId"] = client_id

    @staticmethod
    def validate_response(response):
        """
        Validate an HTTP response.
        :param response: HTTP response object {HTTP response}
        :return: exception thrown in case the response is not valid {void}
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as err:
            if response.status_code == 400:
                try:
                    error_message = "\n".join(
                        msg.get("message", "")
                        for msg in response.json().get("errors", [])
                    )

                except json.JSONDecodeError:
                    error_message = response.text

                raise ConnectWiseBadRequestError(error_message) from err

            raise ConnectWiseManagerError(
                f"HTTP Error, Status Code: {response.status_code}, "
                f"Content: {response.content}, ERROR: {err}"
            ) from err

    def test_connectivity(self):
        """
        Validates connectivity
        :return: {boolean} True/False
        """
        request_url = urllib.parse.urljoin(self._url, CONNECTIVITY_TEST_URL)
        r = self.session.get(request_url)
        self.validate_response(r)
        return True

    def get_status_id_by_name(self, board_name, status_name):
        """
        Retrieve status ID by status name in system
        :param board_name: {string} The board to look the status in
        :param status_name: {string} Status human readable name
        :return: {string} The status id
        """
        board_id = self.get_board_id_by_name(board_name)
        conditions = f"name='{status_name}'"
        request_url = urllib.parse.urljoin(self._url, GET_STATUS_URL.format(board_id))
        r = self.session.get(request_url, params={"conditions": conditions})
        self.validate_response(r)
        # Check if results were found
        if not r.json():
            raise ConnectWiseManagerError(
                f"Error: Cannot find status {status_name} in board {board_name} statuses list"
            )
        return str(r.json()[0]["id"])

    def get_user_id_by_name(self, user_name):
        """
        Retrieve user ID by user name in system
        :param user_name: {string} User name to look for
        :return: {string} The user id
        """
        conditions = f"identifier='{user_name}'"
        request_url = urllib.parse.urljoin(self._url, GET_MEMBERS_URL)
        r = self.session.get(request_url, params={"conditions": conditions})
        self.validate_response(r)
        # Check if results were found
        if not r.json():
            raise ConnectWiseManagerError(f"Error: Cannot find user {user_name}")
        return str(r.json()[0]["id"])

    def get_board_id_by_name(self, board_name):
        """
        Retrieve board ID by board name in system
        :param board_name: {string} board human readable name
        :return: {string} The board id
        """
        conditions = f"name='{board_name}'"
        request_url = urllib.parse.urljoin(self._url, GET_BOARD_URL)
        r = self.session.get(request_url, params={"conditions": conditions})
        self.validate_response(r)
        # Check if results were found
        if not r.json():
            raise ConnectWiseManagerError(
                f"Error: Cannot find board {board_name} in boards list"
            )
        return str(r.json()[0]["id"])

    def get_priority_id_by_name(self, priority_name):
        """
        Retrieve priority ID by priority name in system
        :param priority_name: {string} priority human readable name
        :return: {string} The priority id
        """
        request_url = urllib.parse.urljoin(self._url, GET_PRIORITY_URL)
        r = self.session.get(request_url)
        self.validate_response(r)
        # Look for the suitable status
        for priority in r.json():
            if priority["name"] == priority_name:
                return str(priority["id"])
        raise ConnectWiseManagerError(
            f"Error: Cannot find priority {priority_name} in priorities list"
        )

    def covert_datetime_to_cw_format(self, datetime_obj):
        """
        Convert Datetime object to ConnectWise Datetime format
        :param datetime_obj: {datetime} conver datetime object to ConnectWise timestamp string.
        :return: {string} ConnectWise datetime format
        """
        return datetime.strftime(datetime_obj, self._date_format)

    def create_ticket(
        self,
        summary,
        company,
        board,
        status_name,
        priority_name,
        owner_name=None,
        email_cc=None,
    ):
        """
        Create new ticket in ConnectWise
        :param summary: {string} ticket"s summary text
        :param company: {string} company name
        :param board: {string} board name
        :param status_name: {string} ticket's status
        :param priority_name: {int} ticket's priority
        :param owner_name: {int} User name to assign the ticket to
        :param email_cc: {int} cc emails
        :return: {string} Created ticket id
        """
        request_url = urllib.parse.urljoin(self._url, CREATE_TICKET_URL)
        payload = {
            "board": {"name": board},
            "company": {"identifier": company},
            "status": {"id": self.get_status_id_by_name(board, status_name)},
            "summary": summary,
            "priority": {"id": self.get_priority_id_by_name(priority_name)},
        }

        if owner_name:
            payload["owner"] = {"id": self.get_user_id_by_name(owner_name)}

        if email_cc:
            payload["automaticEmailCcFlag"] = True
            payload["automaticEmailCc"] = ";".join(email_cc)

        r = self.session.post(request_url, json=payload)
        self.validate_response(r)
        return str(r.json()["id"])

    def update_ticket(
        self,
        ticket_id,
        summary=None,
        type_name=None,
        subtype_name=None,
        item_name=None,
        owner_name=None,
        board_name=None,
        priority_name=None,
        status=None,
        email_cc=None,
    ):
        """
        Update ticket summary in ConnectWise
        :param ticket_id: {string} ConnectWise ticket id
        :param summary: {string} ticket's summary text
        :param type_name: {string} ticket's type name
        :param subtype_name: {string} ticket's subtype name
        :param item_name: {string} ticket's item name
        :param owner_name: {string} ticket's owner name
        :param board_name: {string} ticket's board name
        :param priority_name: {string} ticket's priority name
        :param status: {string} ticket's status
        :param email_cc: {string} cc emails
        :return: {string} Updated ticket id
        """
        update_operations = []
        if summary:
            update_operations.append(
                {"op": "replace", "path": "/summary", "value": summary}
            )
        if type_name:
            update_operations.append(
                {"op": "replace", "path": "/type", "value": {"name": type_name}}
            )
        if subtype_name:
            update_operations.append(
                {"op": "replace", "path": "/subType", "value": {"name": subtype_name}}
            )
        if item_name:
            update_operations.append(
                {"op": "replace", "path": "/item", "value": {"name": item_name}}
            )
        if owner_name:
            update_operations.append(
                {
                    "op": "replace",
                    "path": "/owner",
                    "value": {"id": self.get_user_id_by_name(owner_name)},
                }
            )
        if board_name:
            update_operations.append(
                {
                    "op": "replace",
                    "path": "/board",
                    "value": {"id": self.get_board_id_by_name(board_name)},
                }
            )
        if priority_name:
            update_operations.append(
                {
                    "op": "replace",
                    "path": "/priority",
                    "value": {"id": self.get_priority_id_by_name(priority_name)},
                }
            )

        if status and not board_name:
            board = self.get_ticket(ticket_id).get("board", "").get("name", "")
            update_operations.append(
                {
                    "op": "replace",
                    "path": "/status",
                    "value": {"id": self.get_status_id_by_name(board, status)},
                }
            )

        if email_cc:
            update_operations.append(
                {"op": "replace", "path": "/automaticEmailCcFlag", "value": True}
            )
            update_operations.append(
                {
                    "op": "replace",
                    "path": "/automaticEmailCc",
                    "value": ";".join(email_cc),
                }
            )

        request_url = urllib.parse.urljoin(
            self._url, UPDATE_TICKET_URL.format(ticket_id)
        )
        response = self.session.patch(request_url, json=update_operations)
        self.validate_response(response)
        if status and board_name:
            payload = [
                {
                    "op": "replace",
                    "path": "/status",
                    "value": {"id": self.get_status_id_by_name(board_name, status)},
                }
            ]

            request_url = urllib.parse.urljoin(
                self._url, UPDATE_TICKET_URL.format(ticket_id)
            )
            response = self.session.patch(request_url, json=payload)
            self.validate_response(response)
        return str(response.json().get("id", ""))

    def update_ticket_status(self, ticket_id, status):
        """
        Update ticket status in ConnectWise
        :param ticket_id: {string} ConnectWise ticket id
        :param status: {string} Updating status
        :return: {string} Closed ticket id
        """
        board_name = self.get_ticket(ticket_id).get("board", "").get("name", "")
        payload = [
            {
                "op": "replace",
                "path": "/status",
                "value": {"id": self.get_status_id_by_name(board_name, status)},
            }
        ]

        request_url = urllib.parse.urljoin(
            self._url, UPDATE_TICKET_URL.format(ticket_id)
        )
        response = self.session.patch(request_url, json=payload)
        self.validate_response(response)
        return str(response.json().get("id", ""))

    def close_ticket(self, ticket_id, custom_close_status=None):
        """
        Close ticket in ConnectWise, Changed it's status to a closable status if needed
        :param ticket_id: {string} ConnectWise ticket id
        :param custom_close_status: {string} If the specific system use a custom closed status (like: Completed)
        :return: {string} Closed ticket id
        """
        request_url = urllib.parse.urljoin(
            self._url, UPDATE_TICKET_URL.format(ticket_id)
        )
        board_name = self.get_ticket(ticket_id)["board"]["name"]
        if custom_close_status:
            status_id = self.get_status_id_by_name(board_name, custom_close_status)
            r = self.session.patch(
                request_url,
                json=[{"op": "replace", "path": "/status/id", "value": status_id}],
            )
        else:
            r = self.session.patch(
                request_url,
                json=[
                    # need set status first
                    # status list: https://portal.choicesolutions.com/v4_6_release/apis/3.0/service/boards/70/statuses/
                    # {
                    #     "op": "replace",
                    #     "path": "/status/id",
                    #     "value": "1358"  # 1358: Cancelled, 1359: Returned
                    # },
                    {"op": "replace", "path": "closedFlag", "value": "true"}
                ],
            )
        self.validate_response(r)
        ticket = r.json()
        # Verify close operation succeeded
        if not ticket["closedFlag"] and not custom_close_status:
            raise ConnectWiseManagerError(
                f"Error: Cannot close ticket due to current ticket's status - {ticket['status']['name']}"
            )
        return str(ticket["id"])

    def get_ticket(self, ticket_id):
        """
        Get ticket info in ConnectWise
        :param ticket_id: {string} ConnectWise ticket id
        :return: {json} Ticket object
        """
        request_url = urllib.parse.urljoin(
            self._url, UPDATE_TICKET_URL.format(ticket_id)
        )
        r = self.session.get(request_url)
        self.validate_response(r)
        return r.json()

    def delete_ticket(self, ticket_id):
        """
        Delete ticket in ConnectWise
        :param ticket_id: {string} ConnectWise ticket id
        :return: {boolean} is success
        """
        request_url = urllib.parse.urljoin(
            self._url, UPDATE_TICKET_URL.format(ticket_id)
        )
        r = self.session.delete(request_url)
        self.validate_response(r)
        return True

    def add_comment_to_ticket(self, ticket_id, comment, internal=False):
        """
        Create new ticket in ConnectWise
        :param ticket_id: {string} ConnectWise ticket id
        :param comment: {string} comment content to attach to a ticket
        :param internal: {boolean} put comment in internal section
        :return: {json} created comment object
        """
        request_json = {
            "internalFlag": True,
            "detailDescriptionFlag": True,
            "text": comment,
        }
        # Put the comment in the internal section instead of in the discussion
        if internal:
            request_json["internalAnalysisFlag"] = request_json.pop(
                "detailDescriptionFlag"
            )

        request_url = urllib.parse.urljoin(
            self._url, ADD_TICKET_COMMENT_URL.format(ticket_id)
        )
        r = self.session.post(request_url, json=request_json)
        self.validate_response(r)
        return str(r.json()["id"])

    def get_ticket_comments_since_time(self, ticket_id, start_datetime):
        """
        Get ticket info in ConnectWise
        :param ticket_id: {string} ConnectWise ticket id
        :param start_datetime: {datetime} time since fetch ticket from
        :return: {json} Ticket object
        """
        conditions = f"?conditions=dateCreated>[{datetime.strftime(start_datetime, self._date_format)}]"
        request_url = urllib.parse.urljoin(
            self._url, ADD_TICKET_COMMENT_URL.format(ticket_id)
        )
        r = self.session.get(f"{request_url}{conditions}")
        self.validate_response(r)

        return r.json()

    def get_tickets_by_filter(
        self, summary_filter="", company_filter="", board_filter=""
    ):
        """
        Get tickets by filters (if a filter"s string == "": pass the filter)
        :param summary_filter: {string} summery content to filter by
        :param company_filter: {string} company name to filter by
        :param board_filter: {string} board name to filter by
        :return: {json} Ticket object
        """
        conditions = f'summary contains "{summary_filter}" and company/name contains "{company_filter}" and board/name contains "{board_filter}"'
        return self.get_tickets_by_conditions(conditions)

    def get_close_tickets_since_time(self, start_datetime, custom_close_status=None):
        """
        Get all tickets that were close after the time_filter
        :param start_datetime: {datetime} get close ticket since time
        :param custom_close_status: {string} If the specific system use a custom closed status (like: Completed)
        :return: {list} Ticket's id list
        """
        if custom_close_status:
            conditions = f"status/name = '{custom_close_status}' and lastUpdated > [{datetime.strftime(start_datetime, self._date_format)}]"
        else:
            conditions = f"ClosedFlag = True and lastUpdated > [{datetime.strftime(start_datetime, self._date_format)}]"
        return self.get_tickets_by_conditions(conditions)

    def add_attachment_to_ticket(
        self, ticket_id, base64_encoded_file, filename, public_flag, read_only_flag
    ):
        """
        Add attachment to ticket in ConnectWise
        :param ticket_id: {str} ConnectWise ticket id
        :param base64_encoded_file: {string} base 64 for file
        :param filename: {boolean} file name
        :param public_flag: {bool} public flag
        :param read_only_flag: {bool} read only flag
        :return: {json} created comment object
        """
        title = filename
        with open(filename, "wb") as f:
            f.write(base64.b64decode(base64_encoded_file))

        files = [("file", (open(filename, "rb")))]

        request_data = {
            "recordId": ticket_id,
            "recordType": "Ticket",
            "title": title,
            "publicFlag": public_flag,
            "readOnlyFlag": read_only_flag,
        }
        # Content-Type is not working for this endpoint, so we will remove it and then put it back
        del self.session.headers["Content-Type"]
        response = self.session.post(
            urllib.parse.urljoin(self._url, ADD_ATTACHMENT_URL),
            files=files,
            data=request_data,
        )
        # Setting default value for Content-Type
        self.session.headers["Content-Type"] = HEADERS["Content-Type"]
        self.validate_response(response)

        return self.parser.build_attachment_obj(response.json())

    def get_tickets_by_conditions(self, conditions):
        """
        Get ticket's by condition
        :param conditions: {string} from https://developer.connectwise.com/Manage/Developer_Guide
        :return: {list of dicts} Ticket's
        """
        return_ticket = []

        page = 1
        pages_num = 1

        while page <= pages_num:
            request_url = urllib.parse.urlparse(self._url, UPDATE_TICKET_URL)
            r = self.session.get(
                request_url,
                params={
                    "pageSize": self._page_size,
                    "conditions": conditions,
                    "page": page,
                },
            )
            self.validate_response(r)
            # check link headers for last page
            if pages_num == 1 and "last" in r.links:
                pages_num_url = r.links["last"]["url"]
                pages_num = int(
                    urllib.parse.parse_qs(urllib.parse.urlsplit(pages_num_url).query)[
                        "page"
                    ][0]
                )

            # append ticket ids from the result page
            for ticket in r.json():
                return_ticket.append(ticket)
            page += 1

        return return_ticket

    def get_ticket_times_entries(self, ticket_id, time_filter=None):
        """
        Get tickets time entries (different kind of comments)
        :param ticket_id: {string} ConnectWise ticket id
        :param time_filter: {datetime} will fetch only time entries since that time (default None)
        :return: {dict} ticket time entries
        """
        url_request = urllib.parse.urlparse(self._url, GET_TICKET_TIME_ENTIRES)
        conditions = f"chargeToId={ticket_id}"
        # Add time filtering if necessary
        if time_filter:
            time_query = datetime.strftime(time_filter, self._date_format)
            conditions += f" and dateEntered>[{time_query}]"

        # Fetch 1000 time entries records
        r = self.session.get(
            url_request, params={"conditions": conditions, "pageSize": PAGE_SIZE}
        )
        self.validate_response(r)
        return r.json()


if __name__ == "__main__":
    cwm = ConnectWiseManager(
        COMPANY_URL, COMPANY_NAME, API_KEY_PUBLIC, API_KEY_PRIVATE, 50
    )
    # conn = cwm.test_connectivity()
    ticket_id = cwm.create_ticket(
        "TikcetApiTest",
        "Siemplify",
        "Siemplify T&M",
        status_name="Unassigned",
        priority_name="Priority 3 - Normal Response",
    )
    # r = cwm.get_ticket(ticket_id)
    r = cwm.update_ticket(
        "609620",
        summary="test ticket updated",
        type_name="Application",
        subtype_name="Adobe",
        item_name="Development",
    )
    # newComment = cwm.add_comment_to_ticket(ticket_id, "new comment 3")
    # newInternalComment = cwm.add_comment_to_ticket(ticket_id, "new internal comment 3", internal=True)
    # comments = cwm.get_ticket_comments_since_time(ticket_id, datetime(2018, 1, 7, 13, 0, 0))
    # comments = cwm.get_ticket_comments_since_time('608058', datetime(2018, 1, 15, 19, 20, 0))
    # time_entries = cwm.get_ticket_times_entries('608718', datetime(2018, 1, 18, 07, 20, 0))
    # r = cwm.close_ticket(ticket_id, custom_close_status="Completed")
    # # r = cwm.delete_ticket(ticket_id)
    # r = closed_tickets = cwm.get_close_tickets_since_time(datetime(2018, 1, 11, 1, 0, 0), custom_close_status="Completed")
    # r = filtered_tickets = cwm.get_tickets_by_filter(summary_filter="test", company_filter="Siemplify", board_filter="T&M")
    # r = cwm.get_tickets_by_conditions("status/name='Completed'")
    print("")
