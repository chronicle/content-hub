from __future__ import annotations

from .constants import DELIMITER, SECTION_TO_TABLE_MAPPING
from .IPInfo import IPInfo
from .utils import (
    create_table_from_list,
    create_tag_list,
    remove_empty_elements_for_hr,
    remove_nulls_from_dictionary,
    render_data_table,
)


class IPInfoSection(IPInfo):
    def __init__(self, siemplify, section):
        """Initialize IPInfoSection instance.

        Args:
            siemplify (SiemplifyAction): an instance of SiemplifyAction class.
            section (str): the section to query from Team Cymru Scout.

        Attributes:
            siemplify (SiemplifyAction): instance of SiemplifyAction class.
            logger (logging.Logger): logging.Logger instance.
            ip_address (str): the IP address to query.
            error (bool): an error indicator.
            params (dict): the parameters for the API call.
            section (str): the section to query from Team Cymru Scout.
            response (dict): the response from the API call.
            summary (dict): the summary of the response.

        """
        super().__init__(siemplify)
        if not self.error:
            self.section = section
            self.params["sections"] = [self.section]

    def _pdns_table(self):
        """Creates a table from all the PDNS of the IP."""
        table = []

        for ip in self.response:
            pdns = self.response[ip].get("pdns", {}).get("pdns", [])

            for row in pdns:
                table.append(
                    {
                        "IP": ip,
                        "Domain": row.get("domain", "-"),
                        "Event Count": row.get("event_count", "-"),
                        "First Seen": row.get("first_seen", "-"),
                        "Last Seen": row.get("last_seen", "-"),
                    },
                )

        return table

    def _peers_table(self):
        """Creates a table from all the Peers of the IP."""
        table = []

        for ip in self.response:
            top_peers = self.response[ip].get("communications", {}).get("peers", [])

            table += [
                {
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

        table = remove_empty_elements_for_hr(table)
        [remove_nulls_from_dictionary(data) for data in table]
        return table

    def _open_ports_table(self):
        """Creates a table from the all open ports of the IP."""
        table = []

        for ip in self.response:
            open_ports = self.response[ip].get("open_ports", {}).get("open_ports", [])
            for row in open_ports:
                table.append(
                    {
                        "IP": ip,
                        "Service": row.get("service", "-"),
                        "First Seen": row.get("first_seen", "-"),
                        "Last Seen": row.get("last_seen", "-"),
                        "Event Count": row.get("event_count", "-"),
                        "Port": row.get("port", "-"),
                        "Protocol": row.get("protocol", "-"),
                        "Protocol Text": row.get("protocol_text", "-"),
                    },
                )

        return table

    def _fingerprints_table(self):
        """Creates a table from the all fingerprints of the IP."""
        table = []

        for ip in self.response:
            fingerprints = (
                self.response[ip].get("fingerprints", {}).get("fingerprints", [])
            )

            for row in fingerprints:
                table.append(
                    {
                        "IP": ip,
                        "Type": row.get("type", "-"),
                        "Signature": row.get("fingerprint", "-"),
                        "First Seen": row.get("first_seen", "-"),
                        "Last Seen": row.get("last_seen", "-"),
                        "Count": row.get("event_count", "-"),
                        "Port": row.get("port", "-"),
                    },
                )

        return table

    def _certificates_table(self):
        """Creates a table from the all certificates of the IP."""
        table = []

        for ip in self.response:
            certificates = self.response[ip].get("x509", {}).get("x509", [])
            rows_for_single_ip = remove_empty_elements_for_hr(
                create_table_from_list(
                    certificates,
                    ignore_fields=(
                        "serial",
                        "altnames",
                        "country_codes",
                        "as_info",
                        "tags",
                        "count",
                    ),
                ),
            )

            for row in rows_for_single_ip:
                row["Valid Days"] = row.get("Validity Period", "-")
                if "Validity Period" in row:
                    del row["Validity Period"]

                remove_nulls_from_dictionary(row)

            table += rows_for_single_ip

        return table

    def _whois_table(self):
        """Creates a table from the all whois of the IP."""
        table = []

        for ip in self.response:
            whois = self.response[ip].get("whois", {})
            rows_for_single_ip = {
                "IP": ip,
                "ASN": whois.get("asn", "-"),
                "As Name": whois.get("as_name", "-"),
                "BGP ASN": whois.get("bgp_asn", "-"),
                "BGP ASN Name": whois.get("bgp_asn_name", "-"),
                "Net Name": whois.get("net_name", "-"),
                "Org Name": whois.get("org_name", "-"),
                "Org Email": whois.get("org_email", "-"),
                "Abuse Contact Id": whois.get("abuse_contact_id", "-"),
                "Admin Contact Id": whois.get("admin_contact_id", "-"),
                "Tech Contact Id": whois.get("tech_contact_id", "-"),
            }
            table.append(rows_for_single_ip)

        return table

    def _proto_by_ip_table(self):
        """Creates a table from the all proto_by_ip of the IP."""
        table = []

        for ip in self.response:
            proto_by_ip = (
                self.response[ip]
                .get("proto_by_ip", {})
                .get("data", {})
                .get("proto_by_date", [])
            )
            rows_for_single_ip = remove_empty_elements_for_hr(
                create_table_from_list(proto_by_ip),
            )

            for row in rows_for_single_ip:
                row["IP"] = ip
                remove_nulls_from_dictionary(row)

            table += rows_for_single_ip

        return table

    def generate_tables(self):
        """Generates a table from the IP details according to the section given in the input."""
        table_name, method_name = SECTION_TO_TABLE_MAPPING[self.section]
        table_method = getattr(self, method_name)

        render_data_table(self.siemplify, table_name, table_method())
