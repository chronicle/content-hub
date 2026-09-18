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
from TIPCommon.utils import platform_supports_1p_api

from ..core.GitSyncManager import GitSyncManager

SCRIPT_NAME = "Pull Custom Family"


def id_validator(resource, fields_to_compare, id_field, current_state):
    resource[id_field] = 0
    if isinstance(fields_to_compare, str):
        fields_to_compare = [fields_to_compare]
    current = next(
        (
            x
            for x in current_state
            if all(x[y] == resource[y] for y in fields_to_compare)
        ),
        None,
    )
    if current:
        resource[id_field] = current[id_field]
    return resource


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME

    family_name = siemplify.extract_job_param("Family Name")

    try:
        gitsync = GitSyncManager.from_siemplify_object(siemplify)

        siemplify.LOGGER.info(f"Pulling {family_name}")
        family = gitsync.content.get_visual_family(family_name)
        if family:
            current_vfs = gitsync.api.get_custom_families(chronicle_soar=siemplify)
            all_records = gitsync.api.get_ontology_records(chronicle_soar=siemplify)
            valid_record_id = all_records[0].get("id") if all_records else None
            validated_family = id_validator(
                family.raw_data, "family", "id", current_vfs
            )

            if platform_supports_1p_api():
                name_to_check = validated_family.get("family")
                existing_vf = next(
                    (vf for vf in current_vfs if vf.get("family") == name_to_check),
                    None,
                )
                if existing_vf:
                    siemplify.LOGGER.info(
                        f'Updating visual family "{name_to_check}"'
                    )
                    gitsync.api.update_visual_family(
                        validated_family, existing_vf, valid_record_id
                    )
                else:
                    siemplify.LOGGER.info(
                        f'Installing visual family "{name_to_check}"'
                    )
                    response_content = gitsync.api.add_custom_family(
                        {"visualFamilyDataModel": validated_family},
                        valid_record_id,
                    )
                    try:
                        if isinstance(response_content, bytes):
                            created_vf = json.loads(response_content.decode("utf-8"))
                        elif isinstance(response_content, str):
                            created_vf = json.loads(response_content)
                        else:
                            created_vf = response_content
                        created_id = created_vf.get("id")
                        if created_id:
                            siemplify.LOGGER.info(
                                "Successfully created visual "
                                f'family "{name_to_check}" with ID {created_id}.'
                                " Now updating image via PATCH."
                            )
                            new_existing_vf = {
                                "id": created_id,
                                "family": name_to_check,
                            }
                            gitsync.api.update_visual_family(
                                validated_family, new_existing_vf, valid_record_id
                            )
                        else:
                            siemplify.LOGGER.warn(
                                f"Created visual family response did not "
                                f"contain ID: {response_content}"
                            )
                    except Exception as e:
                        siemplify.LOGGER.error(
                            "Failed to parse response or "
                            f"update image for new family: {e}"
                        )
            else:
                gitsync.api.add_custom_family(
                    {
                        "visualFamilyDataModel": validated_family,
                    },
                )
            siemplify.LOGGER.info(f"Successfully pulled {family_name}")
        else:
            siemplify.LOGGER.info(f"Family {family_name} not found")

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise

    siemplify.end_script()


if __name__ == "__main__":
    main()
