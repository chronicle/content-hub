# Copyright 2025 Google LLC
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

import dns.resolver
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

SCRIPT_NAME = "QueryDNS"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    dns_servers = siemplify.parameters.get("DNS Servers")

    output_message = "No address or hostname found"
    entities_exist = False
    server_list = dns_servers.split(",")

    json_results = {}
    res = dns.resolver.Resolver(configure=False)
    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.ADDRESS:
            entities_exist = True
            for server in server_list:
                server = server.strip()
                res.nameservers = [server]
                try:
                    siemplify.LOGGER.info(
                        f"--- Checking {server} for a reverse DNS entry for IP {entity.identifier} ---",
                    )
                    answer = res.resolve_address(entity.identifier)
                    entityidentifier = entity.identifier

                    if answer:
                        siemplify.LOGGER.info(
                            f"A reverse name PTR record for {entity.identifier} was found on DNS server {server}",
                        )
                        ptr_record = "PTR"
                        if entityidentifier not in json_results:
                            json_results[entityidentifier] = []
                        json_results[entityidentifier].append(
                            {
                                "Type": ptr_record,
                                "Response": answer.rrset[0],
                                "DNS Server": server,
                            },
                        )

                        output_message = "Results Found"
                except Exception as err:
                    siemplify.LOGGER.exception(err)

        elif entity.entity_type == EntityTypes.HOSTNAME:
            entities_exist = True
            try:
                entityidentifier = entity.identifier
                outbound_query = dns.message.make_query(
                    entity.identifier,
                    getattr(dns.rdatatype, siemplify.parameters["Data Type"]),
                )

                for server in server_list:
                    try:
                        server = server.strip()
                        siemplify.LOGGER.info(
                            f"--- Checking {server} for entity {entity.identifier} ---",
                        )

                        answer = dns.query.udp(outbound_query, server)

                        if answer.answer:
                            for i in range(len(answer.answer)):
                                print(
                                    f"A record of type {dns.rdatatype.to_text(answer.answer[i].rdtype)} was found on DNS server {server} with a response of {answer.answer[i][0]} for entity {entity.identifier}",
                                )

                                hn_record = dns.rdatatype.to_text(
                                    answer.answer[i].rdtype,
                                )
                                record_response = str(answer.answer[i][0]).strip('"')

                                if entityidentifier not in json_results:
                                    json_results[entityidentifier] = []

                                json_results[entityidentifier].append(
                                    {
                                        "Type": hn_record,
                                        "Response": record_response,
                                        "DNS Server": server,
                                    },
                                )

                            output_message = "Results Found"
                        else:
                            siemplify.LOGGER.info("No record found")

                    except Exception as err:
                        siemplify.LOGGER.error(err)
            except Exception as err:
                siemplify.LOGGER.error(err)

    if json_results:
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
        siemplify.end(output_message, "true")
    else:
        if entities_exist:
            output_message = "No records found"
        siemplify.end(output_message, "false")


if __name__ == "__main__":
    main()
