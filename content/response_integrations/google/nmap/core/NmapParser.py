# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from collections import defaultdict
import xml.etree.ElementTree as ET

from TIPCommon.types import SingleJson


class NmapParser:
    """Parser for Nmap XML output with JSON conversion functionality"""

    def __init__(
        self,
        xml_file: str | None = None,
        xml_string: str | None = None,
    ) -> None:
        """Initialize the parser with either an XML file or XML string

        Args:
            xml_file (str | None): Path to Nmap XML output file
            xml_string (str| None): Nmap XML output as string

        Raises:
            ValueError: If neither `xml_file` nor `xml_string` is provided.
        """
        if xml_file is None and xml_string is None:
            raise ValueError("Either xml_file or xml_string must be provided")

        if xml_file:
            self.root: ET.Element = ET.parse(xml_file).getroot()
        else:
            self.root: ET.Element = ET.fromstring(xml_string)

        self.enrichment_table_data: SingleJson = {}
        self.parsed_data: SingleJson = self._parse_nmap_xml()

    def _parse_nmap_xml(self) -> SingleJson:
        result: SingleJson = self._parse_hosts()

        return result

    def _parse_hosts(self) -> SingleJson:
        """Parse host elements.

        This method iterates through each host element found in the XML and extracts
        relevant information such as status, addresses, and hostnames.

        Returns:
            SingleJson: A dictionary containing information about the scanned hosts.
        """
        host_data: SingleJson = {}

        for host in self.root.findall("./host"):
            host_data = {
                "status": self._parse_status(host),
                "addresses": self._parse_addresses(host),
                "hostnames": self._parse_hostnames(host),
                "ports": self._parse_ports(host),
                "os": self._parse_os(host),
                "uptime": self._parse_uptime(host),
                "distance": self._parse_distance(host),
                "tcpsequence": self._parse_tcpsequence(host),
                "ipidsequence": self._parse_ipidsequence(host),
                "tcptssequence": self._parse_tcptssequence(host),
            }

            host_data = {k: v for k, v in host_data.items() if v}

        return host_data

    def _parse_status(self, host_elem: ET.Element) -> SingleJson:
        """Parse the status element of a host.

        Args:
            host_elem (ET.Element): The XML element representing a host.

        Returns:
            SingleJson: A dictionary containing the status attributes
                (e.g., state, reason).
        """
        status_element: ET.Element | None = host_elem.find("./status")

        if status_element is None:
            return {}

        status_dict: SingleJson = dict(status_element.attrib)

        if "state" in status_dict:
            self.enrichment_table_data.update({"Nmap_state": status_dict["state"]})

        return status_dict

    def _parse_addresses(self, host_elem: ET.Element) -> list[SingleJson]:
        """Parse address elements associated with a host.

        Args:
            host_elem (ET.Element): The XML element representing a host.

        Returns:
            list[SingleJson]: A list of dictionaries, each containing address attributes
                (e.g., addr, addrtype).
        """
        addresses: list[SingleJson] = []
        grouped_addresses_by_type: defaultdict[str, list[str]] = defaultdict(list)

        for addr_element in host_elem.findall("./address"):
            addr_dict: SingleJson = dict(addr_element.attrib)
            addresses.append(addr_dict)

            address_value: str | None = addr_dict.get("addr")
            address_type: str | None = addr_dict.get("addrtype")

            if address_value and address_type:
                grouped_addresses_by_type[address_type].append(address_value)

        for addr_type, addr_list in grouped_addresses_by_type.items():
            self.enrichment_table_data[f"Nmap_related_addresses_{addr_type}"] = (
                ",".join(addr_list)
            )

        return addresses

    def _parse_hostnames(self, host_elem: ET.Element) -> list[SingleJson]:
        """Parse hostname elements.

        Retrieves hostnames associated with a host, if available.

        Args:
            host_elem (ET.Element): The XML element representing a host.

        Returns:
            list[SingleJson]: A list of dictionaries, each containing hostname
                attributes (e.g., name, type).
        """
        hostnames: list[SingleJson] = []
        hostnames_elem: ET.Element | None = host_elem.find("./hostnames")

        if hostnames_elem is None:
            return []

        names: list[str] = []
        for hostname in hostnames_elem.findall("./hostname"):
            hostname_dict: SingleJson = dict(hostname.attrib)
            hostnames.append(hostname_dict)

            name_value: str | None = hostname_dict.get("name")
            if name_value:
                names.append(name_value)

        if names:
            self.enrichment_table_data.update(
                {"Nmap_related_hostnames": ",".join(names)}
            )

        return hostnames

    def _parse_ports(self, host_elem: ET.Element) -> SingleJson:
        """Parse ports element.

        Extracts information about open, closed, or filtered ports on a host,
        including service details and script results.

        Args:
            host_elem (ET.Element): The XML element representing a host.

        Returns:
            SingleJson: A dictionary containing port information,
            structured with 'extraports' and 'ports' keys.
            Each port includes state, service, and script details.
        """
        ports_elem: ET.Element | None = host_elem.find("./ports")
        if ports_elem is None:
            return {}

        result: SingleJson = {
            "extraports": self._parse_extraports(ports_elem),
            "ports": self._parse_port_list(ports_elem),
        }

        if not result["extraports"]:
            del result["extraports"]

        return result

    def _parse_extraports(self, ports_elem: ET.Element) -> list[SingleJson]:
        """Parse <extraports> elements and their nested <extrareasons>.

        Args:
            ports_elem (ET.Element): The parent <ports> XML element.

        Returns:
            list[SingleJson]: A list of dictionaries, where each dictionary
                represents an <extraports> element and its attributes,
                potentially including a list of "reasons". Returns an empty
                list if no <extraports> elements are found.
        """
        extraports_data: list[SingleJson] = []

        for ep_elem in ports_elem.findall("./extraports"):
            ep_dict: SingleJson = dict(ep_elem.attrib)

            reasons: list[SingleJson] = [
                dict(reason.attrib) for reason in ep_elem.findall("./extrareasons")
            ]
            if reasons:
                ep_dict["reasons"] = reasons

            extraports_data.append(ep_dict)

        return extraports_data

    def _parse_port_list(self, ports_elem: ET.Element) -> list[SingleJson]:
        """Parse all <port> elements within a <ports> XML section.

        Args:
            ports_elem (ET.Element): The parent <ports> XML element containing <port>
            children.

        Returns:
            list[SingleJson]: A list of dictionaries, where each dictionary contains
                comprehensive information about a single port. Returns an empty
                list if no <port> elements are found.
        """
        port_dicts: list[SingleJson] = []

        for port_elem in ports_elem.findall("./port"):
            port_info: SingleJson = dict(port_elem.attrib)
            port_id: int | None = port_info.get("portid")  # for enrichment name
            port_key: str = f"Nmap_port_{port_id}" if port_id else None

            # state, service, scripts
            state_key: str | None = self._attach_state(port_elem, port_info)
            service_key: str | None = self._attach_service(port_elem, port_info)
            self._attach_port_scripts(port_elem, port_info)

            # build enrichment table
            if port_key:
                self._update_enrichment(port_key, state_key, service_key)

            port_dicts.append(port_info)

        return port_dicts

    def _attach_state(self, port_elem: ET.Element, port_info: SingleJson) -> str | None:
        """Parse the <state> element of a port and update port_info.

        Args:
            port_elem (ET.Element): The <port> XML element from which to extract state.
            port_info (SingleJson): The dictionary representing the port's information,
                which will be updated with the state details.

        Returns:
            str | None: The value of the "state" attribute (e.g., "open", "closed")
                if found, otherwise None.
        """
        state_elem: ET.Element | None = port_elem.find("./state")
        if state_elem is None:
            return None

        state_dict: SingleJson = dict(state_elem.attrib)
        port_info["state"] = state_dict

        if "state" in state_dict:
            port_info["status"] = state_dict["state"]

        return state_dict.get("state")

    def _attach_service(
        self,
        port_elem: ET.Element,
        port_info: SingleJson,
    ) -> str | None:
        """Parse the <service> element of a port and update port_info.
        Args:
            port_elem (ET.Element): The <port> XML element from which to extract service
                details.
            port_info (SingleJson): The dictionary representing the port's information,
                which will be updated with the service details.

        Returns:
            str | None: The value of the "product" attribute if available, otherwise the
                value of the "name" attribute. Returns None if the <service> element
                is not found or if neither "product" nor "name" attributes are present.
                This value is intended for use in enrichment data.
        """
        service_elem: ET.Element | None = port_elem.find("./service")
        if service_elem is None:
            return None

        service_dict: SingleJson = dict(service_elem.attrib)

        cpes: list[str] = [
            cpe.text for cpe in service_elem.findall("./cpe") if cpe.text
        ]
        if cpes:
            service_dict["cpes"] = cpes

        service_scripts: list[SingleJson] = [
            dict(service_script.attrib)
            for service_script in service_elem.findall("./script")
        ]
        if service_scripts:
            service_dict["scripts"] = service_scripts

        port_info["service"] = service_dict

        if "name" in service_dict:
            port_info["service_name"] = service_dict["name"]

        return service_dict.get("product") or service_dict.get("name")

    def _attach_port_scripts(
        self,
        port_elem: ET.Element,
        port_info: SingleJson,
    ) -> None:
        """Parse <script> elements directly under a <port> and update port_info.

        Args:
            port_elem (ET.Element): The <port> XML element.
            port_info (SingleJson): The dictionary representing the port's information,
                which will be updated with script details if any are found.
        """
        port_scripts: list[SingleJson] = [
            dict(port_script.attrib) for port_script in port_elem.findall("./script")
        ]
        if port_scripts:
            port_info["scripts"] = port_scripts

    def _update_enrichment(
        self,
        field_name: str,
        state_key: str | None,
        service_key: str | None,
    ) -> None:
        """Update the enrichment table with formatted port state and
        service information.

        Args:
            field_name (str): The key to use in `self.enrichment_table_data`.
            state_key (str | None): The state of the port (e.g., "open", "closed").
            service_key (str | None): The service name or product (e.g., "http", "ssh").
        """
        if state_key is None:
            return

        suffix: str = service_key if service_key else "Service Info N/A"
        self.enrichment_table_data[field_name] = f"{state_key} - {suffix}"

    def _parse_os_class_details(self, match_elem: ET.Element) -> list[SingleJson]:
        """Parse <osclass> elements and their nested <cpe> elements.

        Args:
            match_elem (ET.Element): The parent XML element (usually <osmatch>)
                containing <osclass> children.

        Returns:
            list[SingleJson]: A list of dictionaries, where each dictionary represents
                an <osclass> element and its attributes, including a list of CPEs
                if available. Returns an empty list if no <osclass> elements are found.
        """
        os_classes: list[SingleJson] = []
        for os_class_elem in match_elem.findall("./osclass"):
            class_dict: SingleJson = dict(os_class_elem.attrib)

            cpes: list[str] = [
                cpe.text for cpe in os_class_elem.findall("./cpe") if cpe.text
            ]
            if cpes:
                class_dict["cpes"] = cpes

            os_classes.append(class_dict)

        return os_classes

    def _parse_os_matches_details(
        self,
        os_elem: ET.Element,
    ) -> tuple[list[SingleJson], list[str]]:
        """Parse <osmatch> elements, their details, and associated OS fingerprints.

        Args:
            os_elem (ET.Element): The parent <os> XML element containing
            <osmatch> children.

        Returns:
            tuple[list[SingleJson], list[str]]: A tuple containing:
                - A list of dictionaries, each representing an <osmatch> with
                its details.
                - A list of OS names extracted from the "name" attribute of
                each <osmatch>.
        """
        os_matches_list: list[SingleJson] = []
        os_names_list: list[str] = []

        parsed_os_fingerprints = self._parse_os_fingerprint_details(os_elem)

        for match_elem in os_elem.findall("./osmatch"):
            match_dict: SingleJson = dict(match_elem.attrib)

            if name_val := match_dict.get("name"):
                os_names_list.append(name_val)

            os_classes = self._parse_os_class_details(match_elem)
            if os_classes:
                match_dict["osclasses"] = os_classes

            if parsed_os_fingerprints:
                match_dict["osfingerprints"] = parsed_os_fingerprints

            os_matches_list.append(match_dict)

        return os_matches_list, os_names_list

    def _parse_os_fingerprint_details(self, os_elem: ET.Element) -> list[SingleJson]:
        """Parse <osfingerprint> elements from an <os> XML element.

        Args:
            os_elem (ET.Element): The parent <os> XML element.

        Returns:
            list[SingleJson]: A list of dictionaries, where each dictionary
                represents an <osfingerprint> element and its attributes. Returns
                an empty list if no <osfingerprint> elements are found.
        """
        fingerprints: list[SingleJson] = []
        for fp_elem in os_elem.findall("./osfingerprint"):
            fingerprints.append(dict(fp_elem.attrib))

        return fingerprints

    def _parse_os(self, host_elem: ET.Element) -> SingleJson:
        """Parse os element.

        Attempts to identify the operating system running on a host based on
        scan results, including OS matches, OS classes, and fingerprints.

        Args:
            host_elem (ET.Element): The XML element representing a host.

        Returns:
            SingleJson: A dictionary containing OS information,
                structured with 'portused', 'osmatches', and 'osfingerprints' keys.
                Each match includes OS class details.
        """
        os_elem: ET.Element | None = host_elem.find("./os")
        if os_elem is None:
            return {}

        result: SingleJson = {}

        portused_elem: ET.Element | None = os_elem.find("./portused")
        if portused_elem is not None:
            result["portused"] = dict(portused_elem.attrib)

        os_matches_list, os_names_list = self._parse_os_matches_details(os_elem)
        if os_matches_list:
            result["osmatches"] = os_matches_list
        if os_names_list:
            self.enrichment_table_data["Nmap_os_matches"] = ",".join(os_names_list)

        return result

    def _parse_uptime(self, host_elem: ET.Element) -> SingleJson:
        """Parse uptime element. Retrieves the host's uptime information, if available.

        Args:
            host_elem (ET.Element): The XML element representing a host.

        Returns:
            SingleJson: A dictionary containing uptime attributes
                (e.g., seconds, lastboot).
        """

        uptime_elem: ET.Element | None = host_elem.find("./uptime")
        if uptime_elem is None:
            return None

        uptime_dict: SingleJson = dict(uptime_elem.attrib)

        if "lastboot" in uptime_dict:
            self.enrichment_table_data.update(
                {"Nmap_last_boot": uptime_dict["lastboot"]}
            )

        return uptime_dict

    def _parse_distance(self, host_elem: ET.Element) -> SingleJson:
        """Parse distance element."""
        distance: ET.Element | None = host_elem.find("./distance")
        if distance is not None:
            return dict(distance.attrib)

        return {}

    def _parse_tcpsequence(self, host_elem: ET.Element) -> SingleJson:
        """Parse tcpsequence element."""
        tcpsequence: ET.Element | None = host_elem.find("./tcpsequence")
        if tcpsequence is not None:
            return dict(tcpsequence.attrib)

        return {}

    def _parse_ipidsequence(self, host_elem: ET.Element) -> SingleJson:
        """Parse ipidsequence element."""
        ipidsequence: ET.Element | None = host_elem.find("./ipidsequence")
        if ipidsequence is not None:
            return dict(ipidsequence.attrib)

        return {}

    def _parse_tcptssequence(self, host_elem: ET.Element) -> SingleJson:
        """Parse tcptssequence element."""
        tcptssequence: ET.Element | None = host_elem.find("./tcptssequence")
        if tcptssequence is not None:
            return dict(tcptssequence.attrib)

        return {}

    def to_dict(self) -> SingleJson:
        return self.parsed_data

    def to_enrichment(self) -> SingleJson:
        return self.enrichment_table_data
