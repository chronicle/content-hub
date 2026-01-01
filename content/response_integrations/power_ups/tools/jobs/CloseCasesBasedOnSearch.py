# Copyright 2025 Google LLC
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

import json

from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.rest.soar_api import execute_bulk_close_case, search_cases_by_everything

SCRIPT_NAME = "CloseCasesBasedOnSearch"


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        payload = json.loads(siemplify.parameters.get("Search Payload"))
        payload["isCaseClosed"] = False
        results = search_cases_by_everything(siemplify, payload).get("results")
        case_ids = [item.get("id") for item in results]

        if case_ids:
            siemplify.LOGGER.info(f"The following cases will be affected: {case_ids}")

            execute_bulk_close_case(
                chronicle_soar=siemplify,
                case_ids=case_ids,
                close_reason=int(siemplify.parameters.get("Close Reason")),
                root_cause=siemplify.parameters.get("Root Cause"),
                close_comment=siemplify.parameters.get("Close Comment"),
            )
            siemplify.LOGGER.info(f"Successfully closed {len(case_ids)} cases")

        else:
            siemplify.LOGGER.info("No cases found with the search payload")

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end_script()


if __name__ == "__main__":
    main()
