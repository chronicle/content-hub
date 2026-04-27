from __future__ import annotations
from copy import copy

from TIPCommon import dict_to_flat


class BaseData:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_table(self):
        return [self.to_csv()]

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_json(self):
        return self.raw_data


class Message(BaseData):
    def __init__(self, raw_data, subject=None, sender=None, recipients=None):
        super(Message, self).__init__(raw_data)
        self.subject = subject
        self.sender = sender
        self.recipients = recipients if recipients else []


class Report(BaseData):
    def __init__(
        self,
        raw_data: dict,
        begin_time: str,
        end_time: str,
        begin_timestamp: float,
        end_timestamp: float,
        report_type: str,
    ):
        super(Report, self).__init__(raw_data)
        self.begin_time = begin_time
        self.end_time = end_time
        self.begin_timestamp = begin_timestamp
        self.end_timestamp = end_timestamp
        self.report_type = report_type


class DynamicReport(Report):
    def __init__(
        self,
        raw_data: dict,
        begin_time: str,
        end_time: str,
        begin_timestamp: float,
        end_timestamp: float,
        report_type: str,
        **kwargs
    ):
        super(DynamicReport, self).__init__(
            raw_data, begin_time, end_time, begin_timestamp, end_timestamp, report_type
        )
        for attribute, value in kwargs.items():
            setattr(self, attribute, value)

    def to_json(self):
        result = copy(self.__dict__)
        del result["raw_data"]
        return result
