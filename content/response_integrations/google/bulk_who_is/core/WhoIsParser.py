# =============================== CONSTS ==================================== #
from __future__ import annotations
OUTPUT_RES_KEY = "output"
RAW_OUTPUT_RES_KEY = "rawOutput"
COUNTRY_RES_KEY = "Country"
ADMIN_COUNTRY_RES_KEY = "Admin Country"
COUNTRY_CODE_RES_KEY = "country_code"
CITY_RES_KEY = "City"
ADMIN_CITY_RES_KEY = "Admin City"
REGISTRANT_KEY = "registrant_contact"
REGISTAR_COUNTRY = "Registar Country"
REGISTAR_CITY = "Registar City"
SUCCESS = "success"
REMOVE_VALUE = [
    "NOTICE",
    "For more information on Whois status codes, please visit https",
    "URL of the ICANN Whois Inaccuracy Complaint Form",
    "to",
    "by the following terms of use",
    "% for more information on IANA, visit http",
    "% you agree to abide by the following terms of use",
]
COUNTRY_KEYS_LIST = [REGISTAR_COUNTRY, COUNTRY_RES_KEY, ADMIN_COUNTRY_RES_KEY]
CITY_COUNTRY_LIST = [REGISTAR_CITY, ADMIN_CITY_RES_KEY, CITY_RES_KEY]
# ============================== CLASSES ==================================== #

from .datamodels import Detail


class WhoIsParser:

    def build_siemplify_detail_obj(self, detail_data):
        """
        Build Siemplify Detail Object
        The function creates Detail object from detail_data dict
        :return: Detail object
        """
        detail_data_dict = {}
        if RAW_OUTPUT_RES_KEY in detail_data and detail_data[RAW_OUTPUT_RES_KEY]:
            data = detail_data[RAW_OUTPUT_RES_KEY][0]
            # data is string, split the data so enrichment can be made
            splited_data = data.split("\n")
            # splited data is list that each element is a string in the following format 'key: value'
            for val in splited_data:
                splited_val = val.split(":")
                # splited_val is list that should contain at least two elements because the first is the key and the second is the value
                if len(splited_val) > 1:
                    # splited_val[0] is the key (e.g. domain name),  splited_val[1] is the value (e.g. 'google.in')
                    key = splited_val[0].lstrip()[0:235]
                    if key not in REMOVE_VALUE:
                        detail_data_dict[key] = str(splited_val[1].lstrip())
                    if splited_val[0] in COUNTRY_KEYS_LIST:
                        detail_data_dict[COUNTRY_RES_KEY] = str(splited_val[1])
                    if splited_val[0] in CITY_COUNTRY_LIST:
                        detail_data_dict[CITY_RES_KEY] = str(splited_val[1])
            if SUCCESS in detail_data:
                detail_data_dict[SUCCESS] = True if detail_data[SUCCESS] == 1 else False

        if OUTPUT_RES_KEY in detail_data:
            if REGISTRANT_KEY in detail_data[OUTPUT_RES_KEY]:
                if (
                    COUNTRY_RES_KEY.lower()
                    in detail_data[OUTPUT_RES_KEY][REGISTRANT_KEY]
                ):
                    detail_data_dict[COUNTRY_RES_KEY] = str(
                        detail_data[OUTPUT_RES_KEY][REGISTRANT_KEY][
                            COUNTRY_RES_KEY.lower()
                        ]
                    )
                if COUNTRY_CODE_RES_KEY in detail_data[OUTPUT_RES_KEY][REGISTRANT_KEY]:
                    detail_data_dict[COUNTRY_CODE_RES_KEY] = str(
                        detail_data[OUTPUT_RES_KEY][REGISTRANT_KEY][
                            COUNTRY_CODE_RES_KEY
                        ]
                    )
                if CITY_RES_KEY in detail_data[OUTPUT_RES_KEY][REGISTRANT_KEY]:
                    detail_data_dict[CITY_RES_KEY] = str(
                        detail_data[OUTPUT_RES_KEY][REGISTRANT_KEY][
                            CITY_RES_KEY.lower()
                        ]
                    )
                for key, value in list(
                    detail_data[OUTPUT_RES_KEY][REGISTRANT_KEY].items()
                ):
                    # enrich with the rest information (e.g. address: value)
                    detail_data_dict[key] = str(value)

        if detail_data_dict.get("success", 0) == 1:
            return Detail(detail_data, **detail_data_dict)
