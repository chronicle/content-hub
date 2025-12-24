from __future__ import annotations

from .constants import VERDICT_MALICIOUS
from .datamodels import File, Host, Ip
from .exceptions import StairwellError


class StairwellParser(object):
    def build_results(
        self, raw_json, method, data_key="data", pure_data=False, limit=None, **kwargs
    ):
        try:
            data = raw_json if pure_data else raw_json.get(data_key, [])
            if not isinstance(data, list):
                data = [data]

            if limit is not None:
                data = data[:limit]

            return [getattr(self, method)(item_json, **kwargs) for item_json in data]
        except Exception as e:
            raise StairwellError(f"Error building results: {str(e)}")

    def get_host_values(self, raw_data, hostname, logger):
        if not raw_data:
            logger.error("No raw data")
            return []

        return self.build_results(
            raw_data,
            "build_siemplify_host_object",
            pure_data=True,
            hostname=hostname,
            logger=logger,
        )

    def get_ip_values(self, raw_data, ip, logger):
        if not raw_data:
            logger.error("No raw data")
            return []

        return self.build_results(
            raw_data, "build_siemplify_ip_object", pure_data=True, ip=ip, logger=logger
        )

    def get_file_values(self, raw_data, file_hash, logger):
        if not raw_data:
            logger.error("No raw data")
            return []

        return self.build_results(
            raw_data,
            "build_siemplify_file_object",
            pure_data=True,
            file_hash=file_hash,
            logger=logger,
        )

    @staticmethod
    def build_siemplify_host_object(raw_data, hostname, logger):
        try:
            return Host(
                raw_data=raw_data,
                hostname=hostname,
                opinions=raw_data.get("opinionsMostRecent"),
                comments=raw_data.get("commentsMostRecent"),
                a_records=raw_data.get("lookupARecords"),
                aaaa_records=raw_data.get("lookupAaaaRecords"),
                mx_records=raw_data.get("lookupMxRecords"),
            )
        except Exception as e:
            logger.error(f"Error creating Host object: {str(e)}")
            raise StairwellError(f"Failed to build host object: {str(e)}")

    @staticmethod
    def build_siemplify_ip_object(raw_data, ip, logger):
        try:
            return Ip(
                raw_data=raw_data,
                ip=ip,
                opinions=raw_data.get("opinionsMostRecent"),
                comments=raw_data.get("commentsMostRecent"),
                uninterestingaddr="Yes" if raw_data.get("uninterestingAddr", False) else "No",
            )
        except Exception as e:
            logger.error(f"Error creating Ip object: {str(e)}")
            raise StairwellError(f"Failed to build ip object: {str(e)}")

    @staticmethod
    def build_siemplify_file_object(raw_data, file_hash, logger):
        try:
            return File(
                raw_data=raw_data,
                file_hash=file_hash,
                file_size=raw_data.get("fileSize"),
                file_entropy=raw_data.get("fileEntropy"),
                file_hash_sha256=raw_data.get("fileHashSha256"),
                file_hash_sha1=raw_data.get("fileHashSha1"),
                file_hash_md5=raw_data.get("fileHashMd5"),
                file_hash_imphash=raw_data.get("fileHashImphash"),
                file_hash_sorted_imphash=raw_data.get("fileHashSortedImphash"),
                file_hash_tlsh=raw_data.get("fileHashTlsh"),
                file_magic=raw_data.get("fileMagic"),
                file_mime_type=raw_data.get("fileMimeType"),
                signature=raw_data.get("signature"),
                sightings_first=raw_data.get("sightingsFirst"),
                verdict_is_well_known=raw_data.get("verdictIsWellKnown"),
                verdict_maleval_malicious_probability=raw_data.get(
                    "verdictMalevalMaliciousProbability"
                ),
                summary_ai=raw_data.get("summaryAi"),
                summary_rtg=raw_data.get("summaryRtg"),
                # Optional list fields
                sightings_prevalence=raw_data.get("sightingsPrevalence"),
                verdict_maleval_labels=raw_data.get("verdictMalevalLabels"),
                verdict_yara_rule_matches=raw_data.get("verdictYaraRuleMatches"),
                indicators_ips_likely=raw_data.get("indicatorsIpsLikely"),
                indicators_hostnames_likely=raw_data.get("indicatorsHostnamesLikely"),
                indicators_hostnames_private=raw_data.get("indicatorsHostnamesPrivate"),
                variants=raw_data.get("variants"),
                opinions=raw_data.get("opinions"),
                comments=raw_data.get("comments"),
                opinions_most_recent=raw_data.get("opinionsMostRecent"),
                comments_most_recent=raw_data.get("commentsMostRecent"),
            )
        except Exception as e:
            logger.error(f"Error creating File object: {str(e)}")
            raise StairwellError(f"Failed to build file object: {str(e)}")

    def is_entity_suspicious(self, report):
        """
        Returns True if the entity is suspicious based on verdict field, else False.
        """
        verdict = getattr(report, "verdict", None)
        if verdict is not None and verdict.upper() == VERDICT_MALICIOUS:
            return True

        return False

    def is_entity_file_suspicious(self, report):
        """
        Returns True if the entity (file) is suspicious based on verdict and
        verdictMalevalMaliciousProbability fields, else False.
        """
        verdict = getattr(report, "verdict", None)
        if verdict is not None and verdict.upper() == VERDICT_MALICIOUS:
            return True

        verdict_prob = getattr(report, "verdict_maleval_malicious_probability", None)
        if verdict_prob is not None and verdict_prob.upper().startswith(VERDICT_MALICIOUS):
            return True

        return False
