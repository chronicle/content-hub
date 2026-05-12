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

# ==============================================================================
# title           : WildfireManager.py
# description     : This Module contains all Wildfire API operations functionality
# author          : avital@siemplify.co
# date            : 21-02-18
# python_version  : 2.7
# libraries       : pan-python xmltodict
# requirements    :
# product_version : 1.0
# ==============================================================================


# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import pan.wfapi
import xmltodict

# =====================================
#              CONSTS                 #
# =====================================

TEST_URLS = [r"http://paloaltonetworks.com", r"http://www.google.com"]
NOT_FOUND = "HTTP Error 404: Not Found"


# =====================================
#              CLASSES                #
# =====================================


class WildfireManagerError(Exception):
    """
    General Exception for Wildfire manager
    """

    pass


class WildfireManager:
    """
    Responsible for all Wildfire operations functionality
    """

    def __init__(self, api_key):
        # Initialize WF API object
        try:
            self.wfapi = pan.wfapi.PanWFapi(tag="wildfire", api_key=api_key)
        except pan.wfapi.PanWFapiError as e:
            raise WildfireManagerError(f"Unable to connect: {e}")

    def test_connectivity(self):
        """
        Validates connectivity to Wildfire
        :return: bool
        """
        self.wfapi.submit(links=TEST_URLS)
        return True

    def submit_file(self, file_path):
        """
        Submit a file to Wildfire
        :param str file_path: absolute or relative to the script path to file
        :return: {dict} file info
        """

        try:
            self.wfapi.submit(file=file_path)
            response = xmltodict.parse(self.wfapi.response_body)
            return response["wildfire"]["upload-file-info"]

        except Exception as e:
            raise WildfireManagerError(f"Unable to submit file {file_path}:\n{e}")

    def get_sample(self, hash):
        """
        Get a sample of a hash.
        :param str hash: hash of a file
        :return: {dict} sample name and content (pdf)
        """

        try:
            self.wfapi.sample(hash=hash)
            return self.wfapi.attachment

        except pan.wfapi.PanWFapiError as e:
            if e == NOT_FOUND:
                raise WildfireManagerError(f"Sample is not available for {hash}")
            raise

        except Exception as e:
            raise WildfireManagerError(f"Unable to get sample of {hash}:\n{e}")

    def get_report(self, hash):
        """
        Get a report of a hash.
        :param str hash: hash of a file
        :return: {dict} report
        """

        try:
            self.wfapi.report(hash=hash, format="xml")
            response = xmltodict.parse(self.wfapi.response_body)
            # Return dict (the response is OrderedDict)
            return dict(response["wildfire"])

        except pan.wfapi.PanWFapiError as e:
            if e == NOT_FOUND:
                raise WildfireManagerError(f"PDF report is not available for {hash}")
            raise

        except Exception as e:
            raise WildfireManagerError(f"Unable to get report for {hash}:\n{e}")

    def get_pdf_report(self, hash):
        """
        Get a PDF report of a hash.
        :param str hash: hash of a file
        :return: {dict} report name and content (pdf)
        """

        try:
            self.wfapi.report(hash=hash, format="pdf")
            return self.wfapi.attachment

        except pan.wfapi.PanWFapiError as e:
            if e == NOT_FOUND:
                raise WildfireManagerError(f"PDF report is not available for {hash}")
            raise

        except Exception as e:
            raise WildfireManagerError(f"Unable to get report for {hash}:\n{e}")

    def get_pcap(self, hash):
        """
        Retrieve PCAP of a previously submitted file using it's hash
        :param str hash: hash of a file
        :return: {dict} report name and content (pcap)
        """

        try:
            self.wfapi.pcap(hash)
            return self.wfapi.attachment

        except pan.wfapi.PanWFapiError as e:
            if e == NOT_FOUND:
                raise WildfireManagerError(f"PCAP is not available for {hash}")
            raise

        except Exception as e:
            raise WildfireManagerError(f"Unable to get PCAP for {hash}:\n{e}\n")
