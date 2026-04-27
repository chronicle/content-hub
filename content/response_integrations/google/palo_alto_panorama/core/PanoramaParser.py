from __future__ import annotations
import xmltodict
from .PanoramaExceptions import ResponseObjectNotSet
from .datamodels import *


class PanoramaParser:
    def __init__(self):
        self.__response = None
        self.json_response = {}

    def set_response(self, response):
        self.__response = response
        self.json_response = self.response_to_json()

    def response_to_json(self):
        if not self.__response:
            raise ResponseObjectNotSet
        return xmltodict.parse(self.__response.text)

    def get_response(self):
        return self.json_response.get("response", {})

    def get_result(self):
        return self.get_response().get("result", {})

    def get_job_id(self):
        return self.get_result().get("job")

    def get_timezone_string(self):
        return self.get_result()

    def get_logs_from_query_result(self):
        return self.get_result().get("log", {}).get("logs", {})

    def get_query_result_progress(self):
        return int(self.get_logs_from_query_result().get("@progress", 0))

    def get_job_status(self):
        return self.get_result().get("job", {}).get("status")

    def get_log_entities_from_query_result(self, server_time=""):
        data = self.get_logs_from_query_result().get("entry", [])
        if not isinstance(data, list):
            data = [data]
        return [self.build_log_entity(json, server_time) for json in data]

    def get_log_entities_from_json(self, entities_json):
        return [self.build_log_entity(json) for json in entities_json]

    def build_log_entity(self, json, server_time=""):
        return LogEntity(
            raw_data=json,
            log_id=json.get("@logid"),
            seqno=json.get("seqno"),
            receive_time=json.get("receive_time"),
            src=json.get("src"),
            dst=json.get("dst"),
            action=json.get("action"),
            severity=json.get("severity"),
            description=json.get("threatid"),
            misc=json.get("misc"),
            subtype=json.get("subtype"),
            category=json.get("category"),
            filedigest=json.get("filedigest"),
            filetype=json.get("filetype"),
            matchname=json.get("matchname"),
            repeatcnt=json.get("repeatcnt"),
            device_name=json.get("device_name"),
            tag_name=json.get("tag_name"),
            event_id=json.get("event_id"),
            ip=json.get("ip"),
            user=json.get("user"),
            app=json.get("app"),
            admin=json.get("admin"),
            cmd=json.get("cmd"),
            opaque=json.get("opaque"),
            desc=json.get("desc"),
            time_generated=json.get("time_generated"),
            server_time=server_time,
        )
