# coding=utf-8
# ==============================================================================
# title           :TitaniumCloudC.py
# description     :Malware presence provides malware status of the sample. Status can be: malicious, suspicious, known
#                  and unknown. Service supports single or bulk queries, with extended option for response data (trust
#                  factor, threat level, ...).
# author          :vlads@siemplify.co
# date            :01-23-18
# python_version  :2.7
# libraries       :
# requirements    :access to WAN
# product_version :1.0.0
# ==============================================================================


# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import base64
import requests
import hashid

# =====================================
#             CONSTANTS               #
# =====================================
EXAMPLE_OF_SINGLE_QUERY = {
    "rl": {
        "malware_presence": {
            "status": "KNOWN",
            "query_hash": {"sha1|md5|sha256": "hash_value"},
        }
    }
}

MD5 = "md5"
SHA1 = "sha1"
SHA256 = "sha256"
SHA512 = "sha512"

# Malware presence status is labeled as follows:
# - UNKNOWN - the service couldn’t find the hash queries
# - KNOWN - this sample is presumed to be benign by ReversingLabs: it does not have any
# trustworthy AV detections and it does not match any of our internal signatures. We recommend the
# users check the trust factor: if it is lowest (meaning 5) it may be worthwhile checking what other AV
# vendors say (using our XREF API) and if scan record is not recent, triggering a rescan (using our
# re-scan API).
# - SUSPICIOUS - this sample is suspected to be suspicious
# - MALICIOUS- this sample is labeled as malicious

# =====================================
#              CLASSES                #
# =====================================


class TitaniumCloudException(Exception):
    """
    General Exception for TitaniumCloud CLI
    """

    pass


class TitaniumCloudClient:
    """
    TitaniumCloud CLI functions
    """

    def __init__(self, host, username, password):
        self.host = host
        self.headers = self._generate_headers(username, password)

    @staticmethod
    def _generate_headers(username, password):
        auth_str = f"{username}:{password}"
        auth = base64.b64encode(auth_str.encode())

        headers = {"Authorization": f"Basic {auth}"}

        return headers

    def test_connectivity(self):
        """
        Validates connectivity
        :return: {boolean} True/False
        """
        md5_string = "2d5e8e75c5b4477f6db75c10c0452491"
        r = self.single_query(md5_string, "md5")
        if r:
            return True
        raise TitaniumCloudException(
            f"Error: Not able to find data for md5 '{md5_string}'."
        )

    def get_type_of_hash(self, hash_id):
        """
        Get type of hash for single query
        :param hash_id: {string}
        :return: {string} Type of hash
        """
        hash_object = hashid.HashID()
        prop = hash_object.identifyHash(hash_id)
        for i in prop:
            type_of_hash = i[0]
            if "SHA-1" in type_of_hash:
                return SHA1
            elif "MD" in type_of_hash:
                return MD5
            elif "256" in type_of_hash:
                return SHA256
            elif "512" in type_of_hash:
                return SHA512
        # In case no familiar hash type was found
        return None

    def single_query(self, hash_value, hash_type, extended=False):
        """
        This query returns a document containing malware status for the given sample.
        :param hash_value:
        :param hash_type: sha1|md5|sha256
        :param extended: True or False
        :return:
        """
        http_get_variables = "?format=json"
        if extended:
            http_get_variables += "&extended=true"

        url = f"{self.host}/api/databrowser/malware_presence/query/{hash_type}/{hash_value}{http_get_variables}"

        response = requests.get(url, headers=self.headers)

        try:
            response.raise_for_status()
        except Exception as error:
            raise TitaniumCloudException(f"Error: {error} - {response.text}")

        return response.json()

    def bulk_query(self, hashes, hash_type, extended=False):
        """
        Bulk query will retrieve documents with the same format single sample query retrieves, but for multiple
        hashes in single response. There are also additional document elements describing ill-formatted hashes
        and hashes not found by the service.
        :param hashes: Array of hashes
        :param hash_type: sha1|md5|sha256
        :param extended:
        :return:
        """
        post_data = {"rl": {"query": {"hash_type": hash_type, "hashes": hashes}}}

        http_get_variables = "?format=json"
        if extended:
            http_get_variables += "&extended=true"

        url = f"{self.host}/api/databrowser/malware_presence/bulk_query/json{http_get_variables}"
        response = requests.post(url, json=post_data, headers=self.headers)

        try:
            response.raise_for_status()
        except Exception as error:
            raise TitaniumCloudException(f"Error: {error} - {response.text}")

        return response.json()
