# ==============================================================================
# title           :MalShareManager.py
# description     :This Module contain all MalShare operations functionality
# author          :zivh@siemplify.co
# date            :05-15-18
# python_version  :2.7
# libraries       :
# requirements    :
# product_version :v1
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests

# =====================================
#             CONSTANTS               #
# =====================================
API_URL = "https://malshare.com/api.php?api_key={0}&action={1}"

# =====================================
#              CLASSES                #
# =====================================


class MalShareError(Exception):
    """
    General Exception for MalShare manager
    """

    pass


class MalShareManager:
    """
    Responsible for all MalShare operations functionality
    """

    def __init__(self, api_key, use_ssl):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.verify = use_ssl

    def test_connectivity(self):
        """
        Validates connectivity by list hashes from the past 24 hours
        :return: {boolean} True/False
        """
        res = self.session.get(API_URL.format(self.api_key, "getlist"))
        self.validate_response(res, "testing")
        return True

    def upload_and_scan(self, file_path):
        """
         Submit URLs for scanning.
        :param file_path: {string} full file path for submit
        :return: {Json} stored file details if success
        """
        url = API_URL.format(self.api_key, "upload")
        file_path_raw_string = file_path.encode("string-escape")
        files = {"file": open(file_path_raw_string, "rb")}
        response = self.session.post(url, files=files)
        self.validate_response(response, file_path)
        if "Success" in response.content:
            file_hash = response.content.split(" - ")[-1]
            # TODO: search_hash returns even if the file is pending analysis.
            # Because upload action remains in pending status long time
            # TODO: In future - Find a way to wait for analysis completion
            return self.search_hash(file_hash)

    def search_hash(self, hash_sample):
        """
        Get stored file details
        :param hash_sample: {string}
        :return: {Json} search results
        """
        url = API_URL.format(self.api_key, f"details&hash={hash_sample}")
        response = self.session.get(url)
        self.validate_response(response, hash_sample)
        return response.json()

    def validate_response(self, response, search_for):
        """
        Check if request response is ok
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise MalShareError(
                f"An error occurred while trying to search for {search_for}. ERROR: {e}. {response.content}"
            )


if __name__ == "__main__":

    # malshare = MalShareManager('7935224e29efc23d9cb4c991d51d66e0e6ea4c96aa145f3a713dd2b22c224d40', False)

    # is_connected = malshare.test_connectivity()

    # Scan
    # scan_res = malshare.search_hash('9e0e9014a11cc149174d0b306f2ac698')

    # Upload file
    # res = malshare.upload_and_scan("C:\Users\zivh.SIEMPLIFY\Desktop\Ziv\Result.py")

    pass
