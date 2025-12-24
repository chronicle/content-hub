from __future__ import annotations

import requests
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler


class FullContactManager:
    def __init__(self, api_key, verify_ssl=True):
        # self.api_key = api_key
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self.verify_ssl = verify_ssl

    def enrich_person(self, email):
        url = "https://api.fullcontact.com/v3/person.enrich"
        data = {"email": email}
        res = requests.post(
            url,
            headers=self._headers,
            json=data,
            verify=self.verify_ssl,
        )
        return res

    def enrich_domain(self, domain):
        url = "https://api.fullcontact.com/v3/company.enrich"
        data = {"domain": domain}
        res = requests.post(
            url,
            headers=self._headers,
            json=data,
            verify=self.verify_ssl,
        )
        return res


@output_handler
def main():
    siemplify = SiemplifyAction()

    conf = siemplify.get_configuration("Full Contact")
    api_key = conf["API Key"]

    enriched_entities = []
    json_result = {}
    for ent in siemplify.target_entities:
        domain = None
        user_email = None
        enriched = False
        if ent.entity_type == EntityTypes.USER:
            domain = ent.identifier.split("@")[1]
            user_email = ent.identifier

        enrichment_json = {}
        enrichment_json["FullContact_CompanyName"] = ""
        enrichment_json["FullContact_CompanyType"] = ""
        enrichment_json["FullContact_FoundedYear"] = ""
        enrichment_json["FullContact_CompanyEmployees"] = ""
        enrichment_json["FullContact_CompanyWebSite"] = ""
        enrichment_json["FullContact_CompanyCountry"] = ""
        enrichment_json["FullContact_CompanyCity"] = ""

        enrichment_json["FullContact_Person_Linkedin"] = ""
        enrichment_json["FullContact_Person_Title"] = ""
        enrichment_json["FullContact_Person_Gender"] = ""

        if domain:
            fcm = FullContactManager(api_key)
            res2 = fcm.enrich_domain(domain).json()
            while res2.get("status") == 202:
                res2 = fcm.enrich_domain(domain).json()

            if "status" not in res2 or res2["status"] != 404:
                enriched = True
                enrichment_json["raw"] = res2
                enrichment_json["FullContact_CompanyName"] = res2["name"]
                try:
                    enrichment_json["FullContact_CompanyType"] = res2["details"][
                        "industries"
                    ][0]["name"]
                except Exception as x:
                    print(x)
                try:
                    enrichment_json["FullContact_CompanyCountry"] = res2["details"][
                        "locations"
                    ][0]["country"]
                except Exception as x:
                    print(x)
                try:
                    enrichment_json["FullContact_CompanyCity"] = res2["details"][
                        "locations"
                    ][0]["city"]
                except Exception as x:
                    print(x)

                enrichment_json["FullContact_FoundedYear"] = res2["founded"]
                enrichment_json["FullContact_CompanyEmployees"] = res2["employees"]
                enrichment_json["FullContact_CompanyWebSite"] = res2["website"]

        if user_email:
            fcm = FullContactManager(api_key)
            email_res = fcm.enrich_person(user_email).json()
            if "status" not in email_res or email_res["status"] != 404:
                enriched = True
                enrichment_json["FullContact_Person_Gender"] = email_res["gender"]
                enrichment_json["FullContact_Person_Title"] = email_res["title"]
                enrichment_json["FullContact_Person_Linkedin"] = email_res["linkedin"]

        ent.additional_properties["FullContact_CompanyName"] = enrichment_json[
            "FullContact_CompanyName"
        ]
        ent.additional_properties["FullContact_CompanyType"] = enrichment_json[
            "FullContact_CompanyType"
        ]
        ent.additional_properties["FullContact_FoundedYear"] = enrichment_json[
            "FullContact_FoundedYear"
        ]
        ent.additional_properties["FullContact_CompanyEmployees"] = enrichment_json[
            "FullContact_CompanyEmployees"
        ]
        ent.additional_properties["FullContact_CompanyWebSite"] = enrichment_json[
            "FullContact_CompanyWebSite"
        ]
        ent.additional_properties["FullContact_CompanyCountry"] = enrichment_json[
            "FullContact_CompanyCountry"
        ]
        ent.additional_properties["FullContact_CompanyCity"] = enrichment_json[
            "FullContact_CompanyCity"
        ]

        ent.additional_properties["FullContact_Person_Gender"] = enrichment_json[
            "FullContact_Person_Gender"
        ]
        ent.additional_properties["FullContact_Person_Title"] = enrichment_json[
            "FullContact_Person_Title"
        ]
        ent.additional_properties["FullContact_Person_Linkedin"] = enrichment_json[
            "FullContact_Person_Linkedin"
        ]

        if enriched:
            json_result[ent.identifier] = enrichment_json
            enriched_entities.append(ent)

    result_value = len(enriched_entities)
    if result_value > 0:
        siemplify.update_entities(enriched_entities)
    # siemplify.result.add_json('Enrichment Data', enrichment_json)

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))
    # siemplify.result.add_json(enrichment_json)

    output_message = "{} enriched entities:\n{}".format(
        result_value,
        "\n".join([x.identifier for x in enriched_entities]),
    )

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
