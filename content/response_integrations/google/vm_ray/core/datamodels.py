from __future__ import annotations
import copy
from .UtilsManager import convert_list_to_comma_string
from .constants import (
    IOC_VERDICT_INSIGHT_COLORS,
    IOC_TYPE_MAPPING,
    IOC_TYPE_POSSIBLE_VALUES,
)
from TIPCommon import dict_to_flat, add_prefix_to_dict, flat_dict_to_csv


class BaseDataClass:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class SampleAnalyses(BaseDataClass):
    def __init__(self, raw_data, sample_id, sample_webif_url, sample_verdict):
        super(SampleAnalyses, self).__init__(raw_data)
        self.sample_id = sample_id
        self.sample_webif_url = sample_webif_url
        self.sample_verdict = sample_verdict

    def to_json(self):
        return copy.deepcopy(self.raw_data)

    def to_table(self):
        return flat_dict_to_csv(dict_to_flat(self.raw_data))

    def to_insight(
        self,
        iocs_object,
        threat_indicators,
        additional_info=False,
        ioc_types=IOC_TYPE_POSSIBLE_VALUES,
    ):
        insight = (
            f"<h2>"
            f"<strong>Verdict:&nbsp;"
            f"<span style='color: {IOC_VERDICT_INSIGHT_COLORS.get(self.raw_data.get('sample_verdict'))};'>"
            f"{self.raw_data.get('sample_verdict').title() if self.raw_data.get('sample_verdict') else ''}"
            f"</span>"
            f"</strong>"
            f"</h2>"
            f"<p>"
            f"<strong><br />"
            f"Threat Names: {convert_list_to_comma_string(self.raw_data.get('sample_threat_names'))  or 'N/A'}<br />"
            f"</strong>"
        )

        if additional_info:
            insight = (
                f"<strong>Classifications: "
                f"{convert_list_to_comma_string(self.raw_data.get('sample_classifications', [])) or 'N/A'}<br />"
                f"</strong>"
                f"<strong>Type:&nbsp;{self.raw_data.get('sample_type')}<br /></strong>"
            )

        if IOC_TYPE_MAPPING.get("files") in ioc_types:
            insight += (
                f"<strong>File IOCs:&nbsp; {len(iocs_object.ioc_files)}<br /></strong>"
            )

        if IOC_TYPE_MAPPING.get("ips") in ioc_types:
            insight += (
                f"<strong>IP IOCs:&nbsp;{len(iocs_object.ioc_ips)}<br /></strong>"
            )

        if IOC_TYPE_MAPPING.get("urls") in ioc_types:
            insight += (
                f"<strong>URL IOCs:&nbsp;{len(iocs_object.ioc_urls)}<br /></strong>"
            )

        if IOC_TYPE_MAPPING.get("domains") in ioc_types:
            insight += f"<strong>Domain IOCs:&nbsp;{len(iocs_object.ioc_domains)}<br /></strong>"

        if IOC_TYPE_MAPPING.get("mutexes") in ioc_types:
            insight += f"<strong>Mutex IOCs:&nbsp;{len(iocs_object.ioc_mutexes)}<br /></strong>"

        if IOC_TYPE_MAPPING.get("registry") in ioc_types:
            insight += f"<strong>Registry IOCs:&nbsp;{len(iocs_object.ioc_registries)}<br /></strong>"

        if IOC_TYPE_MAPPING.get("processes") in ioc_types:
            insight += (
                f"<strong>Process IOCs: {len(iocs_object.ioc_processes)}<br /></strong>"
            )

        insight += (
            f"</p>"
            f"<h2>"
            f"<strong>"
            f"<span><br />"
            f"<span>Threat Indicators</span>"
            f"</span>"
            f"</strong>"
            f"</h2>"
            f"<p>"
            f"<strong>"
            f"<span>"
        )

        for threat_indicator in threat_indicators:
            insight += (
                f"<span>{threat_indicator.category}. {threat_indicator.operation}. "
                f"{convert_list_to_comma_string(threat_indicator.classifications) or 'N/A'}<br />"
                f"</span>"
            )

        insight += "</span></strong></p>"

        return insight

    def to_enrichment_data(
        self,
        iocs_object,
        threat_indicators,
        prefix=None,
        ioc_types=IOC_TYPE_POSSIBLE_VALUES,
    ):
        data = dict_to_flat(copy.deepcopy(self.to_json()))
        data.update(
            {
                "threat_indicator_operations": convert_list_to_comma_string(
                    [
                        threat_indicator.operation
                        for threat_indicator in threat_indicators
                    ]
                )
                or "",
                "threat_indicator_category": convert_list_to_comma_string(
                    list(
                        set(
                            [
                                threat_indicator.category
                                for threat_indicator in threat_indicators
                            ]
                        )
                    )
                )
                or "",
            }
        )
        data = add_prefix_to_dict(data, prefix) if prefix else data
        data.update(iocs_object.to_enrichment_data(prefix, ioc_types))
        return data


