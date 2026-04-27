# ==============================================================================
# title           :AlienVaultAnywhereManagerV1.py
# description     :This Module contain all AlienVaultAnywhere API functionality (V1)
# python_version  :2.7
# api_version     :v1.0
# ==============================================================================

from __future__ import annotations
import requests
from copy import deepcopy
from .SiemplifyParser import SiemplifyParser

HEADERS = {
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Accept": "application/json, text/plain, */*",
    "X-XSRF-TOKEN": None,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36",
    "Content-Type": "application/json;charset=UTF-8",
    "Accept-Encoding": "gzip, deflate, br",
}

NEW_COOKIE = "JSESSIONID={session_id}"

LIMIT_PER_REQUEST = 100

ALARMS_QUERY = {
    "size": LIMIT_PER_REQUEST,
    "from": 0,
    "query": {
        "bool": {
            "filter": {
                "and": [
                    {"term": {"message.suppressed": "false"}},
                    {"terms": {"message.status": ["open", "in review"]}},
                    {
                        "range": {
                            "message.timestamp_occured": {"gte": None, "lte": None}
                        }
                    },
                ]
            },
            "_cache": True,
        }
    },
    "sort": {"message.timestamp_occured": "asc"},
}


class AlienVaultManagerV1Exception(Exception):
    pass


class AlienVaultAnywhereManagerV1:
    def __init__(self, api_root, username, password, use_ssl=False, siemplify=None):
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.session = requests.Session()
        self.session.verify = use_ssl
        self.session.headers = deepcopy(HEADERS)
        self.login(username, password)
        self.siemplify_parser = SiemplifyParser()
        self.siemplify = siemplify

    def login(self, username, password):
        """
        Login to AlienVault Anywhere.
        :param username: {str} Username
        :param password: {str} Password
        :return: {bool} True if successful, exception otherwise
        """
        # Open the login page
        base_login_url = f"{self.api_root}/#/login"
        response = self.session.get(base_login_url)
        self.validate_response(response, "Unable to login")

        # Set session headers
        self.session.headers["X-XSRF-TOKEN"] = response.cookies.get("XSRF-TOKEN")
        self.session.headers["Cookie"] = NEW_COOKIE.format(
            session_id=response.cookies.get("JSESSIONID")
        )

        # Perform api login
        login_req_url = f"{self.api_root}/api/1.0/login"
        response = self.session.post(
            login_req_url, json={"email": username, "password": password}
        )

        self.validate_response(response, "Unable to login")

        # Set updated headers
        self.session.headers["Cookie"] = NEW_COOKIE.format(
            session_id=response.headers.get("set-cookie")
            .split("JSESSIONID=")[-1]
            .split(";")[0]
        )

        new_xsrf_url = f"{self.api_root}/api/1.0/user"
        response = self.session.get(new_xsrf_url)

        self.validate_response(response, "Unable to login")

        # Update XSRF Token
        self.session.headers["X-XSRF-TOKEN"] = (
            response.headers.get("set-cookie").split("XSRF-TOKEN=")[-1].split(";")[0]
        )
        return True

    def test_connectivity(self):
        """
        Test connectivity to AlienVault Anywhere
        :return: {bool} True if successful, exception otherwise.
        """
        response = self.session.get(f"{self.api_root}/api/1.0/license")
        self.validate_response(response)
        return True

    def _paginate_results(
        self,
        url,
        limit=None,
        from_time=None,
        to_time=None,
        alarms_json_ids=[],
        priority=None,
        show_suppressed=False,
        intent=None,
        strategy=None,
        method=None,
    ):
        """
        Paginate the results
        :param url: {str} The url to send request to
        :param limit: {int} The limit of the results to fetch
        :param from_time: {str} Fetch results that were created after the specified date. (unix timestamp)
        :param to_time: {str} Time to fetch alarms until (unix timestamp)
        :param alarms_json_ids: {list} old ids
        :param priority: {string}  The priority of the alarm. e.g. medium
        :param show_suppressed: {boolean} filter alarms by the suppressed flag.
        :param intent: {string} The intent of the rule that triggered the alarm. e.g. Environmental Awareness
        :param strategy: {string} The strategy of the rule that triggered the alarm. e.g. Network Access Control Modification
        :param method: {string} The method of the rule that triggered the alarm. e.g. AWS EC2 Security Group Modified
        :return: {list} List of results
        """
        from_filter = 0
        # Filter Adjustment
        payload = deepcopy(ALARMS_QUERY)
        payload["query"]["bool"]["filter"]["and"][-1]["range"][
            "message.timestamp_occured"
        ]["gte"] = from_time
        payload["query"]["bool"]["filter"]["and"][-1]["range"][
            "message.timestamp_occured"
        ]["lte"] = to_time

        if show_suppressed:
            payload["query"]["bool"]["filter"]["and"][0]["term"][
                "message.suppressed"
            ] = "true"
        if priority:
            payload["query"]["bool"]["filter"]["and"].append(
                {"term": {"message.priority_label": priority}}
            )
        if intent:
            payload["query"]["bool"]["filter"]["and"].append(
                {"term": {"message.rule_intent": intent}}
            )
        if strategy:
            payload["query"]["bool"]["filter"]["and"].append(
                {"term": {"message.rule_strategy": strategy}}
            )
        if method:
            payload["query"]["bool"]["filter"]["and"].append(
                {"term": {"message.rule_method": method}}
            )

        response = self.session.post(url, json=payload)
        self.siemplify.LOGGER.info(
            f"The request being sent: {str(vars(response.request))}"
        )
        self.validate_response(response, "Unable to get alarms")

        results = [
            alarm.get("_id")
            for alarm in response.json().get("hits", {}).get("hits", [])
        ]

        # filter old ids
        results = [alarm_id for alarm_id in results if alarm_id not in alarms_json_ids]

        while len(results) < response.json().get("hits", {}).get("total"):
            self.siemplify.LOGGER.info(
                "This is an added log from the Manager that runs in the while loop during pagination."
            )
            if limit and len(results) >= limit:
                return results[:limit]

            from_filter += len(results)

            payload["from"] = from_filter

            response = self.session.post(url, json=payload)

            self.validate_response(response, "Unable to get alarms")
            new_results = [
                alarm.get("_id")
                for alarm in response.json().get("hits", {}).get("hits", [])
            ]
            # filter old ids
            new_results = [
                alarm_id for alarm_id in new_results if alarm_id not in alarms_json_ids
            ]
            results.extend(new_results)

        return results[:limit] if limit else results

    def get_alarm(self, alarm_id):
        """
        Get an alarm by id
        :param alarm_id: {str} The alarm id to search for
        :return: {AlienVaultAlarmModel} The alarm info after parsing
        """
        alarm_data_url = f"{self.api_root}/api/1.0/alarms/{alarm_id}"
        response = self.session.get(alarm_data_url)

        self.validate_response(response)

        if response.json().get(alarm_id):
            alarm = response.json()[alarm_id].get("message")
            return self.siemplify_parser.build_siemplify_alarm_object(alarm)

        raise AlienVaultManagerV1Exception(f"Alarm {alarm_id} was not found")

    def get_alarms(
        self,
        from_time=None,
        to_time=None,
        limit=None,
        alarms_json_ids=[],
        priorities=None,
        show_suppressed=False,
        intent=None,
        strategy=None,
        method=None,
        use_suppressed_filter=None,
    ):
        """
        Get alarms
        :param from_time: {str} Time to fetch alarms from (unix timestamp)
        :param to_time: {str} Time to fetch alarms until (unix timestamp)
        :param limit: {int} Alarms count limit
        :param alarms_json_ids: {list} alarms ids that already fetched
        :param priorities: {list}  The priority of the alarm. e.g. medium
        :param show_suppressed: {boolean} filter alarms by the suppressed flag.
        :param use_suppressed_filter: {boolean} indicator to use suppressed filter or not
        :param intent: {string} The intent of the rule that triggered the alarm. e.g. Environmental Awareness
        :param strategy: {string} The strategy of the rule that triggered the alarm. e.g. Network Access Control Modification
        :param method: {string} The method of the rule that triggered the alarm. e.g. AWS EC2 Security Group Modified
        :return: {list} of {AlienVaultAlarmModel} The alarm info after parsing
        """
        alarms = []
        # Getting alarms
        # Get all alarms ids from timestamp, but not process them all.
        # Fetch all to not lose some alerts
        alarms_url = f"{self.api_root}/api/1.0/esproxy/main/alarms*/_search"
        alarms_ids = []

        if priorities:
            for priority in priorities:
                alarms_ids.extend(
                    self._paginate_results(
                        alarms_url,
                        from_time=from_time,
                        to_time=to_time,
                        limit=limit,
                        alarms_json_ids=alarms_json_ids,
                        priority=priority,
                        show_suppressed=show_suppressed,
                        intent=intent,
                        strategy=strategy,
                        method=method,
                    )
                )
        else:
            alarms_ids = self._paginate_results(
                alarms_url,
                from_time=from_time,
                to_time=to_time,
                limit=limit,
                alarms_json_ids=alarms_json_ids,
                show_suppressed=show_suppressed,
                intent=intent,
                strategy=strategy,
                method=method,
            )

        for alarm_id in alarms_ids:
            # Join all the found alarms
            alarms.append(self.get_alarm(alarm_id))

        # Sort the found alarms by timestamp
        alarms = sorted(alarms, key=lambda alarm: alarm.timestamp)

        return alarms[:limit] if limit else alarms

    def get_alarm_by_id(self, alarm_id):
        raise NotImplementedError(
            "This method is not supported in V1 version. Please switch to V2."
        )

    def get_events(
        self,
        start_time=None,
        end_time=None,
        account_name=None,
        event_name=None,
        source_name=None,
        limit=100,
        asc=False,
        suppressed=False,
    ):
        raise NotImplementedError(
            "This method is not supported in V1 version. Please switch to V2."
        )

    @staticmethod
    def validate_response(res, error_msg="An error occurred"):
        """
        Validate a response
        :param error_msg: {str} The error message to display
        :param res: {requests.Response} The response to validate
        """
        try:
            res.raise_for_status()

        except requests.HTTPError as error:
            raise Exception(f"{error_msg}: {error} {error.response.content}")
