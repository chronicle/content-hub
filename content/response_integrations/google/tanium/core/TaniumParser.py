from __future__ import annotations
from tanium.core.datamodels import *


class TaniumParser:
    def build_results(
        self, raw_json, method, data_key="data", pure_data=False, limit=None, **kwargs
    ):
        return [
            getattr(self, method)(item_json, **kwargs)
            for item_json in (raw_json if pure_data else raw_json.get(data_key, []))[
                :limit
            ]
        ]

    @staticmethod
    def build_question_obj(raw_data):
        return Question(raw_data, **raw_data)

    @staticmethod
    def build_endpoint_details_obj(raw_data: dict) -> EndpointDetails:
        """Build EndpointDetails object from raw data

        Args:
            raw_data (dict): raw data

        Returns:
           EndpointDetails object
        """
        return EndpointDetails(
            raw_data=raw_data,
            ip=raw_data.get("ip"),
            hostname=raw_data.get("hostname"),
            client_id=raw_data.get("clientId"),
            platform=raw_data.get("platform"),
            status=raw_data.get("status"),
        )

    def build_question_result_obj(self, raw_data, limit=None):
        short_raw_data = raw_data.get("data", {}).get("result_sets", [])
        short_raw_data = short_raw_data[0] if short_raw_data else {}
        return QuestionResult(
            raw_data=raw_data,
            short_raw_data=short_raw_data,
            columns=self._get_columns(short_raw_data, limit),
            rows=self._get_rows(short_raw_data, limit),
        )

    def _get_columns(self, raw_data, limit=None):
        return raw_data.get("columns", [])[:limit] if raw_data else {}

    def _get_rows(self, raw_data, limit=None):
        return raw_data.get("rows", [])[:limit] if raw_data else {}

    @staticmethod
    def build_connection_obj(raw_data):
        return Connection(
            raw_data=raw_data,
            id=raw_data.get("id"),
            ip=raw_data.get("ip"),
            hostname=raw_data.get("hostname"),
            client_id=raw_data.get("clientId"),
            platform=raw_data.get("platform"),
            status=raw_data.get("status"),
        )

    def build_tasks_list(self, raw_json):
        return [
            self.build_task_obj(raw_json=item, single_data=False)
            for item in raw_json.get("data", [])
        ]

    @staticmethod
    def build_task_obj(raw_json, single_data=True):
        raw_data = raw_json.get("data", {}) if single_data else raw_json
        results = raw_data.get("results", {})
        file_results = (
            results.get("fileResults", [])
            if results and isinstance(results, dict)
            else []
        )
        metadata = (
            raw_data.get("metadata", {})
            if raw_data.get("metadata") and isinstance(raw_data.get("metadata"), dict)
            else {}
        )
        return Task(
            raw_data=raw_data,
            id=raw_data.get("id"),
            status=raw_data.get("status"),
            file_uuid=file_results[0].get("uuid") if file_results else "",
            file_path=(
                file_results[0].get("response", {}).get("source")
                if file_results
                else ""
            ),
            meta_type=metadata.get("type", "") if metadata else "",
            meta_id=metadata.get("id", "") if metadata else "",
        )
