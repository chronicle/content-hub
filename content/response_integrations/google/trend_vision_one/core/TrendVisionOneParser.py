from __future__ import annotations

from typing import List
from .datamodels import *
from typing import Any, List, Dict, Optional

from .constants import SUCCESSFUL_STATUS_CODES, TOO_MANY_REQUESTS


class TrendVisionOneParser:
    def build_results(
        self,
        raw_json: list or dict,
        method: str,
        data_key: str = "items",
        pure_data: bool = False,
        limit: int = None,
        **kwargs,
    ) -> [Any]:
        """
        Build results using provided method
        Args:
            raw_json (dict or list): raw data to build results from
            method (str): parser method to use
            data_key (str): key to use to get needed data from raw data
            pure_data (str): specifies if provided raw data should be used as provided or no
            limit (int): limit for results

        Returns:
            ([any]): list of objects
        """
        return [
            getattr(self, method)(item_json, **kwargs)
            for item_json in (raw_json if pure_data else raw_json.get(data_key, []))[
                :limit
            ]
        ]

    @staticmethod
    def get_items(raw_data: dict) -> List or Dict:
        """
        Get items from provided raw data
        Args:
            raw_data (dict): raw data

        Returns:
            (list or dict):
        """
        return raw_data.get("items", {})

    @staticmethod
    def build_alert_object(raw_data: dict) -> Alert:
        """
        Build Alert object from raw data
        Args:
            raw_data (dict): raw data

        Returns:
            (Alert): Alert object
        """

        alert_id = raw_data.get("id", "").replace("\u0000", "")
        model = raw_data.get("model", "").replace("\u0000", "")
        description = raw_data.get("description", "").replace("\u0000", "")

        return Alert(
            raw_data=raw_data,
            alert_id=alert_id,
            model=model,
            description=description,
            severity=raw_data.get("severity"),
            created_datetime=raw_data.get("createdDateTime"),
        )

    @staticmethod
    def build_endpoint_obj(raw_json: dict) -> Endpoint:
        """
        Build Endpoint object from raw data
        Args:
            raw_json (dict): raw data

        Returns:
            (Endpoint): Endpoint object
        """
        return Endpoint(
            raw_data=raw_json,
            guid=raw_json.get("agentGuid"),
            os_description=raw_json.get("osDescription"),
            login_account_value=raw_json.get("loginAccount", {}).get("value", []),
            endpoint_name_value=raw_json.get("endpointName", {}).get("value"),
            ip_value=raw_json.get("ip", {}).get("value", []),
            installed_product_codes=raw_json.get("installedProductCodes", []),
        )

    @staticmethod
    def build_task_obj(raw_json: dict) -> Task:
        return Task(
            raw_data=raw_json, status=raw_json.get("status"), id=raw_json.get("id")
        )

    @staticmethod
    def build_script_objects(raw_json: dict) -> List[Script]:
        return [
            Script(raw_data=script_dict) for script_dict in raw_json.get("items", [])
        ]

    @staticmethod
    def build_submit_file_object(raw_json: dict) -> SubmitFile:
        """
        Build Submit File object from raw data
        Args:
            raw_json (list): raw data from Submit File action

        Returns:
            (SubmitFile): SubmitFile object
        """
        if raw_json:
            return SubmitFile(raw_json, task_id=raw_json.get("id"))

    @staticmethod
    def build_submit_url_object(
        raw_json: list,
    ) -> tuple[list[SubmitURL], list[SubmitURL]]:
        """
        Build Submit URL object from raw data
        Args:
            raw_json (list): list of raw data from multiple url submissions

        Returns:
            list[SubmitURL]: list of SubmitURL objects
        """
        successful_url_submissions: list[SubmitURL] = []
        unsuccessful_url_submissions: list[SubmitURL] = []
        limit_exceed_url_submissions: list[SubmitURL] = []
        for result in raw_json:
            if result["status"] in SUCCESSFUL_STATUS_CODES:
                successful_url_submissions.append(
                    SubmitURL(
                        raw_json,
                        task_id=result["body"]["id"],
                        url=result["body"]["url"],
                    )
                )
            else:
                if result["status"] == TOO_MANY_REQUESTS:
                    limit_exceed_url_submissions.append(SubmitURL(raw_json))
                unsuccessful_url_submissions.append(
                    SubmitURL(raw_json, url=result.get("body", {}).get("url"))
                )
        return successful_url_submissions, limit_exceed_url_submissions

    @staticmethod
    def build_execute_email_object(raw_json: dict[str, Any]) -> ExecuteEmail:
        """
        Build Execute Email object from raw data
        Args:
            raw_json (dict): raw data

        Returns:
            (ExecuteEmail): ExecuteEmail object
        """
        task_id: Optional[str] = None
        task_location_url: Optional[str] = None
        if raw_json.get("status") in SUCCESSFUL_STATUS_CODES:
            for header in raw_json.get("headers"):
                if header.get("name") == "Operation-Location":
                    task_location_url = header.get("value")
                    task_id = task_location_url.split("tasks/")[-1]
                    return ExecuteEmail(
                        raw_json, task_id=task_id, url=task_location_url
                    )
        return ExecuteEmail(
            raw_json,
            error_message=raw_json.get("body", {}).get("error", {}).get("message"),
        )

    @staticmethod
    def build_task_detail_object(raw_json: dict) -> TaskDetail:
        """
        Build Task Detail object from raw data
        Args:
            raw_json (dict): raw data

        Returns:
            (TaskDetail): TaskDetail object
        """
        return TaskDetail(
            raw_json,
            task_id=raw_json.get("id"),
            action=raw_json.get("action"),
            status=raw_json.get("status"),
        )
