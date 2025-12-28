from __future__ import annotations

import json

from soar_sdk.SiemplifyUtils import add_prefix_to_dict

from .constants import ENRICH_PREFIX


class BaseModel(object):
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Host(BaseModel):
    def __init__(self, raw_data, hostname, opinions, comments, a_records, aaaa_records, mx_records):
        super().__init__(raw_data)
        self.hostname = hostname
        self.opinions = [
            Opinion(op, op["verdict"], op["environment"], op["createTime"], op["email"])
            for op in (opinions or [])
        ]
        self.verdict = opinions[0]["verdict"] if opinions and len(opinions) > 0 else None
        self.comments = comments or []
        self.a_records = a_records or []
        self.aaaa_records = aaaa_records or []
        self.mx_records = mx_records or []

    def to_csv(self):
        """Returns a flat dictionary representation of the object for CSV."""
        return {
            "Hostname": self.hostname,
            "Host_Verdict": self.verdict,
            "Host_Opinions": json.dumps([op.to_csv() for op in self.opinions]),
            "Host_Comments": json.dumps(self.comments),
            "A_Records": json.dumps(self.a_records),
            "AAAA_Records": json.dumps(self.aaaa_records),
            "MX_Records": json.dumps(self.mx_records),
        }

    def to_json(self):
        return {key: value for key, value in self.raw_data.items() if value is not None}

    def to_enrichment(self):
        return add_prefix_to_dict(self.to_csv(), ENRICH_PREFIX)

    def to_insight(self):
        content = f"""
        <b>Hostname Enrichment Result</b><br><br>
        <table border="1">
        <tr>
            <td style='text-align: left; width: 30%;'><b>Verdict</b></td>
            <td style='text-align:right; width: 30%;'>
                <span style='color:red;'>{self.verdict}</span>
            </td>
        </tr>
        </table>
        <br>
        """

        return content


class Ip(BaseModel):
    def __init__(self, raw_data, ip, opinions, comments, uninterestingaddr):
        super().__init__(raw_data)
        self.ip = ip
        self.opinions = [
            Opinion(op, op["verdict"], op["environment"], op["createTime"], op["email"])
            for op in (opinions or [])
        ]
        self.comments = comments or []
        if opinions and len(opinions) > 0:
            self.verdict = opinions[0]["verdict"]
        else:
            self.verdict = None
        self.uninterestingaddr = uninterestingaddr

    def to_csv(self):
        """Returns a flat dictionary representation of the object for CSV."""
        return {
            "Ip": self.ip,
            "Ip_Verdict": self.verdict,
            "Ip_Opinions": json.dumps([op.to_csv() for op in self.opinions]),
            "Ip_Comments": json.dumps(self.comments),
            "UninterestingAddr": self.uninterestingaddr,
        }

    def to_json(self):
        return {key: value for key, value in self.raw_data.items() if value is not None}

    def to_enrichment(self):
        return add_prefix_to_dict(self.to_csv(), ENRICH_PREFIX)

    def to_insight(self):
        content = f"""
        <b>IP Enrichment Result</b><br><br>
        <table border="1">
        <tr><td style='text-align: left; width: 30%;'><b>Verdict</b></td>
        <td style='text-align: right; width: 30%;'>
        <span style='color:red;'>{self.verdict}</span></td></tr>
        </table>
        <br>
        """

        return content


class Certificate(BaseModel):
    def __init__(
        self, raw_data, signature, issuer, subject, earliest_valid_time, latest_valid_time
    ):
        super().__init__(raw_data)
        self.signature = signature
        self.issuer = issuer
        self.subject = subject
        self.earliest_valid_time = earliest_valid_time
        self.latest_valid_time = latest_valid_time

    def to_csv(self):
        return {
            "Signature": self.signature,
            "Issuer": self.issuer,
            "Subject": self.subject,
            "EarliestValidTime": self.earliest_valid_time,
            "LatestValidTime": self.latest_valid_time,
        }

    def to_json(self):
        return {key: value for key, value in self.raw_data.items() if value is not None}


class Signature(BaseModel):
    def __init__(self, raw_data, x509_certificates=None, pkcs7_verification_result=None):
        super().__init__(raw_data)
        self.x509_certificates = [Certificate(**cert) for cert in (x509_certificates or [])]
        self.pkcs7_verification_result = pkcs7_verification_result

    def to_csv(self):
        return {
            "X509Certificates": json.dumps([cert.to_csv() for cert in self.x509_certificates]),
            "Pkcs7VerificationResult": self.pkcs7_verification_result,
        }

    def to_json(self):
        return {key: value for key, value in self.raw_data.items() if value is not None}


class Opinion(BaseModel):
    def __init__(self, raw_data, verdict, environment, create_time, email):
        super().__init__(raw_data)
        self.verdict = verdict
        self.environment = environment
        self.create_time = create_time
        self.email = email

    def to_csv(self):
        """Returns a flat dictionary representation of the object for CSV."""
        return {
            "Verdict": self.verdict,
            "Environment": self.environment,
            "CreateTime": self.create_time,
            "Email": self.email,
        }

    def to_json(self):
        return {
            "verdict": self.verdict,
            "environment": self.environment,
            "createTime": self.create_time,
            "email": self.email,
        }


