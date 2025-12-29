from __future__ import annotations

from airtable import Airtable
from soar_sdk.SiemplifyAction import SiemplifyAction

INTEGRATION_NAME = "AirTable"


def main():
    siemplify = SiemplifyAction()

    api_key = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="Api key",
    )
    base_id = siemplify.parameters["Base Id"]
    table_name = siemplify.parameters["Table name"]

    airtable = Airtable(base_id, table_name, api_key)
    results = airtable.get_all()
    records_ids = []
    for result in results:
        record_id = result["id"]
        records_ids.append(record_id)
        # airtable.delete(record_id)

    airtable.API_LIMIT = 0.00005
    airtable.batch_delete(records_ids)

    records_count = len(records_ids)
    output_message = (
        f"{records_count} records in table {table_name} were deleted successfully."
    )
    siemplify.end(output_message, records_count)


if __name__ == "__main__":
    main()
