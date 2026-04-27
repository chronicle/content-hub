from __future__ import annotations
from .datamodels import *
from .constants import COMPLETED_STATUS


class ExchangeExtensionPackParser:
    def get_compliance_search_status(self, raw_data):
        return SearchStatus(
            raw_data=raw_data,
            name=raw_data.get("Name"),
            run_by=raw_data.get("RunBy"),
            job_end_time=raw_data.get("JobEndTime"),
            status=raw_data.get("Status"),
        )

    def get_compliance_search_preview_status_and_results(
        self, raw_data, compliance_search_name, limit
    ):
        status = raw_data.get("Status")

        if status != COMPLETED_STATUS:
            return status, []

        results_list = self.get_results_list(
            raw_data.get("Results"), compliance_search_name, limit
        )

        return status, [
            SearchResult(
                raw_data=result,
                location=result.get("Location"),
                sender=result.get("Sender"),
                subject=result.get("Subject"),
                type=result.get("Type"),
                size=result.get("Size"),
                received_time=result.get("Received Time"),
                data_link=result.get("Data Link"),
            )
            for result in results_list
        ]

    def get_compliance_search_results(self, results_list):
        return [
            SearchResult(
                raw_data=result,
                location=result.get("Location"),
                sender=result.get("Sender"),
                subject=result.get("Subject"),
                type=result.get("Type"),
                size=result.get("Size"),
                received_time=result.get("Received Time"),
                data_link=result.get("Data Link"),
            )
            for result in results_list
        ]

    def get_results_list(self, raw_data, compliance_search_name, limit):
        results = raw_data[1:-1].splitlines()
        results_list = []

        for result in results:
            item = dict(
                (key.strip(), value.strip())
                for key, value in tuple(
                    element.split(": ", 1) for element in result.split("; ")
                )
            )
            item["Name"] = compliance_search_name
            results_list.append(item)

        return results_list[:limit] if limit else results_list

    def get_compliance_search_purge_status_and_result(self, raw_data):
        return raw_data.get("Status"), self.get_result_data(
            raw_data.get("Results")
            if raw_data.get("Status") == COMPLETED_STATUS
            else ""
        )

    def get_result_data(self, raw_data):
        start_keyword = "Details: {"
        end_keyword = "}"
        details = raw_data[
            raw_data.find(start_keyword)
            + len(start_keyword) : raw_data.find(end_keyword)
        ]
        raw_data = raw_data.replace(details, "")

        data = dict(
            [
                item
                for item in [
                    tuple(element.split(": ", 1)) for element in raw_data.split("; ")
                ]
                if len(item) == 2
            ]
        )

        return {
            "Purge Type": data.get("Purge Type"),
            "Item count": data.get("Item count"),
        }

    def build_rule_objects(self, raw_data):
        raw_data = raw_data if isinstance(raw_data, list) else [raw_data]

        return [
            Rule(
                raw_data=item,
                name=item.get("Name"),
                items=item.get("From") or item.get("FromAddressContainsWords"),
            )
            for item in raw_data
        ]