class File(BaseModel):
    def __init__(
        self,
        raw_data,
        file_hash,
        file_size,
        file_entropy,
        file_hash_sha256,
        file_hash_sha1,
        file_hash_md5,
        file_hash_imphash,
        file_hash_sorted_imphash,
        file_hash_tlsh,
        file_magic,
        file_mime_type,
        signature,
        sightings_first,
        verdict_is_well_known,
        verdict_maleval_malicious_probability,
        summary_ai,
        summary_rtg,
        sightings_prevalence=None,
        verdict_maleval_labels=None,
        verdict_yara_rule_matches=None,
        indicators_ips_likely=None,
        indicators_hostnames_likely=None,
        indicators_hostnames_private=None,
        variants=None,
        opinions=None,
        comments=None,
        opinions_most_recent=None,
        comments_most_recent=None,
    ):
        super().__init__(raw_data)
        self.file_hash = file_hash
        self.file_size = file_size
        self.file_entropy = file_entropy
        self.file_hash_sha256 = file_hash_sha256
        self.file_hash_sha1 = file_hash_sha1
        self.file_hash_md5 = file_hash_md5
        self.file_hash_imphash = file_hash_imphash
        self.file_hash_sorted_imphash = file_hash_sorted_imphash
        self.file_hash_tlsh = file_hash_tlsh
        self.file_magic = file_magic
        self.file_mime_type = file_mime_type
        self.signature = Signature(signature) if signature else None
        self.sightings_first = sightings_first
        self.verdict_is_well_known = verdict_is_well_known
        self.verdict_maleval_malicious_probability = verdict_maleval_malicious_probability
        self.summary_ai = summary_ai
        self.summary_rtg = summary_rtg

        # List fields with empty list defaults
        self.sightings_prevalence = sightings_prevalence or []
        self.verdict_maleval_labels = verdict_maleval_labels or []
        self.verdict_yara_rule_matches = verdict_yara_rule_matches or []
        self.indicators_ips_likely = indicators_ips_likely or []
        self.indicators_hostnames_likely = indicators_hostnames_likely or []
        self.indicators_hostnames_private = indicators_hostnames_private or []
        self.variants = variants or []
        self.verdict = (
            opinions_most_recent[0]["verdict"]
            if opinions_most_recent and len(opinions_most_recent) > 0
            else None
        )
        self.opinions_most_recent = [
            Opinion(op, op["verdict"], op["environment"], op["createTime"], op["email"])
            for op in (opinions_most_recent or [])
        ]
        self.comments_most_recent = comments_most_recent or []

    def to_csv(self):
        """Returns a flat dictionary representation of the object for CSV."""
        signature_data = self.signature.to_csv() if self.signature else {}
        base_data = {
            "FileHash": self.file_hash,
            "FileSize": self.file_size,
            "FileEntropy": self.file_entropy,
            "FileHashSha256": self.file_hash_sha256,
            "FileHashSha1": self.file_hash_sha1,
            "FileHashMd5": self.file_hash_md5,
            "FileHashImphash": self.file_hash_imphash,
            "FileHashSortedImphash": self.file_hash_sorted_imphash,
            "FileHashTlsh": self.file_hash_tlsh,
            "FileMagic": self.file_magic,
            "FileMimeType": self.file_mime_type,
            "SightingsFirst": self.sightings_first,
            "SightingsPrevalence": json.dumps(self.sightings_prevalence),
            "VerdictIsWellKnown": self.verdict_is_well_known,
            "VerdictMalevalMaliciousProbability": self.verdict_maleval_malicious_probability,
            "VerdictMalevalLabels": json.dumps(self.verdict_maleval_labels),
            "VerdictYaraRuleMatches": json.dumps(self.verdict_yara_rule_matches),
            "IndicatorsIpsLikely": json.dumps(self.indicators_ips_likely),
            "IndicatorsHostnamesLikely": json.dumps(self.indicators_hostnames_likely),
            "IndicatorsHostnamesPrivate": json.dumps(self.indicators_hostnames_private),
            "Variants": json.dumps(self.variants),
            "SummaryAi": self.summary_ai,
            "SummaryRtg": self.summary_rtg,
            "File_Verdict": self.verdict,
            "File_OpinionsMostRecent": json.dumps([
                op.to_csv() for op in self.opinions_most_recent
            ]),
            "File_CommentsMostRecent": json.dumps(self.comments_most_recent),
        }
        if signature_data:
            for key, value in signature_data.items():
                base_data[f"Signature{key}"] = value
        return base_data

    def to_json(self):
        return {key: value for key, value in self.raw_data.items() if value is not None}

    def to_enrichment(self):
        return add_prefix_to_dict(self.to_csv(), ENRICH_PREFIX)

    def to_insight(self):
        if self.verdict_maleval_malicious_probability is not None:
            malicious_prob = self.verdict_maleval_malicious_probability.replace(
                "MALICIOUS_PROBABILITY_", ""
            )

        content = f"""
        <b>File Hash Enrichment Result</b><br><br>
        <table border="1">
        <tr>
            <td style='text-align: left;'><b>Malicious Probability<b></b></td>
            <td style='text-align: right;'><span style='color:red;'>{malicious_prob}</span></td>
        </tr>
        <tr>
            <td style='text-align: left;'><b>Detections Labels</b></td>
            <td style='text-align: right;'>{self.verdict_maleval_labels}</td>
        </tr>
        <tr>
            <td style='text-align: left;'><b>File Mime Type</b></td>
            <td style='text-align: right;'>{self.file_mime_type}</td>
        </tr>
        <tr>
            <td style='text-align: left;'><b>First Seen</b></td>
            <td style='text-align: right;'>{self.sightings_first}</td>
        </tr>
        </table>
        <br>
        """

        return content
