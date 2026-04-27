from __future__ import annotations
from . import datamodels


class VMRayParser:
    @staticmethod
    def build_sample_analyses_object(sample_analyses_json):
        return datamodels.SampleAnalyses(
            raw_data=sample_analyses_json,
            sample_id=sample_analyses_json.get("sample_id"),
            sample_webif_url=sample_analyses_json.get("sample_webif_url"),
            sample_verdict=sample_analyses_json.get("sample_verdict"),
        )

    @staticmethod
    def build_sample_iocs_object(sample_iocs_json):
        ioc_files_json = sample_iocs_json.get("files", [])
        ioc_urls_json = sample_iocs_json.get("urls", [])
        ioc_ips_json = sample_iocs_json.get("ips", [])
        ioc_registries_json = sample_iocs_json.get("registry", [])
        ioc_domains_json = sample_iocs_json.get("domains", [])
        ioc_mutexes_json = sample_iocs_json.get("mutexes", [])
        ioc_processes_json = sample_iocs_json.get("processes", [])
        ioc_emails_json = sample_iocs_json.get("emails", [])

        ioc_files = list(map(VMRayParser.build_sample_ioc_file_object, ioc_files_json))
        ioc_urls = list(map(VMRayParser.build_sample_ioc_url_object, ioc_urls_json))
        ioc_ips = list(map(VMRayParser.build_sample_ioc_ip_object, ioc_ips_json))
        ioc_registries = list(
            map(VMRayParser.build_sample_ioc_registry_object, ioc_registries_json)
        )
        ioc_domains = list(
            map(VMRayParser.build_sample_ioc_domain_object, ioc_domains_json)
        )
        ioc_mutexes = list(
            map(VMRayParser.build_sample_ioc_mutexes_object, ioc_mutexes_json)
        )
        ioc_processes = list(
            map(VMRayParser.build_sample_ioc_processes_object, ioc_processes_json)
        )
        ioc_emails = list(
            map(VMRayParser.build_sample_ioc_email_object, ioc_emails_json)
        )

        return datamodels.SampleIoc(
            raw_data=sample_iocs_json,
            ioc_files=ioc_files,
            ioc_urls=ioc_urls,
            ioc_ips=ioc_ips,
            ioc_registries=ioc_registries,
            ioc_domains=ioc_domains,
            ioc_mutexes=ioc_mutexes,
            ioc_processes=ioc_processes,
            ioc_emails=ioc_emails,
        )

    @staticmethod
    def build_sample_ioc_file_object(sample_ioc_file_json):

        filename = sample_ioc_file_json.get("filename")
        severity = sample_ioc_file_json.get("severity")
        imp_hash = sample_ioc_file_json.get("imp_hash")
        md5_hash = sample_ioc_file_json.get("md5_hash")
        sha1_hash = sample_ioc_file_json.get("sha1_hash")
        sha256_hash = sample_ioc_file_json.get("sha256_hash")
        ssdeep_hash = sample_ioc_file_json.get("ssdeep_hash")
        verdict = sample_ioc_file_json.get("verdict")

        operations = ", ".join(sample_ioc_file_json.get("operations", []))

        ob_id = sample_ioc_file_json.get("id")

        return datamodels.SampleIocFile(
            raw_data=sample_ioc_file_json,
            filename=filename,
            severity=severity,
            imp_hash=imp_hash,
            md5_hash=md5_hash,
            sha1_hash=sha1_hash,
            sha256_hash=sha256_hash,
            ssdeep_hash=ssdeep_hash,
            operations=operations,
            ob_id=ob_id,
            verdict=verdict,
        )

    @staticmethod
    def build_sample_ioc_url_object(sample_ioc_url_json):
        severity = sample_ioc_url_json.get("severity")
        ob_id = sample_ioc_url_json.get("id")
        url = sample_ioc_url_json.get("url")
        operations = ", ".join(sample_ioc_url_json.get("operations", []))

        return datamodels.SampleIocUrl(
            raw_data=sample_ioc_url_json,
            severity=severity,
            ob_id=ob_id,
            url=url,
            operations=operations,
        )

    @staticmethod
    def build_sample_ioc_ip_object(sample_ioc_ip_json):
        ob_id = sample_ioc_ip_json.get("id")
        ip = sample_ioc_ip_json.get("ip_address")
        return datamodels.SampleIocIP(raw_data=sample_ioc_ip_json, ob_id=ob_id, ip=ip)

    @staticmethod
    def build_sample_ioc_registry_object(sample_ioc_registry_json):
        registry_key = sample_ioc_registry_json.get("reg_key_name")
        ob_id = sample_ioc_registry_json.get("id")
        severity = sample_ioc_registry_json.get("severity")
        verdict = sample_ioc_registry_json.get("verdict")
        operations = ", ".join(sample_ioc_registry_json.get("operations", []))
        return datamodels.SampleIocRegistry(
            raw_data=sample_ioc_registry_json,
            registry_key=registry_key,
            ob_id=ob_id,
            operations=operations,
            severity=severity,
            verdict=verdict,
        )

    @staticmethod
    def build_sample_ioc_domain_object(sample_ioc_domain_json):
        domain = sample_ioc_domain_json.get("domain")
        severity = sample_ioc_domain_json.get("severity")
        ob_id = sample_ioc_domain_json.get("id")

        return datamodels.SampleIocDomain(
            raw_data=sample_ioc_domain_json,
            domain=domain,
            severity=severity,
            ob_id=ob_id,
        )

    @staticmethod
    def build_sample_ioc_mutexes_object(sample_ioc_mutexes_json):
        return datamodels.SampleIocMutex(
            raw_data=sample_ioc_mutexes_json,
            mutex_name=sample_ioc_mutexes_json.get("mutex_name"),
            operations=sample_ioc_mutexes_json.get("operations"),
            severity=sample_ioc_mutexes_json.get("severity"),
            verdict=sample_ioc_mutexes_json.get("verdict"),
        )

    @staticmethod
    def build_sample_ioc_processes_object(sample_ioc_process_json):
        return datamodels.SampleIocProcess(
            raw_data=sample_ioc_process_json,
            process_names=sample_ioc_process_json.get("process_names", []),
        )

    @staticmethod
    def build_sample_ioc_email_object(sample_ioc_email_json):
        return datamodels.SampleIocEmail(
            raw_data=sample_ioc_email_json, email=sample_ioc_email_json.get("email")
        )

    @staticmethod
    def build_sample_threat_indicator_object(threat_indicator_json):
        analysis_ids = ", ".join(
            str(analysis_id)
            for analysis_id in threat_indicator_json.get("analysis_ids", [])
        )

        return datamodels.SampleThreatIndicator(
            raw_data=threat_indicator_json,
            analysis_ids=analysis_ids,
            category=threat_indicator_json.get("category"),
            operation=threat_indicator_json.get("operation"),
            classifications=threat_indicator_json.get("classifications"),
            score=threat_indicator_json.get("score"),
        )

    @staticmethod
    def build_sample_res_object(sample_res_json):
        samples = sample_res_json.get("samples", [])
        sample_objects = [
            VMRayParser.build_sample_analyses_object(sample) for sample in samples
        ]
        submissions = sample_res_json.get("submissions", [])
        submission_objects = [
            VMRayParser.build_sample_submission_object(submission)
            for submission in submissions
        ]
        sample_id = None
        sample_webif_url = None
        if sample_objects:
            sample_id = sample_objects[0].sample_id
            sample_webif_url = sample_objects[0].sample_webif_url
        return datamodels.SampleRes(
            raw_data=sample_res_json,
            samples=sample_objects,
            submissions=submission_objects,
            sample_id=sample_id,
            sample_webif_url=sample_webif_url,
        )

    @staticmethod
    def build_sample_submission_object(sample_submission_json):
        submission_id = sample_submission_json.get("submission_id", 0)
        return datamodels.SampleSubmission(sample_submission_json, submission_id)

    @staticmethod
    def build_sample_object(raw_data):
        data = raw_data.get("data", {})

        return datamodels.Sample(
            raw_data=raw_data,
            sample_id=(
                data.get("samples")[0].get("sample_id") if data.get("samples") else None
            ),
            job_id=data.get("jobs")[0].get("job_id") if data.get("jobs") else None,
        )