class SampleIoc(BaseDataClass):
    def __init__(
        self,
        raw_data,
        ioc_files,
        ioc_urls,
        ioc_ips,
        ioc_registries,
        ioc_domains,
        ioc_mutexes,
        ioc_processes,
        ioc_emails,
    ):
        super(SampleIoc, self).__init__(raw_data)
        self.ioc_files = ioc_files
        self.ioc_urls = ioc_urls
        self.ioc_ips = ioc_ips
        self.ioc_registries = ioc_registries
        self.ioc_domains = ioc_domains
        self.ioc_mutexes = ioc_mutexes
        self.ioc_processes = ioc_processes
        self.ioc_emails = ioc_emails

    def to_enrichment_data(self, prefix=None, ioc_types=IOC_TYPE_POSSIBLE_VALUES):
        data = {}

        if IOC_TYPE_MAPPING.get("domains") in ioc_types:
            data["ioc_domains"] = (
                convert_list_to_comma_string(
                    [ioc_domain.domain for ioc_domain in self.ioc_domains]
                )
                or ""
            )

        if IOC_TYPE_MAPPING.get("ips") in ioc_types:
            data["ioc_ips"] = (
                convert_list_to_comma_string([ioc_ip.ip for ioc_ip in self.ioc_ips])
                or ""
            )

        if IOC_TYPE_MAPPING.get("urls") in ioc_types:
            data["ioc_urls"] = (
                convert_list_to_comma_string([ioc_url.url for ioc_url in self.ioc_urls])
                or ""
            )

        if IOC_TYPE_MAPPING.get("files") in ioc_types:
            data["ioc_files"] = (
                convert_list_to_comma_string(
                    [ioc_file.filename for ioc_file in self.ioc_files]
                )
                or ""
            )

        if IOC_TYPE_MAPPING.get("mutexes") in ioc_types:
            data["ioc_mutexes"] = (
                convert_list_to_comma_string(
                    [ioc_mutex.mutex_name for ioc_mutex in self.ioc_mutexes]
                )
                or ""
            )

        if IOC_TYPE_MAPPING.get("processes") in ioc_types:
            data["ioc_processes"] = (
                convert_list_to_comma_string(
                    [
                        convert_list_to_comma_string(ioc_process.process_names)
                        for ioc_process in self.ioc_processes
                    ]
                )
                or ""
            )

        if IOC_TYPE_MAPPING.get("registry") in ioc_types:
            data["ioc_registry"] = (
                convert_list_to_comma_string(
                    [ioc_registry.registry_key for ioc_registry in self.ioc_registries]
                )
                or ""
            )

        if IOC_TYPE_MAPPING.get("emails") in ioc_types:
            data["ioc_emails"] = (
                convert_list_to_comma_string(
                    [ioc_email.email for ioc_email in self.ioc_emails]
                )
                or ""
            )

        return add_prefix_to_dict(data, prefix) if prefix else data


class SampleIocFile(BaseDataClass):
    def __init__(
        self,
        raw_data,
        filename=None,
        severity=None,
        imp_hash=None,
        md5_hash=None,
        sha1_hash=None,
        sha256_hash=None,
        ssdeep_hash=None,
        operations=None,
        ob_id=None,
        verdict=None,
    ):
        super(SampleIocFile, self).__init__(raw_data)
        self.filename = filename
        self.severity = severity
        self.imp_hash = imp_hash
        self.md5_hash = md5_hash
        self.sha1_hash = sha1_hash
        self.sha256_hash = sha256_hash
        self.ssdeep_hash = ssdeep_hash
        self.operations = operations
        self.ob_id = ob_id
        self.verdict = verdict

    def to_dict(self):
        ret = {}
        if self.filename:
            ret["Filename"] = self.filename
        if self.severity:
            ret["Severity"] = self.severity
        if self.imp_hash:
            ret["IMP"] = self.imp_hash
        if self.md5_hash:
            ret["MD5"] = self.md5_hash
        if self.sha1_hash:
            ret["SHA1"] = self.sha1_hash
        if self.sha256_hash:
            ret["SHA256"] = self.sha256_hash
        if self.ssdeep_hash:
            ret["SSDeep"] = self.ssdeep_hash
        if self.operations:
            ret["Operations"] = self.operations
        if self.ob_id:
            ret["ID"] = self.ob_id
        return ret

    def to_table(self):
        return {
            "Filename": self.filename,
            "MD5": self.md5_hash,
            "SHA1": self.sha1_hash,
            "SHA256": self.sha256_hash,
            "Operations": self.operations,
            "Severity": self.severity,
            "Verdict": self.verdict,
        }


