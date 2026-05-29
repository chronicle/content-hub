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
from .AsyncActionStepHandler import AsyncActionStepHandler
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict


class AsyncActionStepHandlerMultiple(AsyncActionStepHandler):
    def __init__(
        self,
        siemplify,
        manager,
        action_steps,
        result_value,
        action_global,
        action_start_time=None,
        output_message_collection=None,
    ):
        super().__init__(
            siemplify,
            manager,
            action_steps,
            result_value,
            action_global,
            action_start_time,
            output_message_collection,
        )
        self.failed_entity_json = {}

    def build_json_result(
        self,
        successful_json_result,
        include_failed_json=True,
        include_timed_out_entities=True,
    ):
        if include_failed_json:
            for index, action_step in self.action_steps.items():
                for item in self.failed_on_step(action_step.step_id):
                    host_or_ip, filename = self.extract_entities_from_item(item, -1)

                    successful_json_result[host_or_ip] = successful_json_result.get(
                        host_or_ip, []
                    )
                    default_fail_json = {
                        "step": action_step.step_label,
                        "reason": self.get_reason(item, action_step.step_id),
                        "is_success": False,
                    }
                    failed_json = self.failed_entity_json.get(item, {})
                    failed_json.update(default_fail_json)
                    successful_json_result[host_or_ip].append(failed_json)

        if include_timed_out_entities and self.timeout_reached:
            successful_json_result = {}
            for item in self.get_all_entities():
                entity, filename = self.extract_entities_from_item(item, -1)
                successful_json_result[entity] = successful_json_result.get(entity, [])

                successful_json_result[entity].append(
                    {
                        "step": self.get_step_data_by().step_label,
                        "reason": "Timeout reached!",
                        "entity": filename,
                        "is_success": False,
                    }
                )
        return convert_dict_to_json_result_dict(successful_json_result)
