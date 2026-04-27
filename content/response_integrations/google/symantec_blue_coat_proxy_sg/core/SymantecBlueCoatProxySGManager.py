from __future__ import annotations
import paramiko
from .UtilsManager import split_address, parse_command_output
from .SymantecBlueCoatProxySGParser import SymantecBlueCoatProxySGParser
from .constants import COMMANDS, SHELL_COMMAND_TIMEOUT
from soar_sdk.SiemplifyDataModel import EntityTypes
import time
import socket


ENTITY_TYPE_MAPPING = {
    "hostname": EntityTypes.HOSTNAME,
    "ip": EntityTypes.ADDRESS,
    "url": EntityTypes.URL,
}


class SymantecBlueCoatProxySGManager:
    def __init__(self, ssh_root, username, password, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        :param ssh_root: {str} Blue Coat ProxySG SSH root
        :param username: {str} Blue Coat ProxySG username
        :param password: {str} Blue Coat ProxySG password
        :param siemplify_logger: Siemplify logger
        """
        self.ip, self.port = split_address(ssh_root)
        self.username = username
        self.password = password
        self.siemplify_logger = siemplify_logger
        self.parser = SymantecBlueCoatProxySGParser()
        self.ssh = paramiko.SSHClient()

    def _create_ssh_client(self):
        """
        Create SSH session to remote server
        :return: {SSHClient} SSHClient object
        """
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(
            self.ip, port=self.port, username=self.username, password=self.password
        )

    @staticmethod
    def _get_full_command(command_id, **kwargs):
        """
        Get full command from command identifier.
        :param command_id: {str} the id of command
        :param kwargs: {dict} variables passed for string formatting
        :return: {str} the full command
        """
        return COMMANDS[command_id].format(**kwargs)

    def test_connectivity(self):
        """
        Test connectivity
        :return: {void}
        """
        self._create_ssh_client()
        command = self._get_full_command("help")
        self.ssh.exec_command(command)

    def get_entity_info(self, entity_type, entity_identifier):
        """
        Get entity info
        :param entity_type: {str} entity type
        :param entity_identifier: {str} entity identifier
        :return: {EntityInfo} EntityInfo object
        """
        self._create_ssh_client()
        _stdout = None
        raw_data = ""
        json_data = {}

        if entity_type == ENTITY_TYPE_MAPPING.get("hostname"):
            _stdin, _stdout, _stderr = self.ssh.exec_command(
                self._get_full_command("test_dns", identifier=entity_identifier)
            )

        if entity_type == ENTITY_TYPE_MAPPING.get("ip"):
            _stdin, _stdout, _stderr = self.ssh.exec_command(
                self._get_full_command("test_geolocation", identifier=entity_identifier)
            )

        if entity_type == ENTITY_TYPE_MAPPING.get("url"):
            _stdin, _stdout, _stderr = self.ssh.exec_command(
                self._get_full_command("test_threat_risk", identifier=entity_identifier)
            )
            raw_data += _stdout.read().decode() + "\n"
            json_data.update(parse_command_output(raw_data))
            self._create_ssh_client()
            _stdin, _stdout, _stderr = self.ssh.exec_command(
                self._get_full_command(
                    "test_content_filter", identifier=entity_identifier
                )
            )

        raw_data += _stdout.read().decode()
        json_data.update(parse_command_output(raw_data))
        if "% Error" in json_data:
            append_category_data_as_blank = {"% categories": {}, "category groups": {}}
            json_data.update(append_category_data_as_blank)
        return self.parser.build_entity_info_object(raw_data, json_data, entity_type)

    def execute_interactive_shell_commands(
        self, commands, max_bytes=60000, short_pause=1
    ):
        """
        Execute interactive shell commands
        :param commands: {[str]} list of commands to execute
        :param max_bytes: {int} maximum value in bytes that can be returned
        :param short_pause: {int} amount of seconds to wait after commands run
        :return: {dict} dictionary with commands output
        """
        self._create_ssh_client()

        with self.ssh.invoke_shell() as shell:
            shell.send(f"{self._get_full_command('enable')}\n")
            shell.send(f"{self.password}\n")
            time.sleep(short_pause)
            shell.recv(max_bytes)
            results = {}

            for command in commands:
                shell.send(f"{command}\n")
                shell.settimeout(SHELL_COMMAND_TIMEOUT)
                output = ""

                while True:
                    try:
                        batch_output = shell.recv(max_bytes).decode()
                        output += batch_output
                        time.sleep(short_pause)
                    except socket.timeout:
                        break

                results[command] = output

            return results

    def block_entity(self, entity_identifier):
        """
        Block entity
        :param entity_identifier: {str} entity identifier
        :return: {str} block command output
        """
        results = self.execute_interactive_shell_commands(
            [
                self._get_full_command("conf"),
                self._get_full_command("attack_detection"),
                self._get_full_command("client"),
                self._get_full_command("block", identifier=entity_identifier),
            ]
        )

        return results.get(
            self._get_full_command("block", identifier=entity_identifier)
        )
