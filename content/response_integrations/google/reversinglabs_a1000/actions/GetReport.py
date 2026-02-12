from __future__ import annotations

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    convert_dict_to_json_result_dict,
    dict_to_flat,
    flat_dict_to_csv,
    output_handler,
)

from ..core.A1000MalwareAnalysis import A1000MalwareAnalysisClient

# Consts
FILEHASH = EntityTypes.FILEHASH


@output_handler
def main():
    siemplify = SiemplifyAction()

    # Configuration.
    conf = siemplify.get_configuration("ReversinglabsA1000")
    server_address = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]

    a1000_manager = A1000MalwareAnalysisClient(server_address, username, password)

    hash_values = []

    for entity in siemplify.target_entities:
        if entity.entity_type == FILEHASH:
            hash_values.append(entity.identifier.lower())

    report = a1000_manager.get_report(hash_values)
    hash_report_dict = {}

    if report:
        # Add csv table
        for hash_report in report:
            hash_report_dict.update({hash_report["md5"]: hash_report})
            flat_report = dict_to_flat(hash_report)
            csv_output = flat_dict_to_csv(flat_report)
            siemplify.result.add_data_table(f"Hash Report {hash_report['md5']}:", csv_output)
        output_message = "Scan has been completed, Report is attached."
        result_value = True
    else:
        output_message = "Unable to attach a report."
        result_value = False

    # add json
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(hash_report_dict))
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
