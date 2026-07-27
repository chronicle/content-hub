# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from soar_sdk.SiemplifyDataModel import EntityTypes

from .IronportDatamodels import Message, DynamicReport
from .IronportConstants import ENTITY_TYPES_MAPPING


class IronportParser:
    @staticmethod
    def build_message(message_data):
        return Message(
            raw_data=message_data,
            subject=message_data.get("attributes", {}).get("subject"),
            sender=message_data.get("attributes", {}).get("sender"),
            recipients=message_data.get("attributes", {}).get("recipient"),
        )

    @staticmethod
    def build_dynamic_report(report_data, counter_names, report_type):
        if "keys" not in report_data:
            for report in report_data.get("counter_values", []):
                attributes = IronportParser.convert_names_and_values_to_dict(
                    names=counter_names, values=report.get("counter_values", [])
                )

                attributes[
                    ENTITY_TYPES_MAPPING.get(EntityTypes.ADDRESS, {}).get("field")
                ] = report.get("ip_domain")
                attributes[
                    ENTITY_TYPES_MAPPING.get(EntityTypes.HOSTNAME, {}).get("field")
                ] = report.get("key")

                yield DynamicReport(
                    raw_data=report_data,
                    begin_time=report_data.get("begin_time"),
                    end_time=report_data.get("end_time"),
                    begin_timestamp=report_data.get("begin_timestamp"),
                    end_timestamp=report_data.get("end_timestamp"),
                    report_type=report_type,
                    **attributes
                )
        else:
            for key, counter_values in zip(
                report_data.get("keys"), report_data.get("counter_values")
            ):
                attributes = IronportParser.convert_names_and_values_to_dict(
                    names=counter_names, values=counter_values
                )

                attributes[
                    (
                        ENTITY_TYPES_MAPPING.get(EntityTypes.USER, {}).get("field")
                        if report_type
                        in ENTITY_TYPES_MAPPING.get(EntityTypes.USER, {}).get(
                            "report_types"
                        )
                        else "key"
                    )
                ] = key

                yield DynamicReport(
                    raw_data=report_data,
                    begin_time=report_data.get("begin_time"),
                    end_time=report_data.get("end_time"),
                    begin_timestamp=report_data.get("begin_timestamp"),
                    end_timestamp=report_data.get("end_timestamp"),
                    report_type=report_type,
                    **attributes
                )

    @staticmethod
    def convert_names_and_values_to_dict(names, values):
        return dict(zip(names, values))
