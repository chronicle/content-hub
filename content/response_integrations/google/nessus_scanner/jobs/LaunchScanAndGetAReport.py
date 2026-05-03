from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler

# ==============================================================================
# title           :LaunchScanAndGetAReport.py
# description     :Job for initiating scan in Nessus and get scan report
# author          :zivh@siemplify.co
# date            :01-02-18
# python_version  :2.7
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from ..core.NessusScannerManager import NessusScanner
from soar_sdk.SiemplifyJob import SiemplifyJob
import datetime
import os

# =====================================
#             CONSTANTS               #
# =====================================

TIME_STAMP_STR_FORMAT = "%Y-%m-%d_%H:%M:%S:%f"
TIME_FORMAT = "%Y.%m.%d-%H.%M.%S.%f"
TIME_STAMP_FILE_INITIATE_BACKWARDS = 0  # In days


# =====================================
#              CLASSES                #
# =====================================


def write_scan_to_local_file(scan_report, scan_name, file_path):
    """
    Write the scan report to local file
    :param scan_report: {string} file data
    :param scan_name: {string} file download name
    :param file_path: {string} file download full path
    :return: {string} file path
    """
    # create file path if not exist
    if not os.path.exists(file_path):
        os.makedirs(file_path)

    time = datetime.datetime.utcnow().strftime(TIME_FORMAT)[:-3]
    file_name = f"{scan_name}_{time}.html"
    new_path = os.path.join(file_path, file_name)

    scan_file = open(new_path, "a").write(scan_report)
    return new_path


@output_handler
def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = "NessusJob"

    try:
        siemplify.LOGGER.info("-----Job Started-----")

        # Parameters
        access_key = siemplify.parameters["Access Key"]
        secret_key = siemplify.parameters["Secret Key"]
        server_address = siemplify.parameters["Api Root"]
        scan_name = siemplify.parameters["Scan Name"]
        scan_path = siemplify.parameters["Scan Download Path"]

        nessus_client = NessusScanner(access_key, secret_key, server_address)

        siemplify.LOGGER.info(f"{scan_name} - Launch scan and wait for result")
        scan_id = nessus_client.launch_scan_and_wait(scan_name)

        siemplify.LOGGER.info("Get scan report")
        report = nessus_client.download_scan(scan_name)

        siemplify.LOGGER.info("Write scan report to local file")
        name = scan_name.replace(":", "-")
        scan_file_path = write_scan_to_local_file(report, name, scan_path)
        siemplify.LOGGER.info(f"Scan report was write to {scan_file_path}")

        siemplify.LOGGER.info("-----Job Finished-----")

    except Exception as e:
        siemplify.LOGGER._log.exception(e)
        raise


if __name__ == "__main__":
    main()
