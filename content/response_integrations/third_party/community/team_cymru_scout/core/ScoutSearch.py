from __future__ import annotations

from copy import deepcopy

from .constants import DELIMITER
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


class ScoutSearch:
    def __init__(self, siemplify):
        """Initialize ScoutSearch instance.

        Args:
            siemplify (SiemplifyAction): an instance of SiemplifyAction class.

        Attributes:
            siemplify (SiemplifyAction): instance of SiemplifyAction class.
            logger (logging.Logger): logging.Logger instance.
            query (str): the query to search in Scout.
            error (bool): an error indicator.
            params (dict): the parameters for the API call.
            response (dict): the response from the API call.
            summary (dict): the summary of the response.

        """
        self.siemplify = siemplify
        self.logger = siemplify.LOGGER

        self.query = siemplify.extract_action_param(
            "Query",
            is_mandatory=True,
            default_value='comms.ip="1.1.1.1"',
        ).strip()
        self.error, self.params = get_common_query_parameters(self.siemplify)

        self.response = None
        self.summary = None

    def scout_search(self, api_manager):
        """Makes an API call to search in Scout.

        Args:
            api_manager (ApiManager): an instance of ApiManager class.

        Returns:
            tuple: a tuple containing a boolean indicating success and the response from the API call.

        """
        is_success, response = api_manager.scout_search(self.query, **self.params)

        if is_success is True:
            self.response = response
            self.summary = self.response.get("ips", []) or []

        return is_success, deepcopy(response)

    def _scout_search_summary_row(self, ip_summary):
        """Creates a row for the scout search summary table.

        Args:
            ip_summary (dict): a dictionary containing the ip summary information.

        Returns:
            dict: a dictionary containing the row data for the scout search summary table.

        """
        country_codes = DELIMITER.join(ip_summary.get("country_codes", []))

        whois_info = ip_summary.get("summary", {}).get("whois", {})
        whois_columns = create_row_from_dict(whois_info)

        tags = create_tag_list(ip_summary.get("tags", []))

        return {
            "IP": ip_summary.get("ip", "-"),
            "Country Code(s)": country_codes,
            **whois_columns,
            "Tags": tags,
            "Event Count": ip_summary.get("event_count", "-"),
            "Last Seen": ip_summary.get("summary", {}).get("last_seen", "-"),
        }

    def _create_scout_search_summary_table(self):
        """Creates a table from the summary info of the IPs.

        :return: A list of dictionaries where each dictionary represents a row in the table.
        """
        return [self._scout_search_summary_row(ip) for ip in self.summary]

    def _create_scout_search_pdns_information_table(self):
        """Creates a table from the PDNS information of the IPs.

        :return: A list of dictionaries where each dictionary represents a row in the table.
        """
        pdns_information = []
        for scout_ip in self.summary:
            pdns_info = scout_ip.get("summary", {}).get("pdns", [])
            pdns_info_for_ip = create_table_from_list(pdns_info)
            for row in pdns_info_for_ip:
                row["IP"] = row.get("Ip", "-")
                del row["Ip"]

            pdns_information += pdns_info_for_ip

        return pdns_information

    def _create_scout_search_open_ports_table(self):
        """Creates a table from the open ports of the IPs.

        :return: A list of dictionaries where each dictionary represents a row in the table.
        """
        ports_information = []
        for scout_ip in self.summary:
            ports_info = scout_ip.get("summary", {}).get("open_ports", [])
            ports_info_for_ip = create_table_from_list(ports_info)
            for row in ports_info_for_ip:
                row["IP"] = row.get("Ip", "-")
                del row["Ip"]

            ports_information += ports_info_for_ip

        return ports_information

    def _create_scout_search_top_peers_table(self):
        """Creates a table from the top peers of the IPs.

        :return: A list of dictionaries where each dictionary represents a row in the table.
        """
        top_peers = []
        for scout_ip in self.summary:
            source_ip = scout_ip.get("ip", "-")
            peer_info = scout_ip.get("summary", {}).get("top_peers", [])
            peer_info_for_ip = create_table_from_list(peer_info)
            for row in peer_info_for_ip:
                row["Source IP"] = source_ip
                row["IP"] = row.get("Ip", "-")
                del row["Ip"]

            top_peers += peer_info_for_ip

        return top_peers

    def _create_scout_search_service_count_information_table(self):
        """Creates a table from the service count information of the IPs.

        :return: A list of dictionaries where each dictionary represents a row in the table.
        """
        service_counts = []
        for scout_ip in self.summary:
            source_ip = scout_ip.get("ip", "-")
            counts_info = scout_ip.get("summary", {}).get("service_counts", [])
            counts_info_for_ip = create_table_from_list(counts_info)

            for row in counts_info_for_ip:
                row["Source IP"] = source_ip
                service = row.get("Service")
                if service and isinstance(service, dict):
                    row["Service"] = DELIMITER.join(
                        f"{key}: {value}" for key, value in list(row["Service"].items())
                    )

            service_counts += counts_info_for_ip

        return service_counts

    def _create_scout_search_fingerprints_information_table(self):
        """Creates a table from the fingerprints information of the IPs.

        :return: A list of dictionaries where each dictionary represents a row in the table.
        """
        fingerprints = []
        for scout_ip in self.summary:
            fingerprint_information = scout_ip.get("summary", {}).get(
                "fingerprints",
                [],
            )
            fingerprint_information_for_ip = create_table_from_list(
                fingerprint_information,
            )
            for row in fingerprint_information_for_ip:
                row["IP"] = row.get("Ip", "-")
                del row["Ip"]

            fingerprints += fingerprint_information_for_ip

        return fingerprints

    def _create_scout_search_certs_information_table(self):
        """Creates a table from the certificate information of the IPs.

        :return: A list of dictionaries where each dictionary represents a row in the table.
        """
        certificates = []
        for scout_ip in self.summary:
            certificate_info = scout_ip.get("summary", {}).get("certs", [])
            certificate_info_for_ip = create_table_from_list(certificate_info)
            for row in certificate_info_for_ip:
                row["IP"] = row.get("Ip", "-")
                del row["Ip"]

            certificates += certificate_info_for_ip

        return certificates

    def _create_scout_search_tables(self):
        """Creates all the tables that will be used in the result of the action.

        :return: A tuple of seven lists of dictionaries where each dictionary represents a row in the table.
        """
        summary_table = self._create_scout_search_summary_table()
        pdns_table = self._create_scout_search_pdns_information_table()
        open_ports_table = self._create_scout_search_open_ports_table()
        top_peers_table = self._create_scout_search_top_peers_table()
        service_counts_table = (
            self._create_scout_search_service_count_information_table()
        )
        fingerprints_table = self._create_scout_search_fingerprints_information_table()
        certs_table = self._create_scout_search_certs_information_table()

        return (
            summary_table,
            pdns_table,
            open_ports_table,
            top_peers_table,
            service_counts_table,
            fingerprints_table,
            certs_table,
        )

    def generate_tables(self):
        """Generates the tables for the scout search action.

        The tables are constructed by transforming the response from the scout search action into a list of dictionaries where each dictionary represents a row in the table.

        The tables are then added to the result object of the action.
        """
        for ip_info in self.summary:
            ip_info = remove_empty_elements(ip_info)
            remove_nulls_from_dictionary(ip_info)

        tables = self._create_scout_search_tables()

        new_table_list = []
        for table in tables:
            table = remove_empty_elements_for_hr(table)
            [remove_nulls_from_dictionary(data) for data in table]
            new_table_list.append(table)

        (
            summary,
            pdns,
            open_ports,
            top_peers,
            service_count,
            fingerprints,
            certificates,
        ) = new_table_list

        render_data_table(self.siemplify, "Summary Information", summary)
        render_data_table(self.siemplify, "PDNS Information", pdns)
        render_data_table(self.siemplify, "Open Ports Information", open_ports)
        render_data_table(self.siemplify, "Top Peers Information", top_peers)
        render_data_table(self.siemplify, "Service Counts Information", service_count)
        render_data_table(self.siemplify, "Fingerprints Information", fingerprints)
        render_data_table(self.siemplify, "Certs Information", certificates)
