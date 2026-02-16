from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    flat_dict_to_csv,
    convert_dict_to_json_result_dict,
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

    a1000_manager = A1000MalwareAnalysisClient(
        server_address,
        username,
        password
    )

    hash_values = []
    hash_status_dict = {}

    for entity in siemplify.target_entities:
        if entity.entity_type == FILEHASH:
            hash_values.append(entity.identifier.lower())

    hash_status = a1000_manager.processing_status(hash_values)

    if hash_status:
        for hash_data in hash_status:
            hash_status_dict.update({hash_data["hash_value"]: hash_data["status"]})

        # Add csv table
        flat_report = dict_to_flat(hash_status_dict)
        csv_output = flat_dict_to_csv(flat_report)
        siemplify.result.add_data_table("Scan Status:", csv_output)
        output_message = "Scan completed successfully."
        result_value = True
    else:
        output_message = "Unable to get scan status."
        result_value = False

    # add json
    siemplify.result.add_result_json(
        convert_dict_to_json_result_dict(hash_status_dict)
    )
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
