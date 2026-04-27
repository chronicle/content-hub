from __future__ import annotations
from .ExchangeExtensionPackParser import ExchangeExtensionPackParser
import subprocess
from .constants import (
    COMMANDS,
    RESULT_FILE_NAME,
    POWERSHALL_COMMAND,
    COMMAND_TIMEOUT,
    ON_PREM_CONNECT_COMMAND,
    O365_CONNECT_COMMAND,
    O365_DISCONNECT_COMMAND,
    QUERY_SPECIAL_CHARACTERS,
)
from .UtilsManager import (
    validate_error,
    read_file_content,
    delete_file,
    escape_special_characters,
)


class ExchangeExtensionPackManager:
    def __init__(
        self,
        server_address,
        connection_uri,
        domain,
        username,
        password,
        is_on_prem,
        is_office365,
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param server_address: {str} Mail server address to connect to
        :param connection_uri: {str} Connection Uri to use when working with Office365
        :param domain: {str} The Domain to authenticate with
        :param username: {str} The Username to authenticate with
        :param password: {str} The password to authenticate with
        :param is_on_prem: {bool} Specifies if the target mail server is Exchange On-Prem
        :param is_office365: {bool} Specify if the target mail server is Office365
        :param siemplify_logger: Siemplify logger
        """
        self.server_address = server_address
        self.connection_uri = connection_uri
        self.domain = domain
        self.username = username
        self.password = password
        self.is_on_prem = is_on_prem
        self.is_office365 = is_office365
        self.siemplify_logger = siemplify_logger
        self.parser = ExchangeExtensionPackParser()

    def test_connectivity(self):
        """
        Test connectivity
        """
        if self.is_on_prem:
            command = self.get_full_command("test_connectivity_on_prem")

        if self.is_office365:
            command = self.get_full_command("test_connectivity_o365")

        try:
            p = subprocess.Popen(
                [POWERSHALL_COMMAND, "-NoProfile", "-Command", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            output, error = p.communicate()

            if error:
                raise Exception(error)

        except Exception as e:
            validate_error(e)

    def get_full_command(self, command_name, **kwargs):
        """
        Get full command from command name
        :param command_name: {str} The name of command
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full command
        """
        connect_command = (
            ON_PREM_CONNECT_COMMAND if self.is_on_prem else O365_CONNECT_COMMAND
        )

        main_args = {
            "server_address": self.server_address,
            "connection_uri": self.connection_uri,
            "password": escape_special_characters(self.password),
            "domain": self.domain,
            "username": self.username,
            "file_name": RESULT_FILE_NAME,
        }

        main_args["command"] = COMMANDS.get(command_name).format(
            **{**main_args, **kwargs}
        )

        return connect_command.format(**{**main_args, **kwargs})

    def build_compliance_search_query(
        self, subject_filter, sender_filter, recipient_filter, time_filter, operator
    ):
        """
        Build query string for compliance search
        :param subject_filter: {str} Filter by subject
        :param sender_filter: {str} Filter by sender
        :param recipient_filter: {str} Filter by recipient
        :param time_filter: {str} Filter by time
        :param operator: {str} Operator to use in query
        :return: {str} The query
        """
        filters = {
            "from:": sender_filter,
            "to:": recipient_filter,
            "Subject:": subject_filter,
            "Received>=": time_filter,
        }

        return " {operator} ".join(
            [key + value for key, value in filters.items() if value]
        ).format(operator=operator)

    def create_compliance_search(
        self,
        compliance_search_name,
        subject_filter,
        sender_filter,
        recipient_filter,
        time_filter,
        operator,
        location,
        advanced_query,
    ):
        """
        Create compliance search
        :param compliance_search_name: {str} Name of compliance search
        :param subject_filter: {str} Filter by subject
        :param sender_filter: {str} Filter by sender
        :param recipient_filter: {str} Filter by recipient
        :param time_filter: {str} Filter by time
        :param operator: {str} Operator to use in query
        :param location: {str} Location to search emails in
        :param advanced_query: {str} Query to use in compliance search
        :return: {void}
        """
        query = escape_special_characters(
            (
                advanced_query
                if advanced_query
                else self.build_compliance_search_query(
                    subject_filter=subject_filter,
                    sender_filter=sender_filter,
                    recipient_filter=recipient_filter,
                    time_filter=time_filter,
                    operator=operator,
                )
            ),
            QUERY_SPECIAL_CHARACTERS,
        )

        if self.is_on_prem:
            command = self.get_full_command(
                "create_compliance_search_on_prem",
                compliance_search_name=compliance_search_name,
                location=location,
                query=query,
            )

        if self.is_office365:
            command = self.get_full_command(
                "create_compliance_search_o365",
                compliance_search_name=compliance_search_name,
                location=location,
                query=query,
            )

        try:
            process = subprocess.Popen(
                [POWERSHALL_COMMAND, "-NoProfile", "-Command", command],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            output, error = process.communicate(timeout=COMMAND_TIMEOUT)

            if error:
                raise Exception(error)

        except Exception as e:
            validate_error(e)

    def get_compliance_search_status(self, compliance_search_name):
        """
        Get compliance search status
        :param compliance_search_name: {str} Name of compliance search
        :return: {str} The compliance search status
        """
        if self.is_on_prem:
            command = self.get_full_command(
                "get_compliance_search_status_on_prem",
                compliance_search_name=compliance_search_name,
            )

        if self.is_office365:
            command = self.get_full_command(
                "get_compliance_search_status_o365",
                compliance_search_name=compliance_search_name,
            )

        try:
            p = subprocess.Popen(
                [POWERSHALL_COMMAND, "-NoProfile", "-Command", command],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            output, error = p.communicate(timeout=COMMAND_TIMEOUT)

            if error:
                raise Exception(error)

            result = read_file_content(self.siemplify_logger)
            delete_file(self.siemplify_logger)
            return self.parser.get_compliance_search_status(result)

        except Exception as e:
            validate_error(e)

    def create_compliance_search_preview(self, compliance_search_name):
        """
        Create compliance search preview action
        :param compliance_search_name: {str} Name of compliance search
        :return: {void}
        """
        if self.is_on_prem:
            command = self.get_full_command(
                "create_compliance_search_preview_on_prem",
                compliance_search_name=compliance_search_name,
            )

        if self.is_office365:
            command = self.get_full_command(
                "create_compliance_search_preview_o365",
                compliance_search_name=compliance_search_name,
            )

        try:
            process = subprocess.Popen(
                [POWERSHALL_COMMAND, "-NoProfile", "-Command", command],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            output, error = process.communicate(timeout=COMMAND_TIMEOUT)

            if error:
                raise Exception(error)

        except Exception as e:
            validate_error(e)

    def get_compliance_search_preview_results(self, compliance_search_name, limit):
        """
        Get compliance search preview status and results
        :param compliance_search_name: {str} Name of compliance search
        :param limit: {int} The limit for results
        :return: {tuple} status, results
        """
        if self.is_on_prem:
            command = self.get_full_command(
                "get_compliance_search_preview_on_prem",
                compliance_search_name=compliance_search_name,
            )

        if self.is_office365:
            command = self.get_full_command(
                "get_compliance_search_preview_o365",
                compliance_search_name=compliance_search_name,
            )

        try:
            process = subprocess.Popen(
                [POWERSHALL_COMMAND, "-NoProfile", "-Command", command],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            output, error = process.communicate(timeout=COMMAND_TIMEOUT)

            if error:
                raise Exception(error)

            results = read_file_content(self.siemplify_logger)
            delete_file(self.siemplify_logger)
            return self.parser.get_compliance_search_preview_status_and_results(
                results, compliance_search_name, limit
            )

        except Exception as e:
            validate_error(e)

    def remove_compliance_search(self, compliance_search_name):
        """
        Remove compliance search
        :param compliance_search_name: {str} Name of compliance search
        :return: {void}
        """
        if self.is_on_prem:
            command = self.get_full_command(
                "remove_compliance_search_on_prem",
                compliance_search_name=compliance_search_name,
            )

        if self.is_office365:
            command = self.get_full_command(
                "remove_compliance_search_o365",
                compliance_search_name=compliance_search_name,
            )

        try:
            process = subprocess.Popen(
                [POWERSHALL_COMMAND, "-NoProfile", "-Command", command],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            output, error = process.communicate(timeout=COMMAND_TIMEOUT)

            if error:
                raise Exception(error)

        except Exception as e:
            validate_error(e)

    def create_compliance_search_purge(self, compliance_search_name, state):
        """
        Create compliance search purge action
        :param compliance_search_name: {str} Name of compliance search
        :param state: {str} Specifies state for delete, can be SoftDelete/HardDelete
        :return: {void}
        """
        if self.is_on_prem:
            command = self.get_full_command(
                "create_compliance_search_purge_on_prem",
                compliance_search_name=compliance_search_name,
            )

        if self.is_office365:
            command = self.get_full_command(
                "create_compliance_search_purge_o365",
                compliance_search_name=compliance_search_name,
                state=state,
            )

        try:
            process = subprocess.Popen(
                [POWERSHALL_COMMAND, "-NoProfile", "-Command", command],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            output, error = process.communicate(timeout=COMMAND_TIMEOUT)

            if error:
                raise Exception(error)

        except Exception as e:
            validate_error(e)

    def get_compliance_search_purge_results(self, compliance_search_name):
        """
        Get compliance search purge status
        :param compliance_search_name: {str} Name of compliance search
        :return: {tuple} Compliance search purge status and result
        """
        if self.is_on_prem:
            command = self.get_full_command(
                "get_compliance_search_purge_on_prem",
                compliance_search_name=compliance_search_name,
            )

        if self.is_office365:
            command = self.get_full_command(
                "get_compliance_search_purge_o365",
                compliance_search_name=compliance_search_name,
            )

        try:
            process = subprocess.Popen(
                [POWERSHALL_COMMAND, "-NoProfile", "-Command", command],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            output, error = process.communicate(timeout=COMMAND_TIMEOUT)

            if error:
                raise Exception(error)

            result = read_file_content(self.siemplify_logger)
            delete_file(self.siemplify_logger)
            return self.parser.get_compliance_search_purge_status_and_result(result)

        except Exception as e:
            validate_error(e)

    def get_rules(self):
        """
        Get mail flow rules
        :return: {list} list of Rule objects
        """
        if self.is_on_prem:
            command = self.get_full_command("get_mail_flow_rules_on_prem")

        if self.is_office365:
            command = self.get_full_command("get_mail_flow_rules_o365")

        try:
            process = subprocess.Popen(
                [POWERSHALL_COMMAND, "-NoProfile", "-Command", command],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            output, error = process.communicate(timeout=COMMAND_TIMEOUT)

            if error:
                raise Exception(error)

            result = read_file_content(self.siemplify_logger, default_value=[])
            delete_file(self.siemplify_logger)
            return self.parser.build_rule_objects(result)

        except Exception as e:
            validate_error(e)

    def create_rule(self, rule_name, condition, action, items):
        """
        Create mail flow rule
        :param rule_name: {str} Rule name
        :param condition: {str} Rule condition
        :param action: {str} Rule action
        :param items: {list} Rule items
        :return: {void}
        """
        if self.is_on_prem:
            command = self.get_full_command(
                "create_mail_flow_rule_on_prem",
                rule_name=rule_name,
                condition=condition,
                action=action,
                items=items,
            )

        if self.is_office365:
            command = self.get_full_command(
                "create_mail_flow_rule_o365",
                rule_name=rule_name,
                condition=condition,
                action=action,
                items=items,
            )

        try:
            process = subprocess.Popen(
                [POWERSHALL_COMMAND, "-NoProfile", "-Command", command],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            output, error = process.communicate(timeout=COMMAND_TIMEOUT)

            if error:
                raise Exception(error)

        except Exception as e:
            validate_error(e)

    def update_rule(self, rule_name, condition, items):
        """
        Update mail flow rule
        :param rule_name: {str} Rule name
        :param condition: {str} Rule condition
        :param items: {list} Rule items
        :return: {void}
        """
        if self.is_on_prem:
            command = self.get_full_command(
                "update_mail_flow_rule_on_prem",
                rule_name=rule_name,
                condition=condition,
                items=items,
            )

        if self.is_office365:
            command = self.get_full_command(
                "update_mail_flow_rule_o365",
                rule_name=rule_name,
                condition=condition,
                items=items,
            )

        try:
            process = subprocess.Popen(
                [POWERSHALL_COMMAND, "-NoProfile", "-Command", command],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            output, error = process.communicate(timeout=COMMAND_TIMEOUT)

            if error:
                raise Exception(error)

        except Exception as e:
            validate_error(e)

    def delete_rule(self, rule_name):
        """
        Delete rule by name
        :param rule_name: {str} The rule name
        :return: {void}
        """
        if self.is_on_prem:
            command = self.get_full_command(
                "delete_mail_flow_rule_on_prem", rule_name=rule_name
            )

        if self.is_office365:
            command = self.get_full_command(
                "delete_mail_flow_rule_o365", rule_name=rule_name
            )

        try:
            process = subprocess.Popen(
                [POWERSHALL_COMMAND, "-NoProfile", "-Command", command],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            output, error = process.communicate(timeout=COMMAND_TIMEOUT)

            if error:
                raise Exception(error)

        except Exception as e:
            validate_error(e)

    def get_rules_by_names(self, rule_names):
        """
        Get rules by rule names
        :param rule_names: {list} The list of rule names
        :return: {list} The list of Rule objects
        """
        rules = self.get_rules()
        return [rule for rule in rules if rule.name in rule_names] if rules else []

    def add_items_to_rule(self, rule_name, condition, action, items, rule_items=[]):
        """
        Add provided items to Rule, if rule not found create new rule
        :param rule_name: {str} The rule name
        :param condition: {str} The condition of rule
        :param action: {str} The action of rule
        :param items: {list} The list of items to update rule with
        :param rule_items: {list} The existing rule items
        :return: {void}
        """
        if rule_items:
            items = list(set(map(lambda item: item, rule_items + items)))

        items = ",".join(items)

        if not rule_items:
            self.siemplify_logger.info(
                f'"{rule_name}" rule was not found. New rule will be created'
            )
            self.create_rule(rule_name, condition, action, items)
        else:
            self.update_rule(rule_name, condition, items)

    def remove_items_from_rule(self, rule_name, rule_items, condition, items):
        """
        Remove provided items from rule
        :param rule_name: {str} The rule name
        :param rule_items: {list} The list of rule items
        :param condition: {str} The condition of rule
        :param items: {list} The list of items to remove from rule
        :return: {void}
        """
        filtered_items = [item for item in rule_items if item not in items]

        if not filtered_items:
            self.siemplify_logger.info(
                f"{rule_name} rule doesn't contain any items. It will be deleted."
            )
            self.delete_rule(rule_name)
        elif filtered_items != rule_items:
            self.update_rule(rule_name, condition, ",".join(filtered_items))

    def disconnect(self):
        """
        Disconnect session
        Args:

        Returns:
            () None
        """
        if not self.is_office365:
            return

        try:
            self.siemplify_logger.info("Disconnecting session.")
            process = subprocess.Popen(
                [POWERSHALL_COMMAND, "-NoProfile", "-Command", O365_DISCONNECT_COMMAND],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            output, error = process.communicate(timeout=COMMAND_TIMEOUT)

            if error:
                raise Exception(error)

        except Exception as e:
            validate_error(e)
