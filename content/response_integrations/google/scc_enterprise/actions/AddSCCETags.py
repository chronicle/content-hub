from __future__ import annotations

import re

from TIPCommon.base.action import Action
from scc_enterprise.core import SCCEnterpriseConsts
from scc_enterprise.core.SCCEnterpriseConsts import TAG_MAPPING


class AddSCCETags(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.result_value = True
        self.output_message = "Successfully set all of the necessary SCCE tags."

    def _init_api_clients(self) -> None:
        pass

    def _perform_action(self, _=None) -> None:
        tags_to_set = {}
        added_tags = []
        for security_event in self.soar_action.current_alert.security_events:
            for key, value in security_event.additional_properties.items():
                self.mapping_for_new_key(key, value, tags_to_set)

        for key, value in tags_to_set.items():
            if value:
                if isinstance(value, list):
                    for tag in value:
                        self.soar_action.add_tag(tag=tag)
                        added_tags.append(tag)
                else:
                    self.soar_action.add_tag(tag=value)
                    added_tags.append(value)
            else:
                self.logger.error(f"Mapping not found for {key}")
        if not added_tags:
            self.output_message = "No SCCE tags were set."
            self.result_value = False

    def mapping_for_new_key(self, key, value, tags_to_set):
        """
        Function that goes through mappings and adds them to the provided dict if
        not added yet.

        Args:
            key: It will be used as a field name that is beeing mapped.
            value: value of the field from the alert.
            tags_to_set: dictionary that the mappings are beeing added to.

        Returns:
            None
        """
        for pattern, transformation in TAG_MAPPING.items():
            if re.match(pattern, key) is not None and key not in tags_to_set:
                tags_to_set[key] = transformation(value)


def main() -> None:
    AddSCCETags(SCCEnterpriseConsts.ADD_SCCE_TAGS).run()


if __name__ == "__main__":
    main()
