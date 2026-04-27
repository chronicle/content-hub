# ============================================================================#
# title           :RunnersManager.py
# description     :This Module contain all Runners operations functionality
# author          :avital@siemplify.co
# date            :24-06-2018
# python_version  :2.7
# libreries       :requests
# requirments     :
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #
from __future__ import annotations
import subprocess

# ============================== CONSTS ===================================== #
PIPE_NAME = r"\\.\pipe\siemplify-{}"
BUFFER_SIZE = 4096
WAIT_TIMEOUT = 258
ERROR_PRIVILEGE_NOT_HELD = 1314
PS_COMMAND = '$objUser = New-Object System.Security.Principal.NTAccount("{}", "{}"); $strSID = $objUser.Translate([System.Security.Principal.SecurityIdentifier]); return $strSID.Value'
# ============================= CLASSES ===================================== #
# --------- NOTES --------
#  if you are encountered with permission issue -
# follow this steps:
# In the Siemplify Server Machine
# Open the Control Panel/Administrative Tools/Local Security Policy -->
# Click on LOCAL SECURITY POLICY --> USER RIGHTS ASSIGNMENT --> Replace a process level token
# Add the user the server runs from (if from code add your local user, else the python user: scripting)
# Restart the computer


class PermissionError(Exception):
    """
    Exception for Runners manager in case of required privilege
    """

    pass


class RunAsManagerError(Exception):
    """
    General Exception for Runners manager
    """

    pass


