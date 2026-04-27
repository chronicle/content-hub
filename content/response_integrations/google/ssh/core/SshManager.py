# ==============================================================================
# title           :SshManager.py
# description     :This Module contain all SSH remote operations functionality
# author          :danield@siemplify.co
# date            :1-2-18
# python_version  :2.7
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import paramiko
import base64
from paramiko import client, Transport

# =====================================
#             CONSTANTS               #
# =====================================
CON_LIST_RUNNING_PROCESS = "ps -aux"  # List all running processes
CON_LOGOFF_USER = "pkill -KILL -u '{0}'"  # Logoff user
CON_KILL_PROCESS = "kill -9 {0}"  # Kill process by PID
CON_PKILL_PROCESS = "pkill {0}"  # Kill processes by name
CON_KILLALL_PROCESS = "killall -9 {0}"  # Kill all processes by name
CON_SHUTDOWN_COMMAND = (
    "shutdown -h {0}"  # Shutdown machine with option to specify timeframe
)
CON_REBOOT_COMMAND = "reboot"  # Shutdown machine with option to specify timeframe
CON_LIST_IPTABLES_RULE = "iptables -S {0}"  # Lists all IPtables rules and gives the option to specifiy chain (INPUT, OUTPUT, TCP, etc)
CON_LIST_IPTABLES_RULE_TABLE = "iptables -L {0} {1}"  # Lists all IPtables rules as table and gives the option to specifiy chain (INPUT, OUTPUT, TCP, etc) and show number of packets for rule
CON_DELETE_IPTABLES_RULE = "iptables -D {0}"  # Delete IPtables rules
CON_ADD_IPTABLES_RULE = "iptables -A {0}"  # Add IPtables rules
CON_CHECK_IPTABLES_RULE = "iptables -C {0}"  # Checks IPtables rules
CON_BLOCK_IPADDRESS_RULE = (
    "iptables -I INPUT -s {0} -j DROP"  # Blocks IP Address via IPtables
)
CON_ALLOW_IPADDRESS_RULE = (
    "iptables -A INPUT -s {0} -j ACCEPT"  # Allows IP Address via IPtables
)
CON_CHECK_ALLOW_IPADDRESS_RULE = (
    "iptables -C INPUT -s {0} -j ACCEPT"  # Checks IPtables rules for allowed IP Address
)
CON_CHECK_BLOCK_IPADDRESS_RULE = (
    "iptables -C INPUT -s {0} -j DROP"  # Checks IPtables rules for blocked IP Address
)
CON_SAVE_IPTABLES = "service iptables save"  # Saves IPtables
CON_LIST_CONNECTIONS = "netstat -tnpa"


# =====================================
#              CLASSES                #
# =====================================
class SshManagerError(Exception):
    """
    General Exception for SSH manager
    """

    pass


