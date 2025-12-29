from __future__ import annotations

from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime, unix_now

from .constants import BATCH_SIZE
from .ListSummary import ListSummary
from .utils import (
    create_tag_list,
    merge_ip_summary_responses_for_enrichment,
    remove_empty_elements,
)


class EnrichIPs(ListSummary):
    def __init__(self, siemplify, ip_addresses):
        """Initialize EnrichIPs instance.

        Args:
            siemplify (SiemplifyAction): an instance of SiemplifyAction class.
            ip_addresses (list): a list of IP addresses to query.

        Attributes:
            summary (list): holds the summary of the IPs.
            siemplify (SiemplifyAction): instance of SiemplifyAction class.
            logger (logging.Logger): logging.Logger instance.
            ip_addresses (list): a list of IP addresses to query.
            error (str): an error message if something goes wrong.

        """
        self.summary = []
        self.siemplify = siemplify
        self.logger = siemplify.LOGGER
        self.error = ""
        self.ip_addresses = ip_addresses

    def get_ips_summary(self, api_manager):
        """Makes an API call to list IPs summary and aggregates the results.

        Args:
            api_manager (ApiManager): an instance of ApiManager class.

        Returns:
            int: a boolean indicating success, the response, a list of valid IPs, an additional message, and a dictionary of API usage.

        """
        summary = []
        invalid_response = []

        processed_ips = 0
        while processed_ips < len(self.ip_addresses):
            ip_batch = self.ip_addresses[processed_ips : processed_ips + BATCH_SIZE]

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
        self.summary, self.usage = merge_ip_summary_responses_for_enrichment(summary)

        return len(self.summary)

    def get_enrichment_data(self, ip_address):
        """Returns a dictionary containing the enrichment data for the given IP address.

        Args:
            ip_address (str): the IP address to query.

        Returns:
            dict: a dictionary containing the enrichment data of the IP address.

        """
        enrichment_dict = {
            "rating": self.summary[ip_address]
            .get("insights", {})
            .get("overall_rating", ""),
            "last_enriched": str(convert_unixtime_to_datetime(unix_now())),
            "tags": ", ".join(
                create_tag_list(self.summary[ip_address].get("tags", [])),
            ),
        }

        return remove_empty_elements(enrichment_dict)
