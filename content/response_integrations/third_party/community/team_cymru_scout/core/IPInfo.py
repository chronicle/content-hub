from __future__ import annotations

from copy import deepcopy

from .constants import DELIMITER, ERRORS, MAX_PAGE_SIZE
from .utils import (
    create_row_from_dict,
    create_table_from_list,
    create_tag_list,
    get_common_query_parameters,
    remove_empty_elements,
    remove_empty_elements_for_hr,
    remove_nulls_from_dictionary,
    render_data_table,
)
from .validator import validate_and_generate_optional_params, validate_multiple_ips


class IPInfo:
    def __init__(self, siemplify):
        """Initialize IPInfo instance.

        Args:
            siemplify (SiemplifyAction): an instance of SiemplifyAction class.

        Attributes:
            siemplify (SiemplifyAction): instance of SiemplifyAction class.
            logger (logging.Logger): logging.Logger instance.
            ip_address (str): the IP address to query.
            error (bool): an error indicator.
            params (dict): the parameters for the API call.
            response (dict): the response from the API call.
            summary (dict): the summary of the response.

        """
        self.siemplify = siemplify
        self.logger = siemplify.LOGGER
        self.error = ""
        self.response = {}
        self.summary = {}

        input_ip_addresses = siemplify.extract_action_param(
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

        if not self.error:
            self.ip_addresses = [ip.strip() for ip in input_ip_addresses.split(",")]
            self.error, self.params = get_common_query_parameters(self.siemplify)

            is_valid, params_response = validate_and_generate_optional_params(
                **self.params,
                max_size=MAX_PAGE_SIZE["IP_DETAILS"],
            )
            if not is_valid:
                self.error = ", ".join(params_response)
            else:
                self.params = params_response

    def get_ip_details(self, api_manager):
        """Makes an API call to get the IP details and aggregates the results.

        Args:
            api_manager (ApiManager): an instance of ApiManager class.

        Returns:
            tuple: a tuple containing a boolean indicating success, the response, a list of valid IPs, an additional message, and a dictionary of API usage.

        """
        additional_msg = ""
        valid_ips, invalid_ips, duplicate_ips = validate_multiple_ips(self.ip_addresses)

        # Filter the duplicate IP addresses
        if duplicate_ips:
            additional_msg += (
                ERRORS["VALIDATIONS"]["DUPLICATE_IPS_MSG"].format(
                    len(self.ip_addresses),
                    len(duplicate_ips),
                    ", ".join(duplicate_ips),
                )
                + "\n"
            )

        # Filter the invalid IP addresses
        if invalid_ips:
            additional_msg += (
                ERRORS["VALIDATIONS"]["INVALID_IPS_MSG"].format(
                    len(self.ip_addresses),
                    len(invalid_ips),
                    ", ".join(invalid_ips),
                )
                + "\n"
            )

        usage = {}
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

            invalid_response = []
            for ip in ips_to_process:
                is_success, response = api_manager.get_ip_details(ip, self.params)
                if is_success is True:
                    response = remove_empty_elements(response)
                    self.response[ip] = response
                    self.summary[ip] = response.get("summary", {})
                    usage = response.get("usage", {})
                else:
                    invalid_response.append(f"  - {ip}: {response}")

            # If any API call has failed, then show the error (failure) message
            if invalid_response:
                self.error = (
                    "Invalid response found for the following IPs:\n"
                    + "\n".join(invalid_response)
                    + "\n"
                )

        return (
            len(self.response),
            deepcopy(self.response),
            valid_ips,
            additional_msg,
            usage,
        )

    def _create_summary_table(self):
        """Creates a table from the summary info of the IP."""
        table = []

        for ip in self.summary:
            country_code = self.summary[ip].get("geo_ip_cc", "-")

            whois_info = remove_empty_elements_for_hr(self.summary[ip].get("whois", {}))
            whois_columns = create_row_from_dict(whois_info)

            tags = remove_empty_elements_for_hr(self.summary[ip].get("tags", []))
            tags_to_display = create_tag_list(tags)
            overall_insights_rating = (
                self.summary[ip].get("insights", {}).get("overall_rating", "-")
            )

            table.append(
                {
                    "IP": ip,
                    "Country Code": country_code,
                    **whois_columns,
                    "Tags": tags_to_display,
                    "Overall Insights Rating": overall_insights_rating,
                },
            )

        return table

    def _create_insights_table(self):
        """Creates a table from the insights of the IP."""
        table = []

        for ip in self.summary:
            insights = remove_empty_elements_for_hr(
                self.summary[ip].get("insights", {}).get("insights", []),
            )
            rows_for_single_ip = create_table_from_list(insights)

            for row in rows_for_single_ip:
                row["IP"] = ip

            table += rows_for_single_ip

        return table

    def _top_pdns_table(self):
        """Creates a table from the top PDNS of the IP."""
        table = []

        for ip in self.summary:
            top_pdns = self.summary[ip].get("pdns", {}).get("top_pdns", [])
            rows_for_single_ip = create_table_from_list(
                top_pdns,
                ignore_fields=("css_color",),
            )

            for row in rows_for_single_ip:
                row["IP"] = ip

            table += rows_for_single_ip

        return table

    def _top_peers_table(self):
        """Creates a table from the top Peers of the IP."""
        table = []

        for ip in self.response:
            top_peers = self.response[ip].get("communications", {}).get("peers", [])[:5]

            table += [
                {
                    "IP": ip,
                    "Proto": peer.get("proto_text", "-"),
                    "Client IP": peer.get("peer", {}).get("ip", "-"),
                    "Client Country Code(s)": DELIMITER.join(
                        peer.get("peer", {}).get("country_codes", []),
                    ),
                    "Client Services": DELIMITER.join(
                        [
                            str(service.get("port", "-"))
                            for service in remove_empty_elements_for_hr(
                                peer.get("peer", {}).get("top_services", [])[:5],
                            )
                        ],
                    ),
                    "Client Tag(s)": create_tag_list(
                        peer.get("peer", {}).get("tags", []),
                    ),
                    "Server IP": peer.get("local", {}).get("ip", "-"),
                    "Server Country Code(s)": DELIMITER.join(
                        peer.get("local", {}).get("country_codes", []),
                    ),
                    "Server Tag(s)": create_tag_list(
                        peer.get("local", {}).get("tags", []),
                    ),
                    "Server Services": DELIMITER.join(
                        [
                            str(service.get("port", "-"))
                            for service in remove_empty_elements_for_hr(
                                peer.get("local", {}).get("top_services", [])[:5],
                            )
                        ],
                    ),
                    "Event Count": peer.get("event_count", "-"),
                    "First Seen": peer.get("first_seen", "-"),
                    "Last Seen": peer.get("last_seen", "-"),
                    "Client AS Name": "\n".join(
                        [
                            as_info.get("as_name")
                            for as_info in peer.get("peer", {}).get("as_info", [])
                        ],
                    ),
                    "Server AS Name": "\n".join(
                        [
                            as_info.get("as_name")
                            for as_info in peer.get("local", {}).get("as_info", [])
                        ],
                    ),
                }
                for peer in top_peers
            ]

        return table

    def _top_open_ports_table(self):
        """Creates a table from the top open_ports of the IP."""
        table = []

        for ip in self.summary:
            open_ports = (
                self.summary[ip].get("open_ports", {}).get("top_open_ports", [])
            )
            rows_for_single_ip = create_table_from_list(
                open_ports,
                ignore_fields=("inferred_service_name",),
            )

            for row in rows_for_single_ip:
                row["IP"] = ip

            table += rows_for_single_ip

        return table

    def _top_fingerprints_table(self):
        """Creates a table from the top fingerprints of the IP."""
        table = []

        for ip in self.summary:
            fingerprints = (
                self.summary[ip].get("fingerprints", {}).get("top_fingerprints", [])
            )
            rows_for_single_ip = create_table_from_list(fingerprints)

            for row in rows_for_single_ip:
                row["IP"] = ip

            table += rows_for_single_ip

        return table

    def _top_certificates_table(self):
        """Creates a table from the top certificates of the IP."""
        table = []

        for ip in self.summary:
            certificates = self.summary[ip].get("certs", {}).get("top_certs", [])
            rows_for_single_ip = create_table_from_list(
                certificates,
                ignore_fields=("css_color",),
            )

            for row in rows_for_single_ip:
                row["IP"] = ip

            table += rows_for_single_ip

        return table

    def _create_ip_details_table(self):
        """Creates a list of all the tables that will be used in the result of the action."""
        summary_table = self._create_summary_table()
        insights_table = self._create_insights_table()
        pdns_table = self._top_pdns_table()
        peers_table = self._top_peers_table()
        ports_table = self._top_open_ports_table()
        fingerprints_table = self._top_fingerprints_table()
        certificates_table = self._top_certificates_table()

        return [
            summary_table,
            insights_table,
            pdns_table,
            peers_table,
            ports_table,
            fingerprints_table,
            certificates_table,
        ]

    def generate_tables(self):
        """Generates all the tables from the response of the IP details action."""
        tables = self._create_ip_details_table()

        new_table_list = []
        for table in tables:
            table = remove_empty_elements_for_hr(table)
            [remove_nulls_from_dictionary(data) for data in table]
            new_table_list.append(table)

        summary, insights, pdns, peers, ports, fingerprints, certificates = (
            new_table_list
        )

        render_data_table(self.siemplify, "Summary Information", summary)
        render_data_table(self.siemplify, "Insights", insights)
        render_data_table(self.siemplify, "Top PDNS", pdns)
        render_data_table(self.siemplify, "Top Peers", peers)
        render_data_table(self.siemplify, "Top Open Ports", ports)
        render_data_table(self.siemplify, "Top Fingerprints", fingerprints)
        render_data_table(self.siemplify, "Top Certificates", certificates)
