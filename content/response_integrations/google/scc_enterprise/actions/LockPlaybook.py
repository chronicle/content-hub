from __future__ import annotations

import json

from TIPCommon.base.action import Action
from TIPCommon.base.action.consts import ExecutionState
from TIPCommon.base.interfaces import ApiClient
from TIPCommon.types import SingleJson, Contains
from scc_enterprise.core import SCCEnterpriseConsts
from scc_enterprise.core import SCCEnterpriseUtils


class LockPlaybook(Action):

    def _init_api_clients(self) -> Contains[ApiClient]:
        pass

    def _set_complete_state(self) -> None:
        self.result_value = True
        self.execution_state = ExecutionState.COMPLETED

    def _set_in_progress_state(self):
        self.result_value = False
        self.execution_state = ExecutionState.IN_PROGRESS

    def _set_lock(self) -> None:
        """Set context value with the lock info."""
        self.soar_action.set_case_context_property(
            property_key=SCCEnterpriseConsts.SCC_SMART_LOCK,
            property_value=json.dumps(
                {
                    "alert_identifier": self.soar_action.current_alert.identifier,
                    "alert_group_identifier": (
                        self.soar_action.current_alert.alert_group_identifier
                    ),
                }
            ),
        )

    def _is_lock_valid(self, smart_lock_value: SingleJson) -> bool:
        """Checks if we still have a running playbook for alert that set the lock."""
        workflow_instances = SCCEnterpriseUtils.get_workflow_instances(
            self.soar_action,
            case_id=self.soar_action.case_id,
            alert_identifier=smart_lock_value["alert_group_identifier"],
        )
        return any(wf_instance.is_running for wf_instance in workflow_instances)

    def _perform_action(self, _=None) -> None:
        self.logger.info("Reading current POSTURE-SMART-LOCK value...")
        smart_lock_value_raw = self.soar_action.get_case_context_property(
            SCCEnterpriseConsts.SCC_SMART_LOCK
        )
        if smart_lock_value_raw is None:
            self._set_lock()
            self.output_message = (
                f"Alert {self.soar_action.current_alert.alert_group_identifier} "
                f"has acquired the Lock"
            )
            self._set_complete_state()
            return

        smart_lock_value = json.loads(smart_lock_value_raw)
        if smart_lock_value["alert_identifier"] == self.soar_action.alert_id:
            self.output_message = (
                f"Alert {smart_lock_value['alert_group_identifier']} "
                f"has already acquired the Lock"
            )
            self._set_complete_state()
            return

        if self._is_lock_valid(smart_lock_value):
            self.output_message = (
                f"Alert's {smart_lock_value['alert_group_identifier']} playbook hasn't "
                f"finished yet. Waiting to acquire the Lock."
            )
            self._set_in_progress_state()
            return

        self._set_lock()
        self.output_message = (
            f"Alert's {smart_lock_value['alert_group_identifier']} playbook has "
            f"finished. Alert {self.soar_action.current_alert.alert_group_identifier} "
            f"has acquired the Lock"
        )
        self._set_complete_state()


def main() -> None:
    LockPlaybook(SCCEnterpriseConsts.LOCK_PLAYBOOK).run()


if __name__ == "__main__":
    main()
