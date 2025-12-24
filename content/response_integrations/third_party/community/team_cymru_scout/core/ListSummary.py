from __future__ import annotations

from .constants import BATCH_SIZE, ERRORS
from .utils import (
    create_row_from_dict,
    create_table_from_list,
    create_tag_list,
    merge_ip_summary_responses,
    remove_empty_elements,
    render_data_table,
)
from .validator import validate_multiple_ips


class ListSummary:
    def __init__(self, siemplify):
        """Initialize ListSummary instance.

        Args:
            siemplify (SiemplifyAction): an instance of SiemplifyAction class.

        Attributes:
            summary (list): holds the summary of the IPs.
            siemplify (SiemplifyAction): instance of SiemplifyAction class.
            logger (logging.Logger): logging.Logger instance.
            ip_addresses (str): comma-separated list of IP addresses.
            limit (int): the number of records to retrieve. Default is 10.

        """
        self.summary = []
        self.siemplify = siemplify
        self.logger = siemplify.LOGGER
        self.error = ""
        self.usage = {}

        self.ip_addresses = siemplify.extract_action_param(
            "IP Addresses",
            is_mandatory=True,
        ).strip()

        try:
            self.limit = siemplify.extract_action_param(
                "Limit",
                default_value=10,
                input_type=int,
            )
            if self.limit < 1:
                raise ValueError(f"Limit value: {self.limit} must be greater than 0.")
        except ValueError as err:
            self.error = f"Provided Limit value is not a valid integer. Error: {err}"

    def get_ips_summary(self, api_manager):
        """Makes an API call to list IPs summary and aggregates the results.

        Args:
            api_manager (ApiManager): an instance of ApiManager class.

        Returns:
            tuple: a tuple containing the length of successfully queried IPs indicating success, the valid IPs provided, the additional message to be shown to the user.

        """
        additional_msg = ""
        summary = []
        invalid_response = []

        ip_addresses = [ip.strip() for ip in self.ip_addresses.split(",")]
        valid_ips, invalid_ips, duplicate_ips = validate_multiple_ips(ip_addresses)

        # Filter the duplicate IP addresses
        if duplicate_ips:
            additional_msg += (
                ERRORS["VALIDATIONS"]["DUPLICATE_IPS_MSG"].format(
                    len(ip_addresses),
                    len(duplicate_ips),
                    ", ".join(duplicate_ips),
                )
                + "\n"
            )

        # Filter the invalid IP addresses
        if invalid_ips:
            additional_msg += (
                ERRORS["VALIDATIONS"]["INVALID_IPS_MSG"].format(
                    len(ip_addresses),
                    len(invalid_ips),
                    ", ".join(invalid_ips),
                )
                + "\n"
            )

        if not valid_ips:
            # All the IPs were found to be invalid
            self.error = ERRORS["VALIDATIONS"]["NO_VALID_IPS"]
        else:
            # At least one IP is valid, then check limit and make API calls
            ips_to_process = valid_ips[: self.limit]
            ips_to_skip = valid_ips[self.limit :]

            # If the valid IPs are more than the limit, we must skip the extra ones
            if ips_to_skip:
                additional_msg += (
                    ERRORS["VALIDATIONS"]["EXTRA_IPS"].format(
                        len(valid_ips),
                        self.limit,
                        len(ips_to_skip),
                        ", ".join(ips_to_skip),
                    )
                    + "\n"
                )

            # Batching
            processed_ips = 0
            while processed_ips < len(ips_to_process):
                ip_batch = ips_to_process[processed_ips : processed_ips + BATCH_SIZE]

                is_success, response = api_manager.list_ips_summary(ip_batch)
                if not is_success:
                    invalid_response.append(f"  - {ip_batch}: {response}")
                else:
                    summary.append(response)

                processed_ips += BATCH_SIZE

        # If any API call has failed, then show the error (failure) message
        if invalid_response:
            self.error = (
                "Invalid response found for the following IP Batches:\n"
                + "\n".join(invalid_response)
            )

        # Club all the responses received in the API calls
        self.summary, self.usage = merge_ip_summary_responses(summary)

        return len(self.summary), valid_ips, additional_msg

    def create_summary_table(self):
        """Creates a table from the summary info of the IPs.

        The table will include the IP, country code, autonomous system number, autonomous system name, overall insight rating and tags for each IP.

        :return: A list of dictionaries where each dictionary represents a row in the table.
        """
        summary_table = []
        for ip in self.summary:
            country_code = ip.get("country_code", "-")
            overall_insight_rating = ip.get("insights", {}).get("overall_rating", "-")
            tags = create_tag_list(ip.get("tags", []))

            all_as_info = ip.get("as_info", [])

            as_info = create_row_from_dict({"asn": "-", "as_name": "-"})
            if all_as_info:
                as_info = create_row_from_dict(all_as_info[0])

            summary_table.append(
                {
                    "IP": ip.get("ip", "-"),
                    "Country Code": country_code,
                    **as_info,
                    "Overall Insight Rating": overall_insight_rating,
                    "Tags": tags,
                },
            )

        return summary_table

    def create_insights_table(self):
        """Creates a table from the insights of the IPs.

        :return: A list of dictionaries where each dictionary represents a row in the table.
        """
        insights_table = []

        for ip in self.summary:
            insights = ip.get("insights", {}).get("insights", [])
            insights_table_for_ip = create_table_from_list(insights)

            for row in insights_table_for_ip:
                row["IP"] = ip.get("ip", "-")

            insights_table += insights_table_for_ip

        return insights_table

    def create_ips_summary_table(self):
        """Creates two tables from the IPs summary: a summary table and an insights table.

        :return: A tuple of two lists of dictionaries where the first list represents the summary table and the second list represents the insights table.
        """
        summary_table = self.create_summary_table()
        insights_table = self.create_insights_table()

        return summary_table, insights_table

    def generate_tables(self):
        """Generates two tables from the IPs summary: a summary table and an insights table.

        The tables are added to the result object of the action.

        :return: None
        """
        for ip_data in self.summary:
            ip_data = remove_empty_elements(ip_data)

        summary, insights = self.create_ips_summary_table()

        render_data_table(self.siemplify, "Summary Information for IPs", summary)
        render_data_table(self.siemplify, "Insights", insights)
