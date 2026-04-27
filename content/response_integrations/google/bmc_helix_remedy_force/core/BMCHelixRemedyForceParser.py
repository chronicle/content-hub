from __future__ import annotations
from .datamodels import *

from .constants import CONTAINS_FILTER, EQUAL_FILTER


class BMCHelixRemedyForceParser:

    @staticmethod
    def build_siemplify_record_object(raw_data, fields_to_return):

        if fields_to_return:
            raw_data_temp = {}
            for key, value in list(raw_data.items()):
                if key in fields_to_return:
                    raw_data_temp[key] = value
            raw_data = raw_data_temp

        return Record(raw_data=raw_data)

    @staticmethod
    def build_siemplify_query_object(raw_data):

        return Query(
            raw_data=raw_data,
            records=raw_data.get("records"),
            total_size=raw_data.get("totalSize"),
        )

    @staticmethod
    def build_siemplify_record_types_object(
        raw_data, filter_logic, filter_value, limit
    ):

        record_type_objects = []
        for record_type in raw_data.get("sobjects"):
            if filter_logic == EQUAL_FILTER and filter_value is not None:
                if record_type.get("name") == filter_value:
                    record_type_objects.append(
                        Record_Types(
                            raw_data=record_type,
                            name=record_type.get("name"),
                            label=record_type.get("label"),
                            custom=record_type.get("custom"),
                        )
                    )

            elif filter_logic == CONTAINS_FILTER and filter_value is not None:
                if filter_value in record_type.get("name"):
                    record_type_objects.append(
                        Record_Types(
                            raw_data=record_type,
                            name=record_type.get("name"),
                            label=record_type.get("label"),
                            custom=record_type.get("custom"),
                        )
                    )
            else:
                record_type_objects.append(
                    Record_Types(
                        raw_data=record_type,
                        name=record_type.get("name"),
                        label=record_type.get("label"),
                        custom=record_type.get("custom"),
                    )
                )

        if limit:
            record_type_objects = record_type_objects[:limit]

        return record_type_objects

    def build_incident_objects(self, raw_data):
        return [
            self.build_siemplify_incident_object(item)
            for item in raw_data.get("records", [])
        ]

    @staticmethod
    def build_siemplify_incident_object(raw_data):
        return Incident(
            raw_data=raw_data,
            id=raw_data.get("Id"),
            title=raw_data.get("BMCServiceDesk__Service_Request_Title__c")
            or raw_data.get("BMCServiceDesk__Category_ID__c"),
            description=raw_data.get("BMCServiceDesk__shortDescription__c"),
            priority=raw_data.get("BMCServiceDesk__Priority_ID__c"),
            queue_name=raw_data.get("BMCServiceDesk__queueName__c"),
            created_date=raw_data.get("CreatedDate"),
        )
