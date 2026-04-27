# ============================================================================#
# title           :VirusTotalParser.py
# description     :This Module contains the VirusTotalParser from the raw data based on the data models
# author          :gegham.jivanyan@siemplify.co
# date            :13-12-2019
# python_version  :2.7
# libraries       :
# requirements    :
# product_version :
# ============================================================================#


# ============================= IMPORTS ===================================== #


from __future__ import annotations
from .datamodels import IP, Domain, URL, HASH, Comment


# ============================= CLASSES ===================================== #


#
class VirusTotalParserError(Exception):
    """
    General Exception for VirusTotalParser class.
    """

    pass


#
class VirusTotalParser:
    """
    VirusTotalParser class.
    Build objects of classes defined in data models.
    """

    #
    def __init__(self, siemplify_logger=None):
        self.siemplify_logger = siemplify_logger

    #
    @staticmethod
    def build_ip_address_object(report):
        """
        Build IP address object.
        :param report: {dict} report with ip address information
        :return: IP object
        """
        return IP(
            raw_data=report,
            asn=report.get("asn"),
            country=report.get("country"),
            positives=VirusTotalParser.__get_max_of_positives(report),
            resolutions=report.get("resolutions"),
            detected_urls=report.get("detected_urls"),
            detected_downloaded_samples=report.get("detected_downloaded_samples", []),
            detected_referrer_samples=report.get("detected_referrer_samples", []),
            detected_communicating_samples=report.get(
                "detected_communicating_samples", []
            ),
            undetected_urls=report.get("undetected_urls"),
            undetected_downloaded_samples=report.get("undetected_downloaded_samples"),
        )

    @staticmethod
    def __get_max_of_positives(report):
        mixed_data = (
            report.get("detected_urls", [])
            + report.get("detected_downloaded_samples", [])
            + report.get("detected_referrer_samples", [])
            + report.get("detected_communicating_samples", [])
        )
        positives = [item.get("positives", 0) for item in mixed_data]

        return max(positives) if positives else 0

    #
    @staticmethod
    def build_url_object(report):
        """
        Build URL object.
        :param report: {dict} report with url information
        :return: URL object
        """
        return URL(
            raw_data=report,
            scan_id=report.get("scan_id"),
            scan_date=report.get("scan_date"),
            url=report.get("url"),
            permalink=report.get("permalink"),
            total=report.get("total"),
            positives=report.get("positives"),
            scans=report.get("scans"),
            response_code=report.get("response_code"),
            first_seen=report.get("first_seen"),
            last_seen=report.get("last_seen"),
            resource=report.get("resource"),
        )

    #
    @staticmethod
    def build_hash_object(report):
        """
        Build Hash object.
        :param report: {dict} report with hash information
        :return: HASH object
        """
        return HASH(
            raw_data=report,
            response_code=report.get("response_code"),
            md5=report.get("md5"),
            sha1=report.get("sha1"),
            scan_id=report.get("scan_id"),
            scan_date=report.get("scan_date"),
            permalink=report.get("permalink"),
            positives=report.get("positives"),
            total=report.get("total"),
            scans=report.get("scans"),
            resource=report.get("resource"),
            sha256=report.get("sha256"),
            ssdeep=report.get("ssdeep"),
            authentihash=report.get("authentihash"),
            type=report.get("type"),
            imphash=report.get("additional_info", {}).get("pe-imphash"),
            size=report.get("size"),
            magic=report.get("additional_info", {}).get("magic"),
            tags=report.get("tags"),
            first_seen=report.get("first_seen"),
            last_seen=report.get("last_seen"),
            submission_names=report.get("submission_names"),
        )

    @staticmethod
    def build_comment_object(comment):
        """
        Build Hash object.
        :param report: {dict} report with hash information
        :return: HASH object
        """
        return Comment(
            raw_data=comment, date=comment.get("date"), comment=comment.get("comment")
        )

    #
    @staticmethod
    def build_domain_object(report):
        """
        Build Domain object.
        :param report: {dict} report with domain information
        :return: Domain object
        """

        return Domain(
            raw_data=report,
            undetected_referrer_samples=report.get("undetected_referrer_samples"),
            whois_timestamp=report.get("whois_timestamp"),
            detected_referrer_samples=report.get("detected_referrer_samples"),
            resolutions=report.get("resolutions"),
            subdomains=report.get("subdomains"),
            categories=report.get("categories"),
            domain_siblings=report.get("domain_siblings"),
            undetected_urls=report.get("undetected_urls"),
            detected_urls=report.get("detected_urls"),
            bitdefender_category=report.get("bitdefender_category"),
            forcepoint_threatseeker_category=report.get(
                "forcepoint_threatseeker_category"
            ),
            alexa_category=report.get("alexa_category"),
            alexa_domain_info=report.get("alexa_domain_info"),
            bitdefender_domain_info=report.get("bitdefender_domain_info"),
        )

    #
    @staticmethod
    def get_scan_id(report):
        """
        return scan_id from response.
        :param report: {dict} report with domain information
        :return: scan_id
        """
        return report.get("scan_id")
