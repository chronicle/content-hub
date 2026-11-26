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

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import construct_csv

from ..core.base_action import ZscalerBaseAction
from ..core.constants import GET_URL_CATEGORIES_SCRIPT_NAME


class GetUrlCategoriesAction(ZscalerBaseAction):
    def __init__(self) -> None:
        super().__init__(GET_URL_CATEGORIES_SCRIPT_NAME)
        self.output_message: str = ""
        self.result_value: bool = False

    def _extract_action_parameters(self) -> None:
        """Extract action parameters."""
        self.params.display_urls = extract_action_param(
            self.soar_action,
            param_name="Display URL",
            is_mandatory=False,
            print_value=True,
            default_value="False",
        )
        self.params.display_urls = str(self.params.display_urls).lower() == "true"

    def _perform_action(self, _=None) -> None:
        """Perform the action."""
        categories = self.api_client.list_url_categories()

        if categories:
            self.logger.info(f"Found {len(categories)} categories.")
            self.logger.info("Adding categories table.")

            categories_csv = construct_csv(self._construct_categories_table(categories))
            self.soar_action.result.add_data_table("Zscaler Categories", categories_csv)

            if self.params.display_urls:
                for category in categories:
                    category_id = category.get("id")
                    urls_csv = construct_csv(
                        self._construct_category_url_table(category)
                    )

                    if urls_csv:
                        self.logger.info(
                            f"Adding urls table for category {category_id}."
                        )
                        self.soar_action.result.add_data_table(
                            f"{category_id} - URLs", urls_csv
                        )

            self.output_message = "Successfully get Zscaler Categories"
            self.result_value = True
            self.soar_action.result.add_result_json(categories)
        else:
            self.output_message = "No results found"
            self.result_value = False
            self.soar_action.result.add_result_json({})

    def _construct_categories_table(self, results: list[dict]) -> list[dict]:
        """Build the csv table for the categories."""
        csv_output = []
        for result in results:
            csv_output.append(
                {
                    "ID": result.get("id"),
                    "Custom Category": result.get("customCategory"),
                    "URLS Count": len(result.get("urls")) if result.get("urls") else 0,
                }
            )
        return csv_output

    def _construct_category_url_table(self, category_info: dict) -> list[dict]:
        """Build the csv table for the category urls."""
        csv_output = []
        for url in category_info.get("urls", []):
            csv_output.append({"URL": url})
        return csv_output


def main() -> None:
    GetUrlCategoriesAction().run()


if __name__ == "__main__":
    main()
