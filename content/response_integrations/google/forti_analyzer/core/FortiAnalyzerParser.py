from __future__ import annotations
from typing import Any, Dict

from forti_analyzer.core.datamodels import *
from typing import Any, List, Dict


class FortiAnalyzerParser:
    def build_results(
        self,
        raw_json: list or dict,
        method: str,
        data_key: str = "data",
        pure_data: bool = False,
        limit: int = None,
        **kwargs
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
    def get_data(raw_data: dict) -> List or Dict:
        """
        Get data from provided raw data
        Args:
            raw_data (dict): raw data

        Returns:
            (list or dict):
        """
        return raw_data.get("result", {}).get("data", [])

    @staticmethod
    def build_alert_object(raw_data: dict) -> Alert:
        """
        Build Alert object from raw data
        Args:
            raw_data (dict): raw data

        Returns:
            (Alert): Alert object
        """
        return Alert(
            raw_data=raw_data,
            adom=raw_data.get("adom"),
            alert_id=raw_data.get("alertid"),
            alert_time=raw_data.get("alerttime"),
            subject=raw_data.get("subject").replace("desc:", ""),
            severity=raw_data.get("severity"),
            trigger_name=raw_data.get("triggername"),
            first_log_time=raw_data.get("firstlogtime"),
            last_log_time=raw_data.get("lastlogtime"),
        )

    @staticmethod
    def build_device_obj(raw_json: dict) -> Device:
        """
        Build Device object from raw data
        Args:
            raw_json (dict): raw data

        Returns:
            (Device): Device object
        """
        return Device(
            raw_data=raw_json,
            adm_user=raw_json.get("adm_usr"),
            build=raw_json.get("build"),
            ip_address=raw_json.get("ip"),
            last_checked=raw_json.get("last_checked"),
            last_resync=raw_json.get("last_resync"),
            name=raw_json.get("name"),
            sn=raw_json.get("sn"),
            os_type=raw_json.get("os_type"),
            os_ver=raw_json.get("os_ver"),
            patch=raw_json.get("patch"),
            platform_str=raw_json.get("platform_str"),
            version=raw_json.get("version"),
            desc=raw_json.get("desc"),
        )

    @staticmethod
    def build_log_object(raw_data: Dict[str, Any]) -> Log:
        """
        Parser method for creating Log object
        Args:
            raw_data: dict
        Returns:
            Log object
        """
        return Log(raw_data=raw_data, log_id=raw_data.get("id"))

    def build_search_log_objects(self, raw_data: Dict[str, Any]):
        """
        Parser method creates Log object from
        Args:
            raw_data: Dict

        Returns:
            List of Log objects
        """
        logs = raw_data.get("result", {}).get("data", [])
        if not logs:
            return None
        return [self.build_log_object(log) for log in logs]

    @staticmethod
    def build_alert_comment_response_object(raw_data: dict) -> AlertCommentResponse:
        """
        Build AlertCommentResponse object from raw data
        Args:
            raw_data (dict): raw data
        Returns:
            (AlertCommentResponse): AlertCommentResponse object
        """
        return AlertCommentResponse(raw_data=raw_data)
