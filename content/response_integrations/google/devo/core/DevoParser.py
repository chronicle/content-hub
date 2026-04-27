from __future__ import annotations
from typing import Dict, Optional, List
from .datamodels import QueryResult, QueryObject


class DevoParser:
    """
    Devo Transformation Layer
    """

    @staticmethod
    def build_query_result_model(response: dict) -> QueryResult:
        return QueryResult(
            raw_data=response,
            msg=response.get("msg"),
            error=response.get("error"),
            timestamp=response.get("timestamp", -1),
            cid=response.get("cid"),
            status=response.get("status"),
            objects=DevoParser.build_query_result_objects(response.get("object", [])),
        )

    @staticmethod
    def build_query_result_objects(
        objects_list: Optional[List[Dict]],
    ) -> List[QueryObject]:
        return [
            DevoParser.build_query_result_object(obj_raw_data)
            for obj_raw_data in objects_list
        ]

    @staticmethod
    def build_query_result_object(obj_raw_data: dict) -> QueryObject:
        return QueryObject(
            raw_data=obj_raw_data,
            eventdate=obj_raw_data.get("eventdate"),
            alert_host=obj_raw_data.get("alertHost"),
            domain=obj_raw_data.get("domain"),
            priority=obj_raw_data.get("priority"),
            context=obj_raw_data.get("context"),
            category=obj_raw_data.get("category"),
            status=obj_raw_data.get("status"),
            alert_id=obj_raw_data.get("alertId"),
            src_ip=obj_raw_data.get("srcIp"),
            src_port=obj_raw_data.get("srcPort"),
            src_host=obj_raw_data.get("srcHost"),
            dst_ip=obj_raw_data.get("dstIp"),
            dst_port=obj_raw_data.get("dstPort"),
            dst_host=obj_raw_data.get("dstHost"),
            protocol=obj_raw_data.get("protocol"),
            username=obj_raw_data.get("username"),
            application=obj_raw_data.get("application"),
            engine=obj_raw_data.get("engine"),
            extra_data=obj_raw_data.get("extraData"),
        )
