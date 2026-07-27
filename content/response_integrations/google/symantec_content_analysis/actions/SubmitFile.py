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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.SymantecContentAnalysisManager import SymantecContentAnalysisManager

INTEGRATION_PROVIDER = "SymantecContentAnalysis"
ACTION_NAME = "SymantecContentAnalysis_Submit File"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    conf = siemplify.get_configuration(INTEGRATION_PROVIDER)
    verify_ssl = conf.get("Verify SSL").lower() == "true"
    symantec_manager = SymantecContentAnalysisManager(
        conf.get("API Root"), conf.get("API Key"), verify_ssl
    )

    file_reputation_score = 0

    # Parameters
    file_path = siemplify.parameters.get("File Path")

    result = symantec_manager.submit_file(file_path)

    if "file_reputation" in result:
        file_reputation_score = result.get("file_reputation", {}).get("score", 0)
    elif "score" in result:
        file_reputation_score = result.get("score", 0)

    if 2 <= file_reputation_score <= 6:
        siemplify.create_case_insight(
            INTEGRATION_PROVIDER,
            "File Found as Suspicious",
            f"{file_path} : is suspicious.",
            None,
            None,
            None,
        )
    if 7 <= file_reputation_score <= 10:
        siemplify.create_case_insight(
            INTEGRATION_PROVIDER,
            "File Found as Malicious",
            f"{file_path} : is Malicious.",
            None,
            None,
            None,
        )

    if file_reputation_score:
        output_message = f'"{file_path}" submitted successfully. \n \n File Reputation Score: {file_reputation_score}'
    else:
        output_message = f'"{file_path}" file submission timeout.'

    siemplify.end(output_message, file_reputation_score)


if __name__ == "__main__":
    main()
