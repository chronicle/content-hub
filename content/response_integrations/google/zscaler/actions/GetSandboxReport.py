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
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    create_entity_json_result_object,
    flat_dict_to_csv,
)

from ..core.base_action import ZscalerBaseAction
from ..core.constants import GET_SANDBOX_REPORT_SCRIPT_NAME
from ..core.exceptions import ZscalerManagerError


class GetSandboxReportAction(ZscalerBaseAction):
    def __init__(self) -> None:
        super().__init__(GET_SANDBOX_REPORT_SCRIPT_NAME)
        self.output_message: str = ""
        self.result_value: bool = False

    def _perform_action(self, _=None) -> None:
        """Perform the action."""
        json_results = []
        errors = []
        entities = []
        missing_entities = []

        for entity in self.soar_action.target_entities:
            if entity.entity_type == EntityTypes.FILEHASH:
                try:
                    report = self.api_client.get_sandbox_report(entity.identifier)
                    if report:
                        self.result_value = True
                        entities.append(entity.identifier)

                        json_results.append(
                            create_entity_json_result_object(entity.identifier, report)
                        )
                        flat_dict = dict_to_flat(report)
                        self.soar_action.result.add_entity_table(
                            f"{entity.identifier} Sandbox Report",
                            flat_dict_to_csv(flat_dict),
                        )
                    else:
                        missing_entities.append(entity.identifier)
                        self.logger.info(
                            f"{entity.identifier} does not exist on Zscaler or "
                            f"not yet been completed"
                        )

                except ZscalerManagerError as error:
                    errors.append(entity.identifier)
                    self.logger.error(
                        "Failed to get sandbox report",
                        extra={
                            "entity": entity.identifier,
                            "error": str(error),
                        },
                    )
                    self.logger.exception(error)

        if entities:
            self.output_message += (
                "The following Hashes found in Zscaler: \n{0}".format(
                    "\n".join(entities)
                )
            )

        if errors:
            self.output_message += (
                "\nErrors occurred on the following entities: \n{0}\n"
                "Check logs for more details".format("\n".join(errors))
            )

        if missing_entities:
            self.output_message += (
                f"\nThe following hashes does not exist on Zscaler or "
                f"not yet been completed: {','.join(missing_entities)}\n"
            )

        if not entities and not errors and not missing_entities:
            self.output_message = "No entities were found in Zscaler."

        self.soar_action.result.add_result_json(json_results)


def main() -> None:
    GetSandboxReportAction().run()


if __name__ == "__main__":
    main()