class RunnersManagerBuilder:
    @staticmethod
    def create_manager(is_linux=False):
        if is_linux:
            return RunnersManagerPosix()

        import pywintypes
        import subprocess
        import win32api
        import win32security
        import win32con
        import win32process
        import win32file
        import win32pipe
        import win32profile
        import win32event
        import winerror
        import secrets

        class RunnersManager:
            """
            Runners Manager
            """

            def __init__(self):
                pass

            def create_named_pipe(self, sids=None):
                """
                Create a named pipe.
                :param sids: {list} The sids to grant access to the pipe
                :return: {tuple} (The pipe, the name of the pipe)
                """
                if sids is None:
                    sattrs = None
                else:
                    # Create the security attributes of the pipe
                    sattrs = self.create_security_attributes(
                        sids, access=win32con.PROCESS_ALL_ACCESS
                    )

                # Try to create a named pipe (find a free name)
                for i in range(100):
                    name = PIPE_NAME.format(secrets.randbelow(999999))
                    try:
                        # Try to create the named pipe
                        pipe = win32pipe.CreateNamedPipe(
                            name,
                            win32con.PIPE_ACCESS_DUPLEX,
                            0,
                            1,
                            65536,
                            65536,
                            100000,
                            sattrs,
                        )

                        # Set the inheritance info of the pipe
                        win32api.SetHandleInformation(
                            pipe, win32con.HANDLE_FLAG_INHERIT, 0
                        )

                    except WindowsError as e:
                        if e.winerror != winerror.ERROR_PIPE_BUSY:
                            # Pipe name is taken - try again with another name
                            raise
                    else:
                        return pipe, name

                raise Exception("Could not create pipe after 100 attempts.")

            def create_security_attributes(
                self,
                sids,
                inherit=False,
                access=win32con.GENERIC_READ | win32con.GENERIC_WRITE,
            ):
                """
                Create a SECURITY_ATTRIBUTES structure.
                :param sids: {list} The sids to grant access to in the security attributes
                :param inherit: {bool} Whether to inherit handles or not
                :param access: {int} The access to grant
                :return: {SECURITY_ATTRIBUTES} The security attributes
                """

                attr = win32security.SECURITY_ATTRIBUTES()
                attr.bInheritHandle = inherit

                desc = win32security.SECURITY_DESCRIPTOR()
                dacl = win32security.ACL()

                for sid in sids:
                    dacl.AddAccessAllowedAce(win32security.ACL_REVISION_DS, access, sid)

                desc.SetSecurityDescriptorDacl(True, dacl, False)

                attr.SECURITY_DESCRIPTOR = desc
                return attr

            def lookup_sid(self, domain, username):
                """
                Get the sid of a user by domain and username
                :param domain: {str} The domain
                :param username: {str} The username
                :return: {PySID} The sid
                """
                try:
                    return win32security.LookupAccountName(domain, username)[0]
                except Exception:
                    try:
                        p = subprocess.Popen(
                            [
                                "powershell",
                                "-NoProfile",
                                "-Command",
                                PS_COMMAND.format(domain, username),
                            ],
                            stdout=subprocess.PIPE,
                        )
                        return win32security.ConvertStringSidToSid(
                            p.communicate()[0].strip("\r\n")
                        )
                    except Exception:
                        raise Exception(f"Unable to get SID of {domain}\\{username}")

            def create_startup_info(
                self, stdin_name, stdout_name, stderr_name, daemon=False
            ):
                """
                Create the startup info for a process
                :param stdin_name: {str} The name of the stdin pipe
                :param stdout_name: {str} The name of the stdout pipe
                :param stderr_name: {str} The name of the stderr pipe
                :param daemon: {bool} Thether to run in the background or not
                :return: {STARTUPINFO} The startup info
                """
                startupinfo = win32process.STARTUPINFO()
                startupinfo.dwFlags |= (
                    win32con.STARTF_USESTDHANDLES | win32con.STARTF_USESHOWWINDOW
                )

                if daemon:
                    # Hide the window
                    startupinfo.wShowWindow = win32con.SW_HIDE

                else:
                    # Show the window
                    startupinfo.wShowWindow = win32con.SW_SHOWNORMAL

                # Get the named pipes
                stdin_pipe = win32file.CreateFile(
                    stdin_name,
                    win32con.GENERIC_READ,
                    0,
                    None,
                    win32con.OPEN_EXISTING,
                    0,
                    None,
                )

                # Make sure the pipe handles are inherited
                win32api.SetHandleInformation(
                    stdin_pipe, win32con.HANDLE_FLAG_INHERIT, 1
                )
                stdout_pipe = win32file.CreateFile(
                    stdout_name,
                    win32con.GENERIC_WRITE,
                    0,
                    None,
                    win32con.OPEN_EXISTING,
                    0,
                    None,
                )
                # Make sure the pipe handles are inherited
                win32api.SetHandleInformation(
                    stdout_pipe, win32con.HANDLE_FLAG_INHERIT, 1
                )
                stderr_pipe = win32file.CreateFile(
                    stderr_name,
                    win32con.GENERIC_WRITE,
                    0,
                    None,
                    win32con.OPEN_EXISTING,
                    0,
                    None,
                )
                # Make sure the pipe handles are inherited
                win32api.SetHandleInformation(
                    stderr_pipe, win32con.HANDLE_FLAG_INHERIT, 1
                )
                # Set the process's std pipes
                startupinfo.hStdInput = stdin_pipe
                startupinfo.hStdOutput = stdout_pipe
                startupinfo.hStdError = stderr_pipe

                return startupinfo

            def get_current_sid(self):
                """
                Get the current process's / thread's sid
                :return: {PySID} The sid
                """
                try:
                    # Try to get the token of the current thread
                    token = win32security.OpenThreadToken(
                        win32api.GetCurrentThread(), win32con.MAXIMUM_ALLOWED, True
                    )
                except:
                    # Try to get the token of the current process
                    token = win32security.OpenProcessToken(
                        win32api.GetCurrentProcess(), win32con.MAXIMUM_ALLOWED
                    )

                # Get the sid by token
                return win32security.GetTokenInformation(
                    token, win32security.TokenUser
                )[0]

            def run_command_as_user(
                self, command, username, domain, password, deamon=False
            ):
                """
                Run a command as another user
                :param command: {str} The command to run
                :param username: {str} The username
                :param domain: {str} The domain
                :param password: {str} The password
                :param deamon: {bool} Whether to run in the background or not
                :return:  {int, str, str} return_code, stdout, stderr
                """
                # Get user's token
                usertoken = win32security.LogonUser(
                    username,
                    domain,
                    password,
                    win32con.LOGON32_LOGON_INTERACTIVE,
                    win32con.LOGON32_PROVIDER_DEFAULT,
                )

                # Get the sid's of the current user and the given user to run the process as
                sids = [self.get_current_sid(), self.lookup_sid(domain, username)]

                # Create security attributes
                if sids is None:
                    sattrs = None
                else:
                    sattrs = self.create_security_attributes(
                        sids, inherit=True, access=win32con.PROCESS_ALL_ACCESS
                    )

                # Create the named pipes
                stdin_pipe, stdin_name = self.create_named_pipe(sids)
                stdout_pipe, stdout_name = self.create_named_pipe(sids)
                stderr_pipe, stderr_name = self.create_named_pipe(sids)

                # Make sure that the parent process's pipe ends are not inherited
                win32api.SetHandleInformation(
                    stdin_pipe, win32con.HANDLE_FLAG_INHERIT, 0
                )
                win32api.SetHandleInformation(
                    stdout_pipe, win32con.HANDLE_FLAG_INHERIT, 0
                )
                win32api.SetHandleInformation(
                    stderr_pipe, win32con.HANDLE_FLAG_INHERIT, 0
                )

                try:
                    environment = win32profile.CreateEnvironmentBlock(usertoken, False)
                except:
                    environment = None

                try:
                    profile_dir = win32profile.GetUserProfileDirectory(usertoken)
                except:
                    profile_dir = None

                # Create process's startup info
                startup_info = self.create_startup_info(
                    stdin_name, stdout_name, stderr_name, deamon
                )

                try:
                    # Create process
                    res = win32process.CreateProcessAsUser(
                        usertoken,
                        None,
                        command,
                        sattrs,
                        None,
                        True,
                        win32con.CREATE_NEW_CONSOLE,
                        environment,
                        profile_dir,
                        startup_info,
                    )
                except Exception as e:
                    if e.winerror == ERROR_PRIVILEGE_NOT_HELD:
                        raise PermissionError(
                            f"Permission to replace a process level token is required (in local policies). Error: {e}"
                        )
                    raise RunAsManagerError(f"Error: {e}")

                process_handle = res[0]  # The process handle
                res[1].Close()  # Close the thread handle - not relevant
                pid = res[2]  # The pid

                # Connect to the pipes
                win32pipe.ConnectNamedPipe(stdin_pipe)
                win32pipe.ConnectNamedPipe(stdout_pipe)
                win32pipe.ConnectNamedPipe(stderr_pipe)

                return_code = self.wait_for_process(process_handle)
                stdout = self.read_stdout(process_handle, stdout_pipe)
                stderr = self.read_stdout(process_handle, stderr_pipe)

                return return_code, stdout, stderr

            def wait_for_process(self, process_handle):
                """
                Wait fir process and return its return code
                :param process_handle: {PyHANDLE} The process handle
                :return: {int} The return code of the process
                """
                # Wait for the process to complete
                win32event.WaitForSingleObject(process_handle, win32event.INFINITE)

                # Get return code
                return win32process.GetExitCodeProcess(process_handle)

            def read_stdout(self, process_handle, std_pipe, chunk=BUFFER_SIZE):
                """
                Read output from std pipe
                :param std_pipe: {PyHANDLE} THe pipe handle
                :return: {str} The output
                """
                output = ""

                try:
                    while True:
                        if (
                            not win32event.WaitForSingleObject(process_handle, 0)
                            == WAIT_TIMEOUT
                            and not win32pipe.PeekNamedPipe(std_pipe, chunk)[1]
                        ):
                            # Process is finished and no more data is available - break
                            # the loop
                            break

                        # Check whether there is data to read from the pipe
                        _, bytes_to_read, _ = win32pipe.PeekNamedPipe(std_pipe, chunk)

                        if bytes_to_read:
                            output += win32file.ReadFile(
                                std_pipe, min(bytes_to_read, chunk)
                            )[1]

                except pywintypes.error as e:
                    if e.winerror == winerror.ERROR_BROKEN_PIPE:
                        # Pipe is closed - no more data to read from the pipe
                        pass
                    else:
                        raise

                std_pipe.Close()
                return output

        return RunnersManager()


class RunnersManagerPosix:
    """
    Runners Manager
    """

    COMMAND = "echo {password} | su - {username} -c '{command}'"

    def __init__(self):
        pass

    def run_command_as_user(self, command, username, domain, password, deamon=False):
        """
        Run a command as another user
        :param command: {str} The command to run
        :param username: {str} The username
        :param domain: {str} The domain
        :param password: {str} The password
        :param deamon: {bool} Whether to run in the background or not
        :return: {int, str, str} return_code, stdout, stderr
        """
        if domain:
            username = rf"{domain}\{username}"
        process = subprocess.Popen(
            self.COMMAND.format(command=command, username=username, password=password),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr
