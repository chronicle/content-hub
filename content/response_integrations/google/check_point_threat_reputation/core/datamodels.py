from __future__ import annotations
from TIPCommon import dict_to_flat
import json


class ReputationClassification:
    """
    Base API response reputation classification data model
    """

    def __init__(self, classification=None, severity=None, confidence=None):
        self.classification = classification
        self.severity = severity
        self.confidence = confidence

    def to_dict(self):
        return {
            "classification": self.classification,
            "severity": self.severity,
            "confidence": self.confidence,
        }


class ReputationContext:
    """
    Base API response context data model
    """

    class Location:
        def __init__(
            self,
            countryCode=None,
            countryName=None,
            region=None,
            city=None,
            postalCode=None,
            latitude=None,
            longitude=None,
            dma_code=None,
            area_code=None,
            metro_code=None,
        ):
            self.countryCode = countryCode
            self.countryName = countryName
            self.region = region
            self.city = city
            self.postalCode = postalCode
            self.latitude = latitude
            self.longitude = longitude
            self.dma_code = dma_code
            self.area_code = area_code
            self.metro_code = metro_code

        def to_dict(self):
            return {
                "countryCode": self.countryCode,
                "countryName": self.countryName,
                "region": self.region,
                "city": self.city,
                "postalCode": self.postalCode,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "dma_code": self.dma_code,
                "area_code": self.area_code,
                "metro_code": self.metro_code,
            }

    class MetaData:
        def __init__(
            self,
            company_name=None,
            product_name=None,
            copyright=None,
            original_name=None,
        ):
            self.company_name = company_name
            self.product_name = product_name
            self.copyright = copyright
            self.original_name = original_name

        def to_dict(self):
            return {
                "company_name": self.company_name,
                "product_name": self.product_name,
                "copyright": self.copyright,
                "original_name": self.original_name,
            }

    DATE_FORMATTING = "%Y:%m:%d %H:%M:%S"  # creation date formatting

    def __init__(
        self,
        raw_data=None,
        asn=None,
        as_owner=None,
        safe=None,
        malware_family=None,
        protection_name=None,
        redirections=None,
        malware_types=None,
        categories=None,
        location=None,
        indications=None,
        vt_positives=None,
        alexa_rank=None,
        creation_date=None,
        meta_data=None,
    ):
        self.raw_data = raw_data
        self.asn = asn
        self.as_owner = as_owner
        self.safe = safe
        self.malware_family = malware_family
        self.protection_name = protection_name
        self.redirections = redirections
        self.malware_types = malware_types  # list
        self.categories = categories  # list of dictionaries
        if location:
            self.location = self.Location(
                countryCode=location.get("countryCode"),
                countryName=location.get("countryName"),
                region=location.get("region"),
                city=location.get("city"),
                postalCode=location.get("postalCode"),
                latitude=location.get("latitude"),
                longitude=location.get("longitude"),
                dma_code=location.get("dma_code"),
                area_code=location.get("area_code"),
                metro_code=location.get("metro_code"),
            )
        else:
            self.location = self.Location()
        self.indications = indications
        self.vt_positives = vt_positives
        self.alexa_rank = alexa_rank
        self.creation_date = creation_date
        if meta_data:
            self.meta_data = self.MetaData(
                company_name=meta_data.get("company_name"),
                product_name=meta_data.get("product_name"),
                copyright=meta_data.get("copyright"),
                original_name=meta_data.get("original_name"),
            )
        else:
            self.meta_data = self.MetaData()

    def to_dict(self):
        ## take only non None keys
        return {
            "asn": self.asn,
            "as_owner": self.as_owner,
            "safe": self.safe,
            "malware_family": self.malware_family,
            "protection_name": self.protection_name,
            "redirections": self.redirections if self.redirections else None,
            "malware_types": self.malware_types if self.malware_types else None,
            "categories": self.categories if self.malware_types else None,
            ## TODO - check this
            "location": self.location.to_dict(),
            "indications": self.indications,
            "vt_positives": self.vt_positives,
            "alexa_rank": self.alexa_rank,
            "creation_date": self.creation_date,
            "meta_data": (
                self.meta_data.to_dict() if self.meta_data is not None else None
            ),
        }


class ReputationResponseModel:
    """
    Base API response data model
    """

    def __init__(
        self,
        raw_data=None,
        resource=None,
        risk=None,
        reputation_classification=None,
        reputation_context=None,
    ):
        """
        :param raw_data: raw api response as json
        :param resource: the 'resource' in the API response (IP/HOST/FILE_HASH)
        :param risk: the 'risk' in the API response
        :param reputation_classification: the 'reputation' in the API response
        :param reputation_context:  the 'context' in the API response
        """
        self.raw_data = raw_data
        self.resource = resource
        self.risk = risk
        self.reputation_classification = reputation_classification
        self.reputation_context = reputation_context

    def as_insight(self):
        """
        :return: reputation insight message as string
        """
        return f""" Classification: {self.reputation_classification.classification} \n
                    Confidence: {self.reputation_classification.confidence} \n
                    Severity: {self.reputation_classification.severity} \n
                    Risk: {self.risk} 
                """

    def enriched_data_to_dict(self):
        """
        :return: enriched data as dictionary (not necessarily flatted)
        """
        return {
            "resource": self.resource,
            "risk": self.risk,
            "reputation": dict_to_flat(self.reputation_classification.to_dict()),
            "context": dict_to_flat(self.reputation_context.to_dict()),
        }

    def enriched_data_to_flatted_dict(self):
        """
        :return: enriched data as flatted dict
        """
        return dict_to_flat(self.enriched_data_to_dict())

    def raw_response_to_flatted_dict(self):
        """
        returns raw_data parameter as flatted dictionary
        :return:
        """
        return dict_to_flat(self.raw_data)

    @property
    def raw_response_without_status(self):
        raw_data_without_status = self.raw_data.copy()
        raw_data_without_status.pop("status")
        return raw_data_without_status


class IPReputationModel(ReputationResponseModel):
    def to_csv(self):
        """
        :return: csv table of ip reputation data
        """
        return {
            "Classification": self.reputation_classification.classification,
            "Confidence": self.reputation_classification.confidence,
            "Severity": self.reputation_classification.severity,
            "Risk": self.risk,
            "Country Code": self.reputation_context.location.countryCode,
            "Country": self.reputation_context.location.countryName,
            "Region": self.reputation_context.location.region,
            "City": self.reputation_context.location.city,
            "Postal Code": self.reputation_context.location.postalCode,
            "Latitude": self.reputation_context.location.latitude,
            "Longitude": self.reputation_context.location.longitude,
            "DMA Code": self.reputation_context.location.dma_code,
            "Area Code": self.reputation_context.location.area_code,
            "Metro Code": self.reputation_context.location.metro_code,
            "ASN": self.reputation_context.asn,
            "Owner": self.reputation_context.as_owner,
        }


class FileHashReputationModel(ReputationResponseModel):
    def to_csv(self):
        """
        :return: csv table of file hash reputation data
        """
        return {
            "Classification": self.reputation_classification.classification,
            "Confidence": self.reputation_classification.confidence,
            "Severity": self.reputation_classification.severity,
            "Risk": self.risk,
            "Malware Family": self.reputation_context.malware_family,
            "File Name": self.reputation_context.protection_name,
            "Malware Type": (
                " ".join(self.reputation_context.malware_types)
                if self.reputation_context.malware_types
                else None
            ),
            "Company Name": self.reputation_context.meta_data.company_name,
            "Product Name": self.reputation_context.meta_data.product_name,
            "Copyright": self.reputation_context.meta_data.copyright,
            "Original File Name": self.reputation_context.meta_data.original_name,
        }


class HostReputationModel(ReputationResponseModel):
    def to_csv(self):
        """
        returns csv table of host data
        :return:
        """
        return {
            "Classification": self.reputation_classification.classification,
            "Confidence": self.reputation_classification.confidence,
            "Severity": self.reputation_classification.severity,
            "Risk": self.risk,
            "Categories": (
                " ".join(
                    [
                        json.dumps(category)
                        for category in self.reputation_context.categories
                    ]
                )
                if self.reputation_context.categories
                else None
            ),
            "Indications": (
                " ".join(self.reputation_context.indications)
                if self.reputation_context.indications
                else None
            ),
            "Virus Total Positives Count": self.reputation_context.vt_positives,
            "Alexa Rank": self.reputation_context.alexa_rank,
            "Safe?": self.reputation_context.safe,
            "Creation Date": self.reputation_context.creation_date,
        }
