# coding=utf-8
# ==============================================================================
# title           :AlexaManager.py
# description     :This Module contain all Alexa cloud operations functionality
# author          :zdemoniac@gmail.com
# date            :12-26-17
# python_version  :2.7
# libraries       : copy, datetime, hashlib, hmac, requests, urllib, xml
# requirements    :
# product_version :
# ==============================================================================

# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
import hmac
import hashlib
import urllib.parse
from copy import copy
from datetime import datetime
from urllib.parse import urlencode
import defusedxml.ElementTree as ET


# =====================================
#              CLASSES                #
# =====================================
class AlexaManagerError(Exception):
    """
    General Exception for Alexa manager
    """

    pass


class AlexaManager:
    """
    Responsible for all Alexa cloud operations functionality
    """

    def __init__(self, access_key_id, secret_access_key):
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._ns_ats = {"aws": "http://ats.amazonaws.com/doc/2005-07-11"}
        self._ns_awis = {"aws": "http://awis.amazonaws.com/doc/2005-07-11"}
        self._ns_err = {"aws": "http://alexa.amazonaws.com/doc/2005-10-05/"}
        self._service_region = "us-west-1"
        self._service_endpoint_top_sites = "ats.us-west-1.amazonaws.com"
        self._service_endpoint_awis = "awis.us-west-1.amazonaws.com"
        self._service_name_top_sites = "AlexaTopSites"
        self._service_name_awis = "awis"

    def test_connectivity(self):
        """
        Validates connectivity
        :return: {boolean} True/False
        """
        try:
            res = self.get_url_info("google.co.il", "Rank")
        except Exception as error:
            raise AlexaManagerError(f"test_connectivity Error: ({error})")
        return True

    def get_url_info(self, url, response_group):
        """
        Query Alexa for URL information
        (see http://docs.aws.amazon.com/AlexaWebInfoService/latest/ApiReference_UrlInfoAction.html for response groups)
        :param url: {string} URL of the site
        :param response_group: {string} set group of the retrieving information
        :return: {dict} URL information such as: how popular the site is, what sites are related
        """

        if url.startswith("HTTP"):
            split_url = urllib.parse.urlsplit(url)
            url = f"{split_url.netloc}/{split_url.path}"

        params = [
            ("Action", "UrlInfo"),
            ("ResponseGroup", response_group),
            ("Url", url),
        ]

        req = self._prepare_request(
            params, self._service_endpoint_awis, self._service_name_awis
        )
        request = requests.get(req["url"], headers=req["headers"])
        response = request.text
        root = ET.fromstring(response)
        # root = ET.parse("test_UrlInfo2.xml").getroot() # for testing
        self._check_response_status(root, self._ns_awis)
        alexa_xml = root.findall(".//aws:Alexa", namespaces=self._ns_awis)
        self._remove_xml_namespace(alexa_xml[0], self._ns_awis["aws"])
        return self._dictify(alexa_xml[0], False)

    def top_sites(self, number, country_code, start=1):
        """
        Query Alexa for top sites
        :param number: {int} number of sites to show
        :param country_code: {string} code of the country
        :param start {int} number to start from
        :return: {dict} sites list
        """
        params = [
            ("Action", "TopSites"),
            ("Count", number),
            ("CountryCode", country_code),
            ("ResponseGroup", "Country"),
            ("Start", start),
        ]
        req = self._prepare_request(
            params, self._service_endpoint_top_sites, self._service_name_top_sites
        )
        request = requests.get(req["url"], headers=req["headers"])
        response = request.text
        root = ET.fromstring(response)
        # root = ET.parse("test_TopSites.xml").getroot() # for testing
        self._check_response_status(root, self._ns_ats)
        xml_sites = root.findall(".//aws:Site", namespaces=self._ns_ats)
        sites = {}
        for site in xml_sites:
            url = site.find(".//aws:DataUrl", namespaces=self._ns_ats).text
            sites[url] = {
                "Rank": site.find(".//aws:Rank", namespaces=self._ns_ats).text,
                "ReachPerMillion": site.find(
                    ".//aws:Reach/aws:PerMillion", namespaces=self._ns_ats
                ).text,
                "PageViewsPerMillion": site.find(
                    ".//aws:PageViews/aws:PerMillion", namespaces=self._ns_ats
                ).text,
                "PageViewsPerUser": site.find(
                    ".//aws:PageViews/aws:PerUser", namespaces=self._ns_ats
                ).text,
            }
        return sites

    def _prepare_request(self, params, service_endpoint, service_name):
        canonical_query = urlencode(params)
        amz_date = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        date_stamp = datetime.utcnow().strftime("%Y%m%d")
        canonical_headers = (
            "host:" + service_endpoint + "\nx-amz-date:" + amz_date + "\n"
        )
        signed_headers = "host;x-amz-date"
        payload_hash = hashlib.sha256("".encode("utf-8")).hexdigest()
        canonical_request = (
            "GET\n/api\n"
            + canonical_query
            + "\n"
            + canonical_headers
            + "\n"
            + signed_headers
            + "\n"
            + payload_hash
        )
        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = (
            date_stamp
            + "/"
            + self._service_region
            + "/"
            + service_name
            + "/"
            + "aws4_request"
        )
        string_to_sign = (
            algorithm
            + "\n"
            + amz_date
            + "\n"
            + credential_scope
            + "\n"
            + hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        )
        signing_key = self._getSignatureKey(date_stamp, service_name)
        signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        authorization_header = (
            algorithm
            + " Credential="
            + self._access_key_id
            + "/"
            + credential_scope
            + ", SignedHeaders="
            + signed_headers
            + ", Signature="
            + signature
        )

        url = "https://" + service_endpoint + "/api?" + canonical_query

        headers = {
            "Accept": "application/xml",
            "Content-Type": "application/xml",
            "X-Amz-Date": amz_date,
            "Authorization": authorization_header,
        }
        return {"url": url, "headers": headers}

    def _sign(self, key, msg):
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def _getSignatureKey(self, date, service_name):
        k_date = self._sign(("AWS4" + self._secret_access_key).encode("utf-8"), date)
        k_region = self._sign(k_date, self._service_region)
        k_service = self._sign(k_region, service_name)
        k_signing = self._sign(k_service, "aws4_request")
        return k_signing

    def _check_response_status(self, xml_root, ns):
        """Parse response xml and check status"""
        status = xml_root.find(".//aws:StatusCode", namespaces=self._ns_err)
        if status is not None and "Success" in status.text:
            return True
        else:
            raise AlexaManagerError(
                f"Request Error: ({xml_root.find('.//aws:ErrorCode', namespaces=ns).text})"
            )

    def _remove_xml_namespace(self, doc, namespace):
        """Remove namespace in the passed xml document in place."""
        ns = f"{{{namespace}}}"
        nsl = len(ns)
        for elem in doc.getiterator():
            if elem.tag.startswith(ns):
                elem.tag = elem.tag[nsl:]

    def _dictify(self, r, root=True):
        """
        Convert xml document (or xml node if root=False) to dictionary.
        :param r: {xml.etree.ElementTree} input xml
        :param root: {boolean} is it xml root?
        :return: {dict} resulting dictionary
        """
        if root:
            return {r.tag: self._dictify(r, False)}
        d = copy(r.attrib)
        if r.text:
            d["text"] = r.text
        for x in r.findall("./*"):
            if x.tag not in d:
                d[x.tag] = []
            d[x.tag].append(self._dictify(x, False))
        return d
