# ==============================================================================
# title           :FileOperationManager.py
# description     :This Module contain all file operations functionality
# author          :org@siemplify.co
# date            :11-13-17
# python_version  :2.7
# ==============================================================================

# =====================================
#              IMPORTS               #
# =====================================
from __future__ import annotations
import os
import shutil
import zipfile
import tarfile
import datetime
import paramiko
import uuid


# =====================================
#             CONSTANTS               #
# =====================================
ZIP_EXTENTION = ".zip"
TARGZ_EXTENTION = ".tar.gz"
TIME_STAMP_FORMAT = "{:%Y%m%d_%H%M%S_%f}"
SSH_PORT = 22
ZIP_SSH_COMMAND = "zip -r {0} {1} -i '{2}'"
TAR_SSH_COMMAND = "find {0} -name '{1}' | tar -P -cf {2} -T -"


# =====================================
#              CLASSES                #
# =====================================
class FileOperationError(Exception):
    """
    General Exception for file operation manager
    """

    pass


class FileOperationManager:
    """
    Responsible for all file operations functionality
    """

    def _get_server_ssh_session(self, server_ip, username, password):
        """
        Create SSH session to remote server
        :param server_ip: {string}
        :param username: {string}
        :param password: {string}
        :return: {object} paramiko SSHClient
        """
        ssh_client = paramiko.client.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(server_ip, SSH_PORT, username, password)
        return ssh_client

    def _get_server_sftp_ssesion(self, server_ip, username, password):
        """
        Create SSH ssesion to remote server
        :param server_ip: {string} server address
        :param username: {string}
        :param password: {string}
        :return: {object} sftp client object (paramiko data model)
        """
        transport = paramiko.Transport(server_ip, SSH_PORT)
        transport.connect(username=username, password=password)
        return paramiko.SFTPClient.from_transport(transport)

    def _join_unix_path(self, path, file_name):
        # Remove redundant '/' if necessary
        if path[-1] == "/":
            path = path[:-1]
        return f"{path}/{file_name}"

    def transfer_file_win_to_win(self, source_file_path, dest_path, keep_file=False):
        """
        Transfer file from windows path to another windows path
        :param source_file_path: {string}
        :param dest_path: {string}
        :param keep_file: {boolean} Indicates weather to keep the file in source
        :return: {boolean} success indicator
        """
        if not keep_file or keep_file == "False":
            shutil.move(source_file_path, dest_path)
            print(f"remove file {source_file_path}")
        else:
            shutil.copy(source_file_path, dest_path)
        return os.path.join(dest_path, os.path.basename(source_file_path))

    def transfer_file_win_to_unix(
        self,
        source_win_file_path,
        dest_unix_ip,
        dest_unix_username,
        dest_unix_password,
        dest_unix_path,
        keep_file,
    ):
        """
        Transfer file from windows path to remote unix path
        :param source_win_file_path: {string}
        :param dest_unix_ip: {string}
        :param dest_unix_username: {string}
        :param dest_unix_password: {string}
        :param dest_unix_path: {string}
        :param keep_file: {boolean} Indicates weather to keep the file in source
        :return: {boolean} success indicator
        """
        sftp_client = self._get_server_sftp_ssesion(
            dest_unix_ip, dest_unix_username, dest_unix_password
        )
        # Attach file name to destination path
        file_name = os.path.basename(source_win_file_path)
        dest_path = self._join_unix_path(dest_unix_path, file_name)
        size = sftp_client.put(source_win_file_path, dest_path)
        if not keep_file or keep_file == "False":
            print(f"remove file {source_win_file_path}")
            os.remove(source_win_file_path)
        sftp_client.close()
        if size:
            return dest_path
        raise FileOperationError("File transfer failed")

    def transfer_file_unix_to_win(
        self,
        source_unix_ip,
        source_unix_username,
        source_unix_password,
        source_unix_file_path,
        dest_win_path,
        keep_file=False,
    ):
        """
        Transfer file from remote unix path to windows path
        :param source_unix_ip: {string}
        :param source_unix_username: {string}
        :param source_unix_password: {string}
        :param source_unix_file_path: {string}
        :param dest_win_path: {string}
        :param keep_file: {boolean} Indicates weather to keep the file in source
        :return: {boolean} success indicator
        """
        sftp_client = self._get_server_sftp_ssesion(
            source_unix_ip, source_unix_username, source_unix_password
        )
        # Attach file name to destination path
        file_name = os.path.basename(source_unix_file_path)
        dest_path = os.path.join(dest_win_path, file_name)
        sftp_client.get(source_unix_file_path, dest_path)
        if not keep_file or keep_file == "False":
            print(f"remove file {source_unix_file_path}")
            sftp_client.remove(source_unix_file_path)
        sftp_client.close()
        return dest_path

    def transfer_file_unix_to_unix(
        self,
        source_unix_ip,
        source_unix_username,
        source_unix_password,
        source_unix_file_path,
        dest_unix_ip,
        dest_unix_username,
        dest_unix_password,
        dest_unix_path,
        keep_file=False,
    ):
        """
        Transfer file from remote unix path to remote unix path
        :param source_unix_ip: {string}
        :param source_unix_username: {string}
        :param source_unix_password: {string}
        :param source_unix_file_path: {string}
        :param dest_unix_ip: {string}
        :param dest_unix_username: {string}
        :param dest_unix_password: {string}
        :param dest_unix_path: {string}
        :param keep_file: {boolean} Indicates weather to keep the file in source
        :return: {boolean} success indicator
        """
        src_sftp_client = self._get_server_sftp_ssesion(
            source_unix_ip, source_unix_username, source_unix_password
        )
        dest_sftp_client = self._get_server_sftp_ssesion(
            dest_unix_ip, dest_unix_username, dest_unix_password
        )
        # Attach file name to destination path
        file_name = os.path.basename(source_unix_file_path)
        dest_path = self._join_unix_path(dest_unix_path, file_name)

        # Temporary save the file localy
        temp_file_name = str(uuid.uuid4())
        src_sftp_client.get(source_unix_file_path, temp_file_name)
        # Send local file to server
        size = dest_sftp_client.put(temp_file_name, dest_path)
        # Delete the origin file if necessary
        if size.st_size:
            if not keep_file or keep_file == "False":
                print(f"remove file {source_unix_file_path}")
                src_sftp_client.remove(source_unix_file_path)
            # Delete temporary file
            os.remove(temp_file_name)
            src_sftp_client.close()
            dest_sftp_client.close()
            return dest_path
        raise FileOperationError("Error transfer file")

    def zip_windows(self, source_folder, file_filter, output_folder):
        """
        Crate zip file contain all files in file_filter from specific folder path
        :param source_folder: {string} The folder with the relevant files
        :param file_filter: {string} files extension to include in zip file {ex: *.txt}
        :param output_folder: {string}
        :return: {boolean} success indicator
        """
        # Create zip file unique name (time stamp)
        zip_name = TIME_STAMP_FORMAT.format(datetime.datetime.now()) + ZIP_EXTENTION
        output_path = os.path.join(output_folder, zip_name)
        # Create zipfile object
        zipf = zipfile.ZipFile(output_path, "w")
        # Walk thought all files in source folder
        for root, dirs, files in os.walk(source_folder):
            for file_name in files:
                # Verify files extensions are suitable
                if os.path.splitext(file_name)[1] == os.path.splitext(file_filter)[1]:
                    # Add files to zip
                    zipf.write(os.path.join(root, file_name), file_name)
        zipf.close()
        return output_path

    def zip_over_ssh_linux(
        self, server_ip, username, password, source_folder, file_filter, output_folder
    ):
        """
        Create zip file over ssh on a remote linux server
        :param server_ip: {string}
        :param username: {string}
        :param password: {string}
        :param source_folder: {string} The remote server folder with the relevant files
        :param file_filter: {string} files extension to include in zip file {ex: *.txt}
        :param output_folder: {string} The remote server folder to put the zip file into
        :return: {boolean} success indicator
        """
        ssh_client = self._get_server_ssh_session(server_ip, username, password)
        # Create zip file unique name (time stamp)
        zip_name = TIME_STAMP_FORMAT.format(datetime.datetime.now()) + ZIP_EXTENTION
        output_path = self._join_unix_path(output_folder, zip_name)
        # Add all *. to file filter if necessary
        if file_filter[0:2] != "*.":
            file_filter = "*." + file_filter
        zip_command = ZIP_SSH_COMMAND.format(output_path, source_folder, file_filter)
        (stdin, stdout, stderr) = ssh_client.exec_command(zip_command)
        # Error restarting WCG service
        error = stderr.read()
        if error:
            raise FileOperationError(f"Failed to execute tar command error: {error}")
        return output_path

    def targz_windows(self, source_folder, file_filter, output_folder):
        """
        Crate targzip file contain all files in file_filter from specific folder path
        :param source_folder: {string} The folder with the relevant files
        :param file_filter: {string} files extension to include in targzip file {ex: *.txt}
        :param output_folder: {string}
        :return: {boolean} success indicator
        """
        # Create targzip file unique name (time stamp)
        tar_name = TIME_STAMP_FORMAT.format(datetime.datetime.now()) + TARGZ_EXTENTION
        output_path = os.path.join(output_folder, tar_name)
        # Create targz file object
        tarf = tarfile.TarFile(output_path, "w")
        # Walk thought all files in source folder
        for root, dirs, files in os.walk(source_folder):
            for file_name in files:
                # Verify files extensions are suitable
                if os.path.splitext(file_name)[1] == os.path.splitext(file_filter)[1]:
                    # Add files to targz
                    tarf.add(os.path.join(root, file_name), file_name)
        tarf.close()
        return output_path

    def targz_over_ssh_linux(
        self, server_ip, username, password, source_folder, file_filter, output_folder
    ):
        """
        Create targz file over ssh on a remote linux server
        :param server_ip: {string}
        :param username: {string}
        :param password: {string}
        :param source_folder: {string} The remote server folder with the relevant files
        :param file_filter: {string} files extension to include in zip file {ex: *.txt}
        :param output_folder: {string} The remote server folder to put the zip file into
        :return: {boolean} success indicator
        """
        ssh_client = self._get_server_ssh_session(server_ip, username, password)
        # Create zip file unique name (time stamp)
        tar_name = TIME_STAMP_FORMAT.format(datetime.datetime.now()) + TARGZ_EXTENTION
        output_path = self._join_unix_path(output_folder, tar_name)
        # Add all *. to file filter if necessary
        if file_filter[0:2] != "*.":
            file_filter = "*." + file_filter
        tar_command = TAR_SSH_COMMAND.format(source_folder, file_filter, output_path)
        (stdin, stdout, stderr) = ssh_client.exec_command(tar_command)
        # Error restarting WCG service
        error = stderr.read()
        if error:
            raise FileOperationError(f"Failed to execute tar command error: {error}")
        return output_path

    def get_remote_unix_file_content(
        self, server_ip, username, password, remote_file_path
    ):
        """
        Retrieve file content (file blob) from remote linux host
        :param server_ip: {string} The remote linux server address
        :param username: {string} Remote server creds
        :param password: {string} Remote server creds
        :param remote_file_path: {string} The file path on the remote server
        :return:
        """
        sftp_client = self._get_server_sftp_ssesion(server_ip, username, password)
        file_content = sftp_client.open(remote_file_path, mode="rb")
        return file_content.read()
