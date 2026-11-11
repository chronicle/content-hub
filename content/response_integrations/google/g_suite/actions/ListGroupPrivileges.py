from __future__ import annotations
from typing import List

from TIPCommon.extraction import extract_action_param
from TIPCommon.base.action import Action
from TIPCommon.transformation import convert_dict_to_json_result_dict
from TIPCommon.validation import ParameterValidator

from g_suite.core.action_init import create_api_client
from g_suite.core.consts import LIST_GROUP_PRIVILEGES_SCRIPT_NAME, CUSTOMER
from g_suite.core.exceptions import GSuiteNotFoundException, GSuiteManagerError
from g_suite.core.GSuiteManager import GSuiteManager
from g_suite.core.datamodels import Role, RoleAssignment, Group
from g_suite.core.utils import prepare_roles, prepare_privileges, prepare_result, extract_privileges


class ListGroupPrivileges(Action):
    def __init__(self) -> None:
        super().__init__(LIST_GROUP_PRIVILEGES_SCRIPT_NAME)
        self.output_message = ""
        self.result_value = True
        self.error_output_message = (
            f'Error executing action "{LIST_GROUP_PRIVILEGES_SCRIPT_NAME}".'
        )

    def _extract_action_parameters(self) -> None:
        self.params.group_emails = extract_action_param(
            self.soar_action,
            param_name="Group Email Addresses",
            is_mandatory=True,
            print_value=True,
        )
        self.params.check_roles = extract_action_param(
            self.soar_action, param_name="Check Roles", print_value=True
        )
        self.params.check_privileges = extract_action_param(
            self.soar_action, param_name="Check Privileges", print_value=True
        )

        self.params.expand_privileges = extract_action_param(
            self.soar_action,
            param_name="Expand Privileges",
            input_type=bool,
            print_value=True,
        )
        self.params.max_roles_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Roles To Return",
            input_type=int,
            is_mandatory=True,
            print_value=True,
        )

        self.params.max_privileges_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Privileges To Return",
            input_type=int,
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:

        validator = ParameterValidator(self.soar_action)
        self.params.max_roles_to_return = validator.validate_positive(
            param_name="Max Roles To Return", value=self.params.max_roles_to_return
        )

        self.params.max_privileges_to_return = validator.validate_positive(
            param_name="Max Privileges To Return",
            value=self.params.max_privileges_to_return,
        )

        self.params.group_emails = validator.validate_csv(
            param_name="Group Email Addresses", csv_string=self.params.group_emails
        )

        self.params.check_roles = validator.validate_csv(
            param_name="Check Roles", csv_string=self.params.check_roles
        )

        self.params.check_privileges = validator.validate_csv(
            param_name="Check Privileges", csv_string=self.params.check_privileges
        )

        if self.params.check_privileges and not self.params.expand_privileges:
            raise GSuiteManagerError(
                '"Expand Privileges" parameter should be enabled, '
                'if you have set any value in "Check Privileges" parameter.'
            )

    def _init_api_clients(self) -> GSuiteManager:
        return create_api_client(self.soar_action)

    def _perform_action(self, _: None) -> None:

        self.logger.info(
            f"Extraction done found {len(self.params.group_emails)}"
            " groups to be check in total"
        )

        results = {}

        self.logger.info("Fetching roles")
        roles = {}
        not_found_groups = []
        groups_with_no_filtered_roles = []
        for email in self.params.group_emails:
            try:
                group_details: Group = self.api_client.get_group(email)
            except (GSuiteNotFoundException, GSuiteManagerError) as e:
                not_found_groups.append(email)
                self.logger.error(f"Unable to get group detalis for {email} due to {e}")
                continue

            role_assignments = self._get_role_assignment(group_details, email)

            group_roles = []
            for role_assignment in role_assignments:
                if role_assignment.role_id in roles:
                    group_roles.append(roles[role_assignment.role_id])
                else:
                    try:
                        role: Role = self.api_client.get_role(
                            CUSTOMER, role_assignment.role_id
                        )
                        group_roles.append(role)
                        roles[role_assignment.role_id] = role
                    except GSuiteNotFoundException:
                        self.logger.error(
                            f"Role with id {role_assignment.role_id} not found"
                        )
                        continue
                    except GSuiteManagerError as e:
                        message = (
                            "Unable to get inforamtion about role "
                            f"{role_assignment.role_id} due to {e}"
                        )
                        self.logger.error(message)

            prepared_roles = prepare_roles(self.params.check_roles, group_roles)

            privileges = extract_privileges(prepared_roles)

            prepared_privileges = prepare_privileges(
                self.params.check_privileges, privileges
            )

            result = prepare_result(
                prepared_roles,
                prepared_privileges,
                self.params.max_roles_to_return,
                self.params.max_privileges_to_return,
                self.params.expand_privileges,
            )
            if result:
                results[email] = result
            else:
                groups_with_no_filtered_roles.append(email)

        self.logger.info("Fetched all the data")

        self._format_output_message(
            results=results,
            not_found_groups=not_found_groups,
            groups_with_no_filtered_roles=groups_with_no_filtered_roles,
        )

    def _get_role_assignment(
        self, group_details: Group, email: str
    ) -> List[RoleAssignment]:
        """Get role assignments for a group.

        Args:
            group_details (Group): Group details.
            email (str): Group email.

        Returns:
            List of role assignments.
        """
        try:
            role_assignments: List[RoleAssignment] = (
                self.api_client.list_role_assignments(CUSTOMER, group_details.id)
            )
            return role_assignments
        except GSuiteNotFoundException:
            self.logger.error(f"Role Assignment not found for group: {email}")
        except GSuiteManagerError as e:
            self.logger.error(
                f"Unable to get inforamtion about group {email} due to {e}"
            )
        return None

    def _format_output_message(
        self,
        results: dict,
        not_found_groups: List[str],
        groups_with_no_filtered_roles: List[str],
    ) -> None:
        """Format the output message.

        Args:
            results (dict): The results of the action.
            not_found_groups (list): The groups that were not found.
            groups_with_no_filtered_roles (list): The groups that were found but did not
            have any filtered roles.

        Returns:
            None
        """
        if results:
            self.output_message += (
                "Successfully fetched information for the following groups "
                "using information from Google Workspace: "
                + ", ".join(user for user in results)
                + "\n"
            )
            json_results = convert_dict_to_json_result_dict(results)
            self.soar_action.result.add_result_json(json_results)
        if len(not_found_groups) == len(self.params.group_emails):
            self.output_message += (
                "No information was found for the provided groups "
                "in Google Workspace.\n"
            )
            self.result_value = False
        elif not_found_groups:
            self.output_message += (
                "Action wasn’t able to fetch information for the following groups"
                " using information from Google Workspace:"
                + ", ".join(user for user in not_found_groups)
                + "\n"
            )
        if len(groups_with_no_filtered_roles) == len(self.params.group_emails):
            self.output_message += (
                "None of the specific roles/privileges were found "
                "for the provided groups in Google Workspace.\n"
            )
        elif groups_with_no_filtered_roles:
            self.output_message += (
                "None of the specific roles/privileges were found for "
                "the following groups in Google Workspace: "
                + ", ".join(user for user in groups_with_no_filtered_roles)
                + "\n"
            )


def main() -> None:
    ListGroupPrivileges().run()


if __name__ == "__main__":
    main()
