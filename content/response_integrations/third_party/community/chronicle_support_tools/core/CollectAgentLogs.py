from __future__ import annotations

import os
import re

# CSAL

log_path = "/var/log/SiemplifyAgent/agent.log"
integration_log_file_base_path = "/opt/SiemplifyAgent/Integrations/"
error_identifier_in_agent_log = "- agent - ERROR"
connector_runner_log_identifier = "runner - ERROR -"
agent_normal_message = "- agent - INFO "
self_identification = "Gather Remote Agent Datapoints"
limit_of_error_logs_to_capture_default = 15


class CollectAgentLogs:
    _integration_name = None
    _connector_name = None
    _siemplify = None

    def __init__(
        self,
        integration_name,
        connector_name,
        siemplify,
        limit_of_error_logs_to_capture=limit_of_error_logs_to_capture_default,
    ):
        self._integration_name = integration_name
        self._connector_name = connector_name
        self._siemplify = siemplify
        self.limit_of_error_logs_to_capture = limit_of_error_logs_to_capture

    def find_integration_folders(self, base_file_path, pattern_string):
        matching_folders = []
        pattern = re.compile(rf"{pattern_string}_V(?P<version>\d+\.\d+)")

        for root, dirs, _ in os.walk(base_file_path):
            for dir_name in dirs:
                match = pattern.match(dir_name)
                if match:
                    version_str = match.group("version")  # Extract the version part
                    matching_folders.append((version_str, os.path.join(root, dir_name)))

        # Sort by version number
        matching_folders.sort(key=lambda item: [float(x) for x in item[0].split(".")])

        return [
            folder_path for _, folder_path in matching_folders
        ]  # Return just the folder paths

    def find_connector_log(self, base_folder_path, connector_name):
        log_files = []

        for root, dirs, files in os.walk(base_folder_path):
            if "Connectors" in dirs:  # Check if "Connectors" is in the current level
                connectors_path = os.path.join(root, "Connectors")
                for subdir in os.listdir(connectors_path):
                    if subdir.startswith(connector_name):
                        log_file_path = os.path.join(
                            connectors_path,
                            subdir,
                            "connectors_runner.log",
                        )
                        if os.path.isfile(log_file_path):
                            creation_time = os.path.getctime(log_file_path)
                            log_files.append((log_file_path, creation_time))

        if log_files:
            log_files.sort(
                key=lambda item: item[1],
                reverse=True,
            )  # Sort by creation time (descending)
            return log_files[0:3]

        return []  # File not found

    def parse_error_logs(self, textData):
        errorCapture = ""
        allErrors = []
        keepCapturing = False

        for x in textData:
            # dont capture self log.
            if (
                error_identifier_in_agent_log in x and self_identification not in x
            ) or keepCapturing:
                errorCapture += x + "\n"
                keepCapturing = True
            if agent_normal_message in x and keepCapturing:
                keepCapturing = False
                allErrors.append(errorCapture)
                errorCapture = ""

        return allErrors

    def parse_connector_runner_logs(self, textData):
        errorCapture = ""
        allErrors = []
        keepCapturing = False

        for x in textData:
            # TODO dont capture self log.
            if ("runner - WARNING" in x or "runner - INFO" in x) and keepCapturing:
                keepCapturing = False
                allErrors.append(errorCapture)
                errorCapture = ""

            if (connector_runner_log_identifier in x) or keepCapturing:
                errorCapture += x + "\n"
                keepCapturing = True

        totalErrorCount = len(allErrors)

        return allErrors[5:], totalErrorCount

    def read_connector_runner_logs(self, fileName):
        result = []

        try:
            logFile = open(fileName).read().split("\n")

            allErrors, errorLogCount = self.parse_connector_runner_logs(logFile)

            count = 1
            for elements in reversed(allErrors):
                if count <= self.limit_of_error_logs_to_capture:
                    result.append(
                        "================connectors_runner.log=====================",
                    )
                    result.append(elements)
                    count += 1

            result.append(
                "Captured "
                + str(errorLogCount)
                + " And logged "
                + str(count - 1)
                + " Errors",
            )

        except Exception as e:
            result.append(str(e))
            result.append("Unable to Read" + fileName + "file.")

        return result

    def read_agent_log_file(self):
        result = []

        try:
            logFile = open(log_path).read().split("\n")

            allErrors = self.parse_error_logs(logFile)
            total_error_count = len(allErrors)

            count = 1
            for elements in reversed(allErrors):
                if count <= self.limit_of_error_logs_to_capture:
                    result.append("================agent.log=====================")
                    result.append(elements)
                    count += 1

            result.append(
                "Captured "
                + str(total_error_count)
                + " And logged "
                + str(count - 1)
                + " Errors",
            )

        except Exception as e:
            result.append(str(e))
            result.append("Unable to Read agent.log file")

        return "\n".join(result)

    def read_connector_and_action_log(self):
        result = []

        try:
            if len(self._connector_name) > 0 and len(self._integration_name) > 0:
                # find the correct Integration/Connector File name.
                integrationFileName = self.find_integration_folders(
                    integration_log_file_base_path,
                    self._integration_name,
                )

                if integrationFileName != None and len(integrationFileName) > 1:
                    result.append(
                        "Found following Integration Folders "
                        + str(integrationFileName),
                    )

                if integrationFileName != None and len(integrationFileName) > 0:
                    # only if the Integration folder is present
                    # now find the Correct connector folder
                    files = self.find_connector_log(
                        integrationFileName[-1],
                        self._connector_name,
                    )
                    for conectorRunnerFile in files:
                        result.append(
                            "==========================================================",
                        )
                        result.append(
                            "Reading File  : "
                            + str(conectorRunnerFile[0])
                            + " Created on : "
                            + str(conectorRunnerFile[1]),
                        )
                        for x in self.read_connector_runner_logs(conectorRunnerFile[0]):
                            result.append(x)

        except Exception as e:
            result.append(str(e))
            result.append("Unable to Read connector log file")

        return "\n".join(result)

    def log_collected_info(self):
        self._siemplify.LOGGER.info(
            "============= Collecting Agent Log Information (CSAL) ================",
        )
        self._siemplify.LOGGER.info(str(self.read_agent_log_file()))
        self._siemplify.LOGGER.info(str(self.read_connector_and_action_log()))
        self._siemplify.LOGGER.info(
            "============= Finish Collecting Agent Log Information (CSAL) =============",
        )
