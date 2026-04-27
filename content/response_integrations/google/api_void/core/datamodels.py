from __future__ import annotations
from copy import deepcopy
from TIPCommon import dict_to_flat


class Reputation:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def as_enrichment_data(self):
        """
        Get the domain reputation data as enrichment data
        :return: {dict} The enrichment data
        """
        return self.raw_data

    def as_json(self):
        """
        Get the data represented as json
        :return: {dict} The data as json
        """
        temp_data = deepcopy(self.raw_data)
        temp_data["blacklists"]["engines"] = self.get_blacklist_report()
        return temp_data

    def get_blacklist_report(self):
        """
        Create a blacklist report dict from the domain reputation data
        :return: {dict} Blacklist report
        """
        blacklist_report = []
        temp_data = deepcopy(self.raw_data)

        for engine in list(temp_data.get("blacklists", {}).get("engines", {}).values()):
            if "elapsed" in engine:
                # Elapsed - How long it took to get the data.
                # This is not important data - remove it.
                del engine["elapsed"]

            blacklist_report.append(engine)

        return blacklist_report


class IPReputation(Reputation):
    def as_enrichment_data(self):
        """
        Get the ip reputation data as enrichment data
        :return: {dict} The enrichment data
        """
        temp_data = deepcopy(self.raw_data)
        enrichment_data = temp_data.get("information", {})
        enrichment_data.update(temp_data.get("anonymity", {}))
        enrichment_data["detections"] = temp_data.get("blacklists", {}).get(
            "detections"
        )
        enrichment_data["detection_rate"] = temp_data.get("blacklists", {}).get(
            "detection_rate"
        )
        enrichment_data["engines_count"] = temp_data.get("blacklists", {}).get(
            "engines_count"
        )
        return enrichment_data


class URLReputation(Reputation):
    def as_enrichment_data(self):
        """
        Get the url reputation data as enrichment data
        :return: {dict} The enrichment data
        """
        enrichment_data = {
            "risk_score": self.raw_data.get("risk_score", {}).get("result"),
            "is_external_redirect": self.raw_data.get("security_checks", {}).get(
                "is_external_redirect"
            ),
            "is_risky_geo_location": self.raw_data.get("security_checks", {}).get(
                "is_risky_geo_location"
            ),
            "is_suspicious_domain": self.raw_data.get("security_checks", {}).get(
                "is_suspicious_domain"
            ),
            "geo_location": self.raw_data.get("geo_location", {}).get("countries", []),
        }
        return dict_to_flat(enrichment_data)

    @property
    def risk_score(self):
        return int(self.raw_data.get("risk_score", {}).get("result", 0))

    def get_blacklist_report(self):
        """
        Create a blacklist report dict from the url reputation data
        :return: {dict} Blacklist report
        """
        blacklist_report = []
        temp_data = deepcopy(self.raw_data)

        for engine in temp_data.get("domain_blacklist", {}).get("engines", []):
            if "elapsed" in engine:
                # Elapsed - How long it took to get the data.
                # This is not important data - remove it.
                del engine["elapsed"]

            blacklist_report.append(engine)

        return blacklist_report

    def as_json(self):
        """
        Get the data represented as json
        :return: {dict} The data as json
        """
        temp_data = deepcopy(self.raw_data)
        temp_data["domain_blacklist"]["engines"] = self.get_blacklist_report()
        return temp_data


class DomainReputation(Reputation):
    def as_enrichment_data(self):
        """
        Get the domain reputation data as enrichment data
        :return: {dict} The enrichment data
        """
        enrichment_data = deepcopy(self.raw_data)
        enrichment_data.pop("blacklists")
        server_info = enrichment_data.pop("server")
        enrichment_data.update(server_info)
        return enrichment_data


class Screenshot:
    def __init__(
        self,
        raw_data,
        format=None,
        base64_file=None,
        image_width=None,
        image_height=None,
        file_size_bytes=None,
        file_md5_hash=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.file_format = format
        self.base64_file = base64_file
        self.image_height = image_height
        self.image_width = image_width
        self.file_size_bytes = file_size_bytes
        self.file_md5_hash = file_md5_hash


class EmailInformation:
    def __init__(
        self,
        raw_data,
        suspicious_domain=None,
        should_block=None,
        score=None,
        disposable=None,
        has_spf_records=None,
        has_mx_records=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.suspicious_domain = suspicious_domain
        self.should_block = should_block
        self.score = score
        self.disposable = disposable
        self.has_mx_records = has_mx_records
        self.has_spf_records = has_spf_records

    def as_csv(self):
        return {
            key.replace("_", " ").capitalize(): value
            for key, value in list(self.raw_data.items())
        }

    def as_enrichment_data(self):
        """
        Get the email information data as enrichment data
        :return: {dict} The enrichment data
        """
        enrichment_data = {
            "suspicious_domain": self.suspicious_domain,
            "should_block": self.should_block,
            "score": self.score,
            "has_mx_records": self.has_mx_records,
            "has_spf_records": self.has_spf_records,
        }
        return dict_to_flat(enrichment_data)
