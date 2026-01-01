from __future__ import annotations


class IP:
    """IP dataclass"""

    def __init__(
        self,
        raw_data=None,
        isPublic=None,
        ipVersion=None,
        isAllowlisted=None,
        abuseConfidenceScore=None,
        countryCode=None,
        countryName=None,
        usageType=None,
        isp=None,
        domain=None,
        hostnames=None,
        totalReports=None,
        numDistinctUsers=None,
        lastReportedAt=None,
        reports=None,
    ):
        self.raw_data = raw_data
        self.isPublic = isPublic
        self.ipVersion = ipVersion
        self.isAllowlisted = isAllowlisted
        self.abuseConfidenceScore = abuseConfidenceScore
        self.countryCode = countryCode
        self.countryName = countryName
        self.usageType = usageType
        self.isp = isp
        self.domain = domain
        self.hostnames = hostnames
        self.totalReports = totalReports
        self.numDistinctUsers = numDistinctUsers
        self.lastReportedAt = lastReportedAt
        self.reports = reports

    def to_enrichment_data(self):
        return {
            "countryName": self.countryName,
            "abuseConfidenceScore": self.abuseConfidenceScore,
            "domain": self.domain,
        }

    def to_json(self):
        return self.raw_data
