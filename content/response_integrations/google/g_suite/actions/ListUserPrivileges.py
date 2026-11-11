from __future__ import annotations
from typing import List

from TIPCommon.extraction import extract_action_param
from TIPCommon.base.action import Action
from TIPCommon.transformation import (
    convert_dict_to_json_result_dict,
    convert_list_to_comma_string,
    dict_to_flat,
    add_prefix_to_dict,
)
from TIPCommon.validation import ParameterValidator

from g_suite.core.action_init import create_api_client
from g_suite.core.consts import LIST_USER_PRIVILEGES_SCRIPT_NAME, CUSTOMER, PREFIX
from g_suite.core.exceptions import GSuiteNotFoundException, GSuiteManagerError
from g_suite.core.GSuiteManager import GSuiteManager
from g_suite.core.datamodels import Role, RoleAssignment
from g_suite.core.utils import prepare_roles, prepare_privileges, prepare_result, extract_privileges
from soar_sdk.SiemplifyDataModel import EntityTypes

SUPPORTED_ENTITY_TYPES = [EntityTypes.USER]


class ListUserPrivileges(Action):
    def __init__(self) -> None:
        super().__init__(LIST_USER_PRIVILEGES_SCRIPT_NAME)
        self.output_message = ""
        self.result_value = True
        self.error_output_message = (
            f'Error executing action "{LIST_USER_PRIVILEGES_SCRIPT_NAME}".'
        )

    def _extract_action_parameters(self) -> None:
        self.params.users_emails = extract_action_param(
            self.soar_action,
            param_name="User Email Addresses",
            is_mandatory=False,
            print_value=True,
        )
        self.params.check_roles = extract_action_param(
            self.soar_action, param_name="Check Roles", print_value=True
        )
        self.params.check_privileges = extract_action_param(
            self.soar_action, param_name="Check Privileges", print_value=True
        )

        self.params.include_inherited_roles = extract_action_param(
            self.soar_action,
            param_name="Include Inherited Roles",
            input_type=bool,
            print_value=True,
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

        self.params.users_emails = validator.validate_csv(
            param_name="User Email Addresses", csv_string=self.params.users_emails
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
        self.logger.info("Extracting user data from entities")
        used_entities = {
            entity.identifier: entity
            for entity in self.soar_action.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        }

        primary_emails = [email.lower() for email in used_entities]
        self.params.users_emails = [email.lower() for email in self.params.users_emails]
        primary_emails.extend(
            email for email in self.params.users_emails if email not in primary_emails
        )

        self.logger.info(
            f"Extraction done found {len(primary_emails)} users to be check in total"
        )

        results = {}

        self.logger.info("Fetching roles")
        roles = {}
        not_found_users = []
        users_with_no_filtered_roles = []
        for email in primary_emails:

            role_assignments = self._get_role_assignments(email)
            if not role_assignments:
                self.logger.info(f"No roles found for user {email}")
                not_found_users.append(email)
                continue

            user_roles = []
            for role_assignment in role_assignments:
                role = self._get_role(role_assignment, roles)
                if role:
                    user_roles.append(role)

            prepared_roles = prepare_roles(self.params.check_roles, user_roles)

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
                users_with_no_filtered_roles.append(email)

        self.logger.info("Fetched all the data")

        self._format_output_messages(
            results=results,
            used_entities=used_entities,
            not_found_users=not_found_users,
            primary_emails=primary_emails,
            users_with_no_filtered_roles=users_with_no_filtered_roles,
        )

    def _get_role_assignments(self, email: str) -> List[RoleAssignment]:
        """
        Gets the role assignments for a user.

        Args:
            email (str): The email of the user.
        Returns:
            List[RoleAssignment] The role assignments for the user.
        """
        try:
            role_assignments: List[RoleAssignment] = (
                self.api_client.list_role_assignments(
                    CUSTOMER, email, self.params.include_inherited_roles
                )
            )
            return role_assignments
        except GSuiteNotFoundException:
            self.logger.error(f"Role Assignment not found for user: {email}")
        except GSuiteManagerError as e:
            self.logger.error(
                f"Unable to get inforamtion about user {email} due to {e}"
            )
        return None

    def _get_role(self, role_assignment: RoleAssignment, roles: List[Role]) -> Role:
        """
        Gets the role by id that is found in the role assignment.

        Args:
            role_assignment (RoleAssignment): Role assignment object.
            roles (List): List of roles that weere previously found.
        Returns:
            Role: Role object.
        """
        if role_assignment.role_id in roles:
            return roles[role_assignment.role_id]

        try:
            role: Role = self.api_client.get_role(CUSTOMER, role_assignment.role_id)
            roles[role_assignment.role_id] = role
            return role
        except GSuiteNotFoundException:
            self.logger.error(f"Role with id {role_assignment.role_id} not found")

        except GSuiteManagerError as e:
            message = (
                "Unable to get inforamtion about role "
                f"{role_assignment.role_id} due to {e}"
            )
            self.logger.error(message)
        return None

    def _format_output_messages(
        self,
        results: dict,
        used_entities: List[str],
        not_found_users: List[str],
        primary_emails: List[str],
        users_with_no_filtered_roles: List[str],
    ) -> None:
        """
        Formats the output messages.

        Args:
            results (Map): List of results created in the action.
            used_entities (Entity): List of entities that were used during action
            execution.
            not_found_users (List): List of users that were not found in the API.
            primary_emails (List): List of users that were provided in the action.
            users_with_no_filtered_roles (List): List of users that were found
            in the API but didn't have any roles/privileges that were provided
            in the action.
        Returns:
            None.
        """
        if results:
            self.output_message += (
                "Successfully enriched the following users "
                "using information from Google Workspace: "
                + ", ".join(user for user in results)
                + "\n"
            )
            modified_entities = [
                used_entities[identifier]
                for identifier in used_entities
                if identifier.lower() in results
            ]

            self._enrich_entities(results, modified_entities)
            self.soar_action.update_entities(modified_entities)

            json_results = convert_dict_to_json_result_dict(results)
            self.soar_action.result.add_result_json(json_results)

        if not primary_emails:
            self.output_message += (
                "None of the provided users were enriched in Google Workspace.\n"
            )
            self.result_value = False
            return
        if len(not_found_users) == len(primary_emails):
            self.output_message += (
                "None of the provided users were enriched in Google Workspace.\n"
            )
            self.result_value = False
        elif not_found_users:
            self.output_message += (
                "Action wasn’t able to enrich the following users "
                "using information from Google Workspace: "
                + ", ".join(user for user in not_found_users)
                + "\n"
            )
        if len(users_with_no_filtered_roles) == len(primary_emails):
            self.output_message += (
                "None of the specific roles/privileges were found "
                "for the provided users in Google Workspace.\n"
            )
        elif users_with_no_filtered_roles:
            self.output_message += (
                "None of the specific roles/privileges were found for "
                "the following users in Google Workspace: "
                + ", ".join(user for user in users_with_no_filtered_roles)
                + "\n"
            )

    def _enrich_entities(self, results, entities):
        """
        Updates the Entities with the result that was obtained from the API.

        Args:
            results (Map): List of results obtained from the api.
            entities (Entity): List of entities that identifiers are present in the
            results map.
        Returns:
            None.
        """
        for entity in entities:
            roles_string = convert_list_to_comma_string(
                results[entity.identifier.lower()]["roles"]
            )
            roles = {"roles": roles_string}
            entity.additional_properties.update(
                add_prefix_to_dict(dict_to_flat(roles), PREFIX)
            )


def main() -> None:
    ListUserPrivileges().run()


if __name__ == "__main__":
    main()