class SampleIocUrl(BaseDataClass):
    def __init__(self, raw_data, severity=None, ob_id=None, url=None, operations=None):
        super(SampleIocUrl, self).__init__(raw_data)
        self.operations = operations
        self.severity = severity
        self.ob_id = ob_id
        self.url = url

    def to_dict(self):
        ret = {}
        if self.operations:
            ret["Operations"] = self.operations
        if self.severity:
            ret["Severity"] = self.severity
        if self.ob_id:
            ret["ID"] = self.ob_id
        if self.url:
            ret["URL"] = self.url

        return ret

    def to_table(self):
        return {
            "URL": self.raw_data.get("url"),
            "Severity": self.raw_data.get("severity"),
            "Verdict": self.raw_data.get("verdict"),
        }


class SampleIocIP(BaseDataClass):
    def __init__(self, raw_data, ob_id=None, ip=None):
        super(SampleIocIP, self).__init__(raw_data)
        self.ob_id = (ob_id,)
        self.ip = ip

    def to_dict(self):
        ret = {}
        if self.ob_id:
            ret["ID"] = self.ob_id
        if self.ip:
            ret["IP"] = self.ip

        return ret

    def to_table(self):
        return {
            "IP": self.raw_data.get("ip_address"),
            "Severity": self.raw_data.get("severity"),
            "Verdict": self.raw_data.get("verdict"),
        }


class SampleIocRegistry(BaseDataClass):
    def __init__(
        self,
        raw_data,
        registry_key=None,
        ob_id=None,
        operations=None,
        severity=None,
        verdict=None,
    ):
        super(SampleIocRegistry, self).__init__(raw_data)
        self.registry_key = (registry_key,)
        self.ob_id = (ob_id,)
        self.operations = operations
        self.severity = severity
        self.verdict = verdict

    def to_dict(self):
        ret = {}
        if self.registry_key:
            ret["Registry Key"] = self.registry_key
        if self.ob_id:
            ret["ID"] = self.ob_id
        if self.operations:
            ret["Operations"] = self.operations

    def to_table(self):
        return {
            "Registry Key": self.registry_key,
            "Operations": self.operations,
            "Severity": self.severity,
            "Verdict": self.verdict,
        }


class SampleThreatIndicator(BaseDataClass):
    def __init__(
        self, raw_data, analysis_ids, category, operation, classifications, score
    ):
        super(SampleThreatIndicator, self).__init__(raw_data)
        self.analysis_ids = analysis_ids
        self.category = category
        self.operation = operation
        self.classifications = classifications
        self.score = score

    def to_table(self):
        return {
            "Category": self.category,
            "Operation": self.operation,
            "Score": self.score,
            "Classifications": convert_list_to_comma_string(self.classifications) or "",
        }


class SampleRes(BaseDataClass):
    def __init__(self, raw_data, samples, submissions, sample_id, sample_webif_url):
        super(SampleRes, self).__init__(raw_data)
        self.samples = samples
        self.submissions = submissions
        self.sample_id = sample_id
        self.sample_webif_url = sample_webif_url


class SampleSubmission(BaseDataClass):
    def __init__(self, raw_data, submission_id):
        super(SampleSubmission, self).__init__(raw_data)
        self.submission_id = submission_id


class SampleIocDomain(BaseDataClass):
    def __init__(self, raw_data, domain=None, severity=None, ob_id=None):
        super(SampleIocDomain, self).__init__(raw_data)
        self.domain = domain
        self.severity = severity
        self.ob_id = ob_id

    def to_dict(self):
        ret = {}
        if self.domain:
            ret["Domain"] = self.domain
        if self.severity:
            ret["Severity"] = self.severity
        if self.ob_id:
            ret["ID"] = self.ob_id

        return ret

    def to_table(self):
        return {
            "Domain": self.raw_data.get("domain"),
            "Severity": self.raw_data.get("severity"),
            "Verdict": self.raw_data.get("verdict"),
        }


class SampleIocProcess(BaseDataClass):
    def __init__(self, raw_data, process_names):
        super(SampleIocProcess, self).__init__(raw_data)
        self.process_names = process_names


class SampleIocMutex(BaseDataClass):
    def __init__(self, raw_data, mutex_name, operations, severity, verdict):
        super(SampleIocMutex, self).__init__(raw_data)
        self.mutex_name = mutex_name
        self.operations = operations
        self.severity = severity
        self.verdict = verdict

    def to_table(self):
        return {
            "Name": self.mutex_name,
            "Operations": convert_list_to_comma_string(self.operations) or "",
            "Severity": self.severity,
            "Verdict": self.verdict,
        }


class SampleIocEmail(BaseDataClass):
    def __init__(self, raw_data, email):
        super(SampleIocEmail, self).__init__(raw_data)
        self.email = email


class Sample(BaseDataClass):
    def __init__(self, raw_data, sample_id, job_id):
        super(Sample, self).__init__(raw_data)
        self.sample_id = sample_id
        self.job_id = job_id
