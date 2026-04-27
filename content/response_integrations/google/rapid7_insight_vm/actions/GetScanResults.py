from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.Rapid7Manager import Rapid7Manager
from soar_sdk.SiemplifyUtils import dict_to_flat, flat_dict_to_csv
import time

SCRIPT_NAME = "Rapid7InsightVm - Get Scan Results"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("Rapid7InsightVm")
    rapid7_manager = Rapid7Manager(
        conf["Api Root"],
        conf["Username"],
        conf["Password"],
        conf.get("Verify SSL", "false").lower() == "true",
    )

    scan_id = siemplify.parameters["Scan ID"]
    json_results = {}

    while not rapid7_manager.is_scan_completed(scan_id):
        time.sleep(2)

    scan_info = rapid7_manager.get_scan_by_id(scan_id)

    if scan_info:
        json_results = scan_info

        if "links" in scan_info:
            del scan_info["links"]

        siemplify.result.add_data_table(
            f"Scan {scan_id} Info", flat_dict_to_csv(dict_to_flat(scan_info))
        )

    output_message = f"Scan {scan_id} results were fetch successfully."

    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
