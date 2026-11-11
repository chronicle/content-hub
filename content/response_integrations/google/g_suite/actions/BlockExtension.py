from __future__ import annotations

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param
from g_suite.core import consts
from g_suite.core.GSuiteManager import GSuiteManager
from g_suite.core.action_init import create_api_client
from g_suite.core.datamodels import OrgUnit, ResolvedPolicy
from g_suite.core.exceptions import (
    GSuiteManagerError,
    GSuiteNotFoundException,
    GSuiteValidationException,
)


class BlockExtensionAction(Action):

    def __init__(self) -> None:
        super().__init__(consts.BLOCK_EXTENSION_SCRIPT_NAME)
        self.manager: GSuiteManager | None = None
        self.output_message: str = ""
        self.result_value: bool = False

    def _init_api_clients(self) -> None:
        self.manager: GSuiteManager = create_api_client(self.soar_action)

    def _extract_action_parameters(self) -> None:
        self.params.org_unit_name = extract_action_param(
            self.soar_action,
            param_name="Organization Unit Name",
            is_mandatory=True,
        )
        self.params.extension_id = extract_action_param(
            self.soar_action,
            param_name="Extension ID",
            is_mandatory=True,
        )

    def _validate_params(self) -> None:
        if not consts.EXTENSION_ID_REGEX.match(self.params.extension_id):
            raise GSuiteValidationException(
                f"'{self.params.extension_id}' is not a valid extension ID. "
                "A valid ID is a 32-character string using letters 'a' through 'p'."
            )

    def _perform_action(self, _: None = None) -> None:
        org_unit_id: str
        target_ou_name: str
        org_unit_id, target_ou_name = self._get_org_unit_id()

        self.logger.info(
            f"Attempting to block extension '{self.params.extension_id}' "
            f"in OU '{target_ou_name}' (ID: {org_unit_id})."
        )

        self.manager.block_extension(
            extension_id=self.params.extension_id,
            org_unit_id=org_unit_id,
        )

        self.logger.info("Successfully sent request to block extension.")

        self._validate_policy_blocked(org_unit_id, target_ou_name)

    def _get_org_unit_id(self) -> tuple[str, str]:
        self.logger.info("Fetching organizational units.")
        all_ous: list[OrgUnit] = self.manager.list_ou(customer_id=consts.CUSTOMER)

        return self._find_ou_by_name(all_ous, self.params.org_unit_name)

    def _find_ou_by_name(
        self,
        all_ous: list[OrgUnit],
        name: str,
    ) -> tuple[str, str]:
        ou: OrgUnit
        for ou in all_ous:
            if ou.name == name:
                self.logger.info(
                    f"Found OU '{ou.name}' with ID '{ou.org_unit_id}'."
                )
                clean_ou_id: str = ou.org_unit_id.split(":")[-1]
                return clean_ou_id, ou.name

        raise GSuiteNotFoundException(f"Organizational Unit '{name}' not found.")

    def _validate_policy_blocked(
        self,
        org_unit_id: str,
        target_ou_name: str,
    ) -> None:
        self.logger.info("Validating the policy has been applied.")
        resolved_policies: list[ResolvedPolicy] = self._get_resolved_policies(
            org_unit_id
        )
        self._verify_policy_and_set_result(resolved_policies, target_ou_name)

    def _get_resolved_policies(
        self,
        org_unit_id: str,
    ) -> list[ResolvedPolicy]:
        resolved_policies: list[ResolvedPolicy] = self.manager.resolve_policy(
            extension_id=self.params.extension_id, org_unit_id=org_unit_id
        )

        if not resolved_policies:
            raise GSuiteManagerError(
                "Failed to validate the policy change for extension "
                f"'{self.params.extension_id}'. No policy was resolved."
            )

        return resolved_policies

    def _verify_policy_and_set_result(
        self,
        resolved_policies: list[ResolvedPolicy],
        target_ou_name: str,
    ) -> None:
        self.soar_action.result.add_result_json(
            [p.to_json() for p in resolved_policies]
        )

        install_type: str | None = resolved_policies[0].install_type

        if install_type == consts.BLOCKED_INSTALL_TYPE:
            self.output_message = (
                f"Successfully blocked extension “{self.params.extension_id}” in "
                f"Organization Unit {target_ou_name} using Google Workspace."
            )
            self.result_value = True
        else:
            raise GSuiteManagerError(
                f"Failed to validate the policy change for extension "
                f"'{self.params.extension_id}'. The extension install type is "
                f"'{install_type}', not '{consts.BLOCKED_INSTALL_TYPE}'."
            )


def main() -> None:
    action = BlockExtensionAction()
    action.run()


if __name__ == "__main__":
    main()
