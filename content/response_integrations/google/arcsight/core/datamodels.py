from __future__ import annotations
from TIPCommon import dict_to_flat, construct_csv
from TIPCommon.data_models import BaseAlert
from io import StringIO
import csv
from .UtilsManager import remove_brackets, replace_spaces_with_underscore
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.raw_data)


class MSSObject(BaseModel):
    def __init__(self, raw_data):
        super(MSSObject, self).__init__(raw_data)


class EntriesObject(BaseModel):
    def __init__(self, raw_data, columns=None, entry_list=None, enries_count=None):
        super(EntriesObject, self).__init__(raw_data)
        self.columns = columns
        self.entry_list = entry_list
        self.enries_count = enries_count

    def to_csv(self):
        return construct_csv(self.to_mapped_json())

    def to_json(self, map_columns=False):
        return self.to_mapped_json() if map_columns else self.raw_data

    def to_mapped_json(self):
        entry_list = (
            self.entry_list if isinstance(self.entry_list, list) else [self.entry_list]
        )
        return [
            dict(
                zip(
                    self.columns if isinstance(self.columns, list) else [self.columns],
                    (
                        [values.get("entry")]
                        if isinstance(values.get("entry"), str)
                        else values.get("entry")
                    ),
                )
            )
            for values in entry_list
        ]


class RawObject(BaseModel):
    def __init__(self, raw_data, columns=None, rows_list=None, rows_count=None):
        super(RawObject, self).__init__(raw_data)
        self.columns = columns
        self.rows_list = rows_list
        self.rows_count = rows_count

    def to_csv(self):
        return construct_csv(self.to_mapped_json())

    def to_json(self, map_columns=False):
        return self.to_mapped_json() if map_columns else self.raw_data

    def to_mapped_json(self):
        mapped_json_results = []
        row_list = (
            self.rows_list if isinstance(self.rows_list, list) else [self.rows_list]
        )

        for row in row_list:
            row_data = {}
            for index, column in enumerate(self.columns):
                row_data[column] = row["value"][index].get("$", "")
            mapped_json_results.append(row_data)

        return mapped_json_results


class Report(BaseModel):
    def __init__(self, raw_data, uri, report_id, common_params, report_format):
        super(Report, self).__init__(raw_data)
        self.uri = uri
        self.report_id = report_id
        self.common_params = common_params
        self.report_format = report_format


class ReportContent(BaseModel):
    def __init__(self, raw_data):
        super(ReportContent, self).__init__(raw_data)
        self.json_data_holder = None

    def to_json(self, transform_data=False):
        results = []
        if not self.json_data_holder:
            self.json_data_holder = self.read_csv()

        if transform_data:
            for item in self.json_data_holder:
                result = {}
                for key, value in item.items():
                    result[remove_brackets(replace_spaces_with_underscore(key))] = value

                results.append(result)

        return self.json_data_holder if not transform_data else results

    def read_csv(self):
        return [
            dict(item)
            for item in list(csv.DictReader(StringIO(self.raw_data.decode())))
        ]

    def to_csv(self):
        return [dict_to_flat(report) for report in self.to_json()]


class QueryObject(BaseModel):
    def __init__(self, raw_data, id=None, name=None, enabled=None, description=None):
        super(QueryObject, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.description = description
        self.enabled = enabled

    def __repr__(self):
        return f"{self.id}"

    def to_table(self):
        return {
            "Description": self.description,
            "Name": self.name,
            "ID": self.id,
            "Enabled": self.enabled,
        }


class ActiveListObject(BaseModel):
    def __init__(self, raw_data, id=None, name=None, disabled=None, description=None):
        super(ActiveListObject, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.description = description
        self.disabled = disabled

    def __repr__(self):
        return f"{self.id}"

    def to_table(self):
        return {
            "Description": self.description,
            "Name": self.name,
            "ID": self.id,
            "Disabled": self.disabled,
        }


class CaseObject(BaseModel):
    def __init__(self, raw_data, id=None, name=None, stage=None):
        super(CaseObject, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.stage = stage

    def __repr__(self):
        return f"{self.id}"

    def to_table(self):
        return {"Name": self.name, "ID": self.id, "Stage": self.stage}


class ReportObject(BaseModel):
    def __init__(self, raw_data, id=None, name=None, uri=None, description=None):
        super(ReportObject, self).__init__(raw_data)
        self.id = id
        self.uri = uri
        self.name = name
        self.description = description

    def __repr__(self):
        return f"{self.id}"

    def to_table(self):
        return {
            "Description": self.description,
            "Name": self.name,
            "ID": self.id,
            "URI": self.uri,
        }


class Case(BaseModel):
    def __init__(self, raw_data, stage):
        super(Case, self).__init__(raw_data)
        self.stage = stage


class Correlation(BaseAlert):
    def __init__(
        self,
        raw_data,
        event_id=None,
        name=None,
        priority=None,
        start_time=None,
        end_time=None,
    ):
        super(Correlation, self).__init__(raw_data, event_id)
        self.flat_raw_data = dict_to_flat(raw_data)
        self.event_id = event_id
        self.name = name
        self.priority = int(priority)
        self.start_time = start_time
        self.end_time = end_time
        self.start_time_ms = convert_string_to_unix_time(start_time + "+00")
        self.end_time_ms = convert_string_to_unix_time(end_time + "+00")

    def get_siemplify_priority(self):
        """
        Get mapped priority from data
        :return: {int} Mapped value
        """
        if self.priority in [9, 10]:
            return 100  # Critical
        elif self.priority in [7, 8]:
            return 80  # High
        elif self.priority in [5, 6]:
            return 60  # Medium
        elif self.priority in [3, 4]:
            return 40  # Low

        return -1  # Informative