class SshManager:
    """
    Responsible for all SSH operations functionality
    """

    def __init__(self, server, username, password, port=22):
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.client = client.SSHClient()

    def _create_ssh_client(self):
        """
        Create SSH session to remote server
        :return: {object} paramiko SSHClient
        """
        # The following line is required if you want the script to be able to access a server that's not yet in the known_hosts file
        self.client.set_missing_host_key_policy(client.AutoAddPolicy())
        self.client.connect(
            self.server,
            port=self.port,
            username=self.username,
            password=self.password,
            timeout=4,
        )

    def _create_sftp_client(self):
        """
        Create SFTP ssesion to remote server
        :return: {object} sftp client object (paramiko data model)
        """
        sftp_connect = Transport(self.server, self.port)
        sftp_connect.connect(username=self.username, password=self.password)
        sftp_client = paramiko.SFTPClient.from_transport(sftp_connect)
        return sftp_client

    def _run_command(self, command):
        """
        Run command on remote host
        :param command: {string} The command to run
        :return: {boolean}
        """
        if self.client.get_transport() and not self.client.get_transport().is_active():
            self._create_ssh_client()
        (stdin, stdout, stderr) = self.client.exec_command(command)
        status_code = stdout.channel.recv_exit_status()
        return status_code, stdout, stderr

    def test_conectivity(self):
        """
        Validates connectivity
        :return: {boolean} True/False
        """
        self._create_ssh_client()
        return True

    def list_file(self, remote_folder_path):
        """
        lists files on remote host
        :param remote_folder_path: {string} the folder path in the remote host
        :return: {string} list of files in directory
        """
        file_list = []
        sftp_client = self._create_sftp_client()
        remote_files = sftp_client.listdir(remote_folder_path)
        for file in remote_files:
            file_list.append(file)
        sftp_client.close()
        return file_list

    def get_file(self, file_path):
        """
        Get file from remote host
        :param remote_path: {string} the file path in the remote host
        :return: {string} file content (in base64)
        """
        sftp_client = self._create_sftp_client()
        remote_file = sftp_client.open(file_path, mode="rb")
        base64_file = base64.encodebytes(remote_file.read())
        sftp_client.close()
        return base64_file

    def list_process(self):
        """
        List all running processes in remote host
        :return: {list of strings}
        """
        self._create_ssh_client()
        status_code, output, error = self._run_command(CON_LIST_RUNNING_PROCESS)
        process_result = output.readlines()
        self.client.close()
        # Creates a list result values inside a list after the header
        header = " ".join(process_result[0].strip().split()).split()
        process_data = [
            process.strip().split(None, len(header) - 1)
            for process in process_result[1:]
        ]
        # connection_data = map(lambda s: s.strip().split(None), netstat_result[1:])
        data_table = []
        for lines in process_data:
            data_table.append(",".join(lines))
        data_table = [",".join(header)] + data_table
        return status_code, data_table, error

    def logoff_user(self, username):
        """
        Logoff user in remote host
        :param username: {string} the username to logff
        :return: {boolean}
        """
        self._create_ssh_client()
        logoff_command = CON_LOGOFF_USER.format(username)
        status_code, output, error = self._run_command(logoff_command)
        self.client.close()
        return status_code

    def terminate_process(self, process):
        """
        Terminate process in remote host
        :param process: {string} The process name or ID to terminate
        :return: {boolean}
        """
        self._create_ssh_client()
        if process.isdigit():
            kill_command = CON_KILL_PROCESS.format(process)
        else:
            kill_command = CON_PKILL_PROCESS.format(process)
        status_code, output, error = self._run_command(kill_command)
        self.client.close()
        return status_code

    def shutdown(self, wait_time="now"):
        """
        Shutdown remote host
        :param wait_time: {string} Time to wait before shutdown in minutes
        :return: {boolean}
        """
        self._create_ssh_client()
        shutdown_command = CON_SHUTDOWN_COMMAND.format(wait_time)
        status_code, output, error = self._run_command(shutdown_command)
        print(status_code)
        self.client.close()
        return status_code

    def reboot(self):
        """
        Reboot remote host
        :param wait_time: {string} Time to wait before reboot in minutes
        :return: {boolean}
        """
        self._create_ssh_client()
        reboot_command = CON_REBOOT_COMMAND
        status_code, output, error = self._run_command(reboot_command)
        print(status_code)
        self.client.close()
        return status_code

    def list_iptables_rules(self, chain=""):
        """
        List all iptables rules in remote host
        :chain: {string} the iptables chain that you wish to see (example: INPUT, OUTPUT, etc.)
        :return: {list of strings}
        """
        self._create_ssh_client()
        list_rules = CON_LIST_IPTABLES_RULE.format(chain)
        status_code, output, error = self._run_command(list_rules)
        # Using readlines in order to create a list of the the command that was ran
        iptables_results = output.readlines()
        # List of header columns
        header = ["-", "Chain", "Rule"]
        # Creates a list result values inside a list after the header
        iptables_data = [
            s.strip().split(None, len(header) - 1) for s in iptables_results
        ]
        data_table = []
        for lines in iptables_data:
            data_table.append(",".join(lines))
        data_table = [",".join(header)] + data_table
        self.client.close()
        return status_code, data_table, error

    def list_iptables_rules_table(self, chain="", show_number_packets=""):
        # CR: it's not the same as above? use only one func for it
        """
        List all iptables rules in remote host in a table
        :chain: {string} the iptables chain that you wish to see (example: INPUT, OUTPUT, etc.)
        :show_number_packets: {string} Displays the number of packets that have matched each rule
        :return: {list of strings}
        """
        self._create_ssh_client()
        list_rules = CON_LIST_IPTABLES_RULE_TABLE.format(chain, show_number_packets)
        status_code, output, error = self._run_command(list_rules)
        for line in output:
            print(line.strip("\n"))
        self.client.close()
        return True

    def delete_iptables_rule(self, rule):
        """
        Delete iptable rule in remote host
        :param rule: {string} The iptables rule to delete (Example: INPUT -s 192.168.1.1 -j DROP)
        :return: {boolean}
        """
        delete_rule = CON_DELETE_IPTABLES_RULE.format(rule)
        self._create_ssh_client()
        run_status_code, *_ = self._run_command(delete_rule)
        self.client.close()
        if run_status_code == 0:
            return (
                f"Successfully deleted {rule} iptables rule on remote machine",
                run_status_code,
            )
        return (
            f"Failed to delete {rule} iptables rule on remote machine",
            run_status_code,
        )

    def add_iptables_rule(self, rule):
        """
        Add rule to iptables in remote host
        :param rule: {string} The iptables rule to add (Example: INPUT -s 192.168.1.1 -j DROP)
        :return: {boolean}
        """
        add_rule = CON_ADD_IPTABLES_RULE.format(rule)
        check_rule = CON_CHECK_IPTABLES_RULE.format(add_rule)
        self._create_ssh_client()
        check_status_code, check_output, check_error = self._run_command(check_rule)
        # In order to prevent from having a rule added more then once I check if the rule is there.
        if check_status_code != 0:
            run_status_code, run_output, run_error = self._run_command(add_rule)
            self.client.close()
            if run_status_code == 0:
                return f"Successfully added rules {rule} via iptables", run_status_code
            else:
                return f"Failed to add rule {rule} via iptables", run_status_code
        self.client.close()
        return "The specified rule already exists on the remote machine"

    def block_ip_in_iptables(self, ip_address):
        # CR: Document the desire rule format (put an example for root)
        """
        Block ip address in remote host iptables
        :param ip_address: {string} The IP address to block in iptables
        :return: {boolean}
        """
        self._create_ssh_client()
        add_rule = CON_BLOCK_IPADDRESS_RULE.format(ip_address)
        check_rule = CON_CHECK_BLOCK_IPADDRESS_RULE.format(ip_address)
        # In order to prevent from having a rule added more then once I check if the rule is there.
        check_status_code, check_output, check_error = self._run_command(check_rule)
        if check_status_code != 0:
            run_status_code, run_output, run_error = self._run_command(add_rule)
            self.client.close()
            if run_status_code == 0:
                return (
                    f"Successfully added rule to block '{ip_address}' via iptables",
                    run_status_code,
                )
            else:
                return (
                    f"Failed to add rule to block '{ip_address}' on remote machine",
                    run_status_code,
                )
        self.client.close()
        return (
            f"Already blocking '{ip_address}' on the remote machine",
            check_status_code,
        )

    def allow_ip_in_iptables(self, ip_address):
        """
        Allow ip address in remote host iptables
        :param ip_address: {string} The ip address to allow in iptables
        :return: {boolean}
        """
        self._create_ssh_client()
        add_rule = CON_ALLOW_IPADDRESS_RULE.format(ip_address)
        check_rule = CON_CHECK_ALLOW_IPADDRESS_RULE.format(ip_address)
        # In order to prevent from having a rule added more then once I check if the rule is there.
        check_status_code, check_output, check_error = self._run_command(check_rule)
        if check_status_code != 0:
            run_status_code, run_output, run_error = self._run_command(add_rule)
            self.client.close()
            if run_status_code == 0:
                return (
                    f"Successfully added rule to block '{ip_address}' via iptables",
                    run_status_code,
                )
            else:
                return (
                    f"Failed to add rule to block '{ip_address}' on remote machine",
                    run_status_code,
                )
        self.client.close()
        return (
            f"Already blocking '{ip_address}' on the remote machine",
            check_status_code,
        )

    def list_connections(self):
        """
        List connections in remote host
        :return: {list of strings}
        """
        self._create_ssh_client()
        status_code, output, error = self._run_command(CON_LIST_CONNECTIONS)
        # Using readlines in order to create a list of the the command that was ran
        netstat_result = output.readlines()[1:]
        # List of header columns
        header = " ".join(netstat_result[0].strip().split()).split()
        # Creates a list result values inside a list after the header
        connection_data = [
            s.strip().split(None, len(header) - 1) for s in netstat_result[1:]
        ]
        data_table = []
        for lines in connection_data:
            data_table.append(",".join(lines))
        data_table = [",".join(header)] + data_table
        self.client.close()
        return status_code, data_table, error

    def upload_file(self, file_blob, destination_file_path):
        """
        Upload file to remote host
        :param file_blob: {string} The file blob data in base64! to create in the remote host
        :param destination_file_path: {string}
        :return: {boolean}
        """
        sftp_client = self._create_sftp_client()
        file = base64.b64decode(file_blob)
        remote_file = sftp_client.file(destination_file_path, "w+")
        remote_file.write(file)
        sftp_client.close()
        return True

    def execute_program(self, file_path):
        """
        Excute program in remote host
        :param file_path: {string} The path to the program in the remote host
        :return: {string} program output
        """
        self._create_ssh_client()
        status_code, output, error = self._run_command(file_path)
        self.client.close()
        return status_code, output, error

    def run_command(self, command):
        """
        Execute command in remote host
        :param command: {string} The command to run
        :return: {string} command output
        """
        self._create_ssh_client()
        status_code, output, error = self._run_command(command)
        self.client.close()
        return status_code, output, error
