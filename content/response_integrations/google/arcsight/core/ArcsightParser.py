from __future__ import annotations
from .datamodels import *
import csv

FILE_FORMATS = {"0": "pdf", "1": "xls", "2": "rtf", "3": "csv", "4": "html"}


class ArcsightParser:
    def build_search_response_object(self, raw_data):
        raw_data = (
            raw_data.get("mss.search1Response", {})
            .get("mss.return", {})
            .get("searchHits", [])
        )
        raw_data = raw_data if isinstance(raw_data, list) else [raw_data]
        return [self.build_mss_object(raw_data=item) for item in raw_data]

    def build_mss_object(self, raw_data):
        return MSSObject(raw_data=raw_data)

    def build_activelist_entries_object(self, raw_data, limit=None):
        entry_list = (
            raw_data.get("act.getEntriesResponse", {})
            .get("act.return", {})
            .get("entryList", [])
        )
        if limit and isinstance(entry_list, list):
            entry_list = entry_list[:limit]
            raw_data["act.getEntriesResponse"]["act.return"]["entryList"] = entry_list

        return EntriesObject(
            raw_data=raw_data,
            columns=raw_data.get("act.getEntriesResponse", {})
            .get("act.return", {})
            .get("columns", []),
            entry_list=entry_list,
            enries_count=len(entry_list),
        )

    def build_query_raws_object(self, raw_data, limit=None):
        rows_list = (
            raw_data.get("qvs.getMatrixDataResponse", {})
            .get("qvs.return", {})
            .get("rows", [])
        )
        if limit and isinstance(rows_list, list):
            rows_list = rows_list[:limit]
            raw_data["qvs.getMatrixDataResponse"]["qvs.return"]["rows"] = rows_list

        return RawObject(
            raw_data=raw_data,
            columns=raw_data.get("qvs.getMatrixDataResponse", {})
            .get("qvs.return", {})
            .get("columnHeaders", []),
            rows_list=rows_list,
            rows_count=len(rows_list),
        )

    def get_token(self, raw_data):
        return raw_data.get("log.loginResponse", {}).get("log.return", "")

    def get_uuid(self, raw_data):
        return (
            raw_data.get("act.getResourceByNameResponse", {})
            .get("act.return", {})
            .get("reference", {})
            .get("id", "")
        )

    def build_case_by_name_object(self, raw_data):
        raw_data = raw_data.get("cas.getResourceByNameResponse", {}).get(
            "cas.return", {}
        )

        return Case(raw_data=raw_data, stage=raw_data.get("stage", ""))

    def get_query_uuid(self, raw_data):
        return (
            raw_data.get("qvs.getResourceByNameResponse", {})
            .get("qvs.return", {})
            .get("reference", {})
            .get("id", "")
        )

    def build_report_info_object(self, raw_data, report_format):
        raw_data = raw_data.get("rep.getResourcesByNameSafelyResponse", {}).get(
            "rep.return", {}
        )
        return Report(
            raw_data=raw_data,
            uri=raw_data.get("URI", ""),
            report_id=raw_data.get("reference", {}).get("id", ""),
            common_params=raw_data.get("commonParameters", []),
            report_format=self.get_report_format(
                raw_data.get("commonParameters", []), report_format
            ),
        )

    def get_report_format(self, data, report_format):
        for item in data:
            if item.get("displayName", "") == report_format:
                return FILE_FORMATS.get(str(item.get("value")))

        return None

    def get_report_download_token(self, raw_data):
        return raw_data.get(
            "arc.initDefaultArchiveReportDownloadWithOverwriteResponse", {}
        ).get("arc.return", "")

    def build_report_content(self, report_content):
        return ReportContent(raw_data=report_content)

    def to_list(self, raw_data):
        return raw_data if isinstance(raw_data, list) else [raw_data]

    def get_resources_ids(self, raw_data, key_prefix=None, limit=None):
        resources = raw_data.get(f"{key_prefix}.findAllIdsResponse", {})
        ids = resources.get(f"{key_prefix}.return", []) if resources else []
        return ids[:limit] if limit else ids

    def build_queries(self, raw_data):
        return [
            self.build_query_object(query)
            for query in self.to_list(
                raw_data.get("qvs.getResourcesByIdsResponse", {}).get("qvs.return", [])
            )
        ]

    def build_query_object(self, raw_data):
        return QueryObject(
            raw_data=raw_data,
            id=raw_data.get("resourceid"),
            name=raw_data.get("name", ""),
            enabled=raw_data.get("enabled", ""),
            description=raw_data.get("description", ""),
        )

    def build_active_lists(self, raw_data):
        return [
            self.build_active_list_object(active_list)
            for active_list in self.to_list(
                raw_data.get("act.getResourcesByIdsResponse", {}).get("act.return", [])
            )
        ]

    def build_active_list_object(self, raw_data):
        return ActiveListObject(
            raw_data=raw_data,
            id=raw_data.get("resourceid"),
            name=raw_data.get("name", ""),
            disabled=raw_data.get("disabled", ""),
            description=raw_data.get("description", ""),
        )

    def build_cases(self, raw_data):
        return [
            self.build_case_object(case)
            for case in self.to_list(
                raw_data.get("cas.getResourcesByIdsResponse", {}).get("cas.return", [])
            )
        ]

    def build_case_object(self, raw_data):
        return CaseObject(
            raw_data=raw_data,
            id=raw_data.get("resourceid"),
            name=raw_data.get("name", ""),
            stage=raw_data.get("stage"),
        )

    def build_reports(self, raw_data):
        return [
            self.build_report_object(report)
            for report in self.to_list(
                raw_data.get("rep.getResourcesByIdsResponse", {}).get("rep.return", [])
            )
        ]

    def build_report_object(self, raw_data):
        return ReportObject(
            raw_data=raw_data,
            id=raw_data.get("resourceid"),
            name=raw_data.get("name", ""),
            uri=raw_data.get("URI"),
            description=raw_data.get("description", ""),
        )

    def build_correlations_list(self, raw_data):
        raw_list = list(csv.reader(raw_data.splitlines(), delimiter=","))
        headers = [key.replace(" ", "_") for key in raw_list[0]]
        list_of_dicts = [dict(zip(headers, row)) for row in raw_list[1:]]
        return [self.build_correlation_object(item) for item in list_of_dicts]

    @staticmethod
    def build_correlation_object(raw_data):
        return Correlation(
            raw_data=raw_data,
            event_id=raw_data.get("Event_ID"),
            name=raw_data.get("Name"),
            priority=raw_data.get("Priority"),
            start_time=raw_data.get("Start_Time"),
            end_time=raw_data.get("End_Time"),
        )
