# ==============================================================================
# title           :CBEnterpriseEDRManager.py
# description     :This Module contain all CB Enterprise EDR functionality
# author          :avital@siemplify.co
# date            :31-05-2020
# python_version  :2.7
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
import arrow
import time
from .CBEnterpriseEDRParser import CBEnterpriseEDRParser


# =====================================
#               CONFIG                #
# =====================================

SLEEP_TIME = 5
DEFAULT_PAGE_SIZE = 50
MAX_RETRY = 3

# =====================================
#               CONSTS                #
# =====================================


# =====================================
#              CLASSES                #
# =====================================


class CBEnterpriseEDRException(Exception):
    """
    General Exception for CB Enterprise EDR manager
    """

    pass


class CBEnterpriseEDRNotFoundError(Exception):
    """
    Not Found Exception for CB Enterprise EDR manager
    """

    pass


class CBEnterpriseEDRUnauthorizedError(Exception):
    """
    Unauthorized Exception for CB Enterprise EDR manager
    """

    pass


class CBEnterpriseEDRManager:
    """
    Responsible for all CB Enterprise EDR operations functionality
    """

    def __init__(self, api_root, org_key, api_id, api_secret_key, verify_ssl=False):
        """
        Connect to a CB Enterprise EDR instance
        """
        self.session = requests.session()
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.org_key = org_key
        self.session.headers["X-Auth-Token"] = f"{api_secret_key}/{api_id}"
        self.session.verify = verify_ssl
        self.parser = CBEnterpriseEDRParser()

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate response
        :param response: {requests.Response} The response to validate
        :param error_msg: {unicode} Default message to display on error
        """
        try:
            if response.status_code == 401:
                raise CBEnterpriseEDRUnauthorizedError(
                    "Unauthorized. Please check given credentials."
                )

            try:
                if response.status_code == 403:
                    raise CBEnterpriseEDRUnauthorizedError(
                        "Invalid organization ID. Please check given credentials."
                    )

                if (
                    response.status_code == 404
                    and response.json().get("error_code") == "NOT_FOUND"
                ):
                    raise CBEnterpriseEDRNotFoundError(error_msg)

            except (CBEnterpriseEDRUnauthorizedError, CBEnterpriseEDRNotFoundError):
                raise
            except:
                # Unable to parse out the JSON - let the error be raised as any regular error
                pass

            response.raise_for_status()

        except requests.HTTPError as error:
            raise CBEnterpriseEDRException(f"{error_msg}: {error} {response.content}")

    def test_connectivity(self):
        """
        Test connectivity to CB Enterprise EDR
        :return: {bool} True if successful, exception otherwise
        """
        response = self.session.get(
            f"{self.api_root}/threathunter/watchlistmgr/v3/orgs/{self.org_key}/watchlists"
        )
        self.validate_response(response, "Unable to connect to CB Enterprise EDR")
        return True

    def get_filehash_metadata(self, filehash):
        """
        Get the metadata of a SHA256
        :param filehash: {unicode} The sha256 hash
        :return: {FileHashMetadata} The found metadata of the hash
        """
        response = self.session.get(
            f"{self.api_root}/ubs/v1/orgs/{self.org_key}/sha256/{filehash}/metadata"
        )
        self.validate_response(response, f"Unable to get metadata for {filehash}")
        return self.parser.build_siemplify_filehash_metadata_obj(response.json())

    def get_filehash_summary(self, filehash):
        """
        Get the summary of a SHA256
        :param filehash: {unicode} The sha256 hash
        :return: {FileHashSummary} The found summary of the hash
        """
        response = self.session.get(
            f"{self.api_root}/ubs/v1/orgs/{self.org_key}/sha256/{filehash}/summary/device"
        )
        self.validate_response(response, f"Unable to get summary for {filehash}")
        return self.parser.build_siemplify_filehash_summary_obj(response.json())

    def process_search(
        self,
        device_name,
        query=None,
        sort_by=None,
        sort_order="ASC",
        timeframe=None,
        limit=None,
    ):
        """
        Search processes
        :param device_name: {string} The name of the device to filter against
        :param query: {string} The query to run
        :param sort_by: {string} Field name to sort by
        :param sort_order: {string} ASC / DESC
        :param timeframe: {int} X hours timeframe to search in
        :param limit: {int} Max results to return
        :return: {[Process]} Found processes
        """
        payload = {"criteria": {"device_name": [device_name]}}

        if query:
            payload["query"] = query

        if sort_by:
            payload["sort"] = [{"order": sort_order.lower(), "field": sort_by}]

        if timeframe:
            payload["time_range"] = {
                "end": arrow.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "start": arrow.utcnow()
                .shift(hours=-timeframe)
                .strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        response = self.session.post(
            f"{self.api_root}/api/investigate/v2/orgs/{self.org_key}/observations/search_jobs",
            json=payload,
        )

        self.validate_response(
            response, f"Unable to initiate process search for {device_name}"
        )
        job_id = response.json()["job_id"]

        counter = 0
        while counter < MAX_RETRY:

            processes = self._paginate_results(
                "GET",
                f"{self.api_root}/api/investigate/v2/orgs/{self.org_key}/observations/search_jobs/{job_id}/results",
                err_msg=f"Unable to get processes for {device_name}",
                limit=limit,
            )

            if processes:
                return [
                    self.parser.build_siemplify_process_obj(process)
                    for process in processes
                ]

            # The second request needs to wait a couple of seconds so the data in EDR are ready to be fetched
            time.sleep(SLEEP_TIME)
            counter += 1

        return [
            self.parser.build_siemplify_process_obj(process) for process in processes
        ]

    def events_search(
        self,
        process_guid,
        event_types=None,
        query=None,
        sort_by=None,
        sort_order="ASC",
        timeframe=None,
        limit=None,
    ):
        """
        Get events associated with specific process by process guid
        :param process_guid: {string} The guid of the process to filter against
        :param query: {string} The query to run
        :param event_types: {list} The types of the events to search for
        :param sort_by: {string} Field name to sort by
        :param sort_order: {string} ASC / DESC
        :param timeframe: {int} X hours timeframe to search in
        :param limit: {int} Max results to return
        :return: {[Event]} Found events
        """
        payload = {}

        if event_types:
            payload["criteria"] = {"event_type": event_types}

        if query:
            payload["query"] = query

        if sort_by:
            payload["sort"] = [{"order": sort_order.lower(), "field": sort_by}]

        if timeframe:
            payload["time_range"] = {
                "end": arrow.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "start": arrow.utcnow()
                .shift(hours=-timeframe)
                .strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        events = self._paginate_results(
            "POST",
            f"{self.api_root}/api/investigate/v2/orgs/{self.org_key}/events/{process_guid}/_search",
            body=payload,
            err_msg=f"Unable to get events for process {process_guid}",
            limit=limit,
            pagination_in_payload=True,
        )
        return [self.parser.build_siemplify_event_obj(event) for event in events]

    def _paginate_results(
        self,
        method,
        url,
        params=None,
        body=None,
        limit=None,
        err_msg="Unable to get results",
        pagination_in_payload=False,
    ):
        """
        Paginate the results of a job
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param limit: {int} The limit of the results to fetch
        :param err_msg: {str} The message to display on error
        :param pagination_in_payload: {bool} Whether the pagination should be done in query string or body
        :return: {list} List of results
        """
        if pagination_in_payload:
            if body is None:
                body = {}

            body.update(
                {
                    "start": 0,
                    "rows": (
                        min(DEFAULT_PAGE_SIZE, limit) if limit else DEFAULT_PAGE_SIZE
                    ),
                }
            )

        else:
            if params is None:
                params = {}

            params.update(
                {
                    "start": 0,
                    "rows": (
                        min(DEFAULT_PAGE_SIZE, limit) if limit else DEFAULT_PAGE_SIZE
                    ),
                }
            )

        response = self.session.request(method, url, params=params, json=body)

        self.validate_response(response, err_msg)
        results = response.json().get("results", [])

        while True:
            if limit and len(results) >= limit:
                break

            if not response.json().get("results"):
                break

            if pagination_in_payload:
                body.update({"start": len(results)})

            else:
                params.update({"start": len(results)})

            response = self.session.request(method, url, params=params, json=body)

            self.validate_response(response, err_msg)
            results.extend(response.json().get("results", []))

        return results[:limit] if limit else results
