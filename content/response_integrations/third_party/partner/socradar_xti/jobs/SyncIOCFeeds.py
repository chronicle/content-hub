"""
Sync IOC Feeds Job
==================
Scheduled job that fetches IOCs from configured SOCRadar Threat Feed
collections and writes them to Google SecOps SOAR Custom Lists.

Runs daily (or at configured interval). Groups IOCs by type
(ip, domain, hash, url) and writes one Custom List category per type.

Note: the SOAR SDK (SiemplifyJob) exposes Custom Lists, not SIEM reference
lists, so each IOC is stored as a Custom List entry (category = list name,
identifier = IOC value) scoped to the configured environment.
"""
from __future__ import annotations

from soar_sdk.SiemplifyDataModel import CustomList
from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import output_handler

from ..core.SOCRadarManager import SOCRadarManager

INTEGRATION_NAME = "SOCRadar"
JOB_NAME = "SOCRadar - Sync IOC Feeds"

# Custom List category prefix — creates categories like:
# SOCRadar_IOC_ip, SOCRadar_IOC_domain, SOCRadar_IOC_hash, SOCRadar_IOC_url
REFERENCE_LIST_PREFIX = "SOCRadar_IOC"

# Max Custom List entries sent per API call (bounds request size for large feeds).
CUSTOM_LIST_BATCH_SIZE = 1000

# Default SOAR environment for Custom List entries when none is configured.
DEFAULT_ENVIRONMENT = "Default Environment"

IOC_TYPES = ["ip", "domain", "hash", "url"]

# Map SOCRadar feed_type values to custom-list bucket names.
# NOTE: the feed returns domain IOCs as "hostname" (OpenAPI docs are wrong).
FEED_TYPE_MAP = {
    "hostname": "domain", "domain": "domain",
    "ip": "ip", "ipv4": "ip", "ipv6": "ip",
    "url": "url",
    "hash": "hash", "md5": "hash", "sha1": "hash", "sha256": "hash",
}


def _parse_uuids(raw: str | None) -> list[str]:
    """Parse comma/newline/semicolon separated UUIDs."""
    if not raw:
        return []
    uuids = []
    for line in raw.replace(";", ",").replace("\n", ",").split(","):
        val = line.strip()
        if val:
            uuids.append(val)
    return uuids


@output_handler
def main() -> None:
    """Main execution function for the Sync IOC Feeds job."""
    siemplify = SiemplifyJob()
    siemplify.script_name = JOB_NAME

    try:
        api_root = siemplify.extract_job_param("API Root",
                                                default_value="https://platform.socradar.com/api")
        api_key = siemplify.extract_job_param("API Key")
        company_id = siemplify.extract_job_param("Company ID")
        verify_ssl = siemplify.extract_job_param("Verify SSL",
                                                  input_type=bool, default_value=True)

        uuids_raw = siemplify.extract_job_param("Collection UUIDs")
        try:
            max_iocs = int(siemplify.extract_job_param("Max IOCs Per Feed",
                                                        default_value="5000"))
        except (ValueError, TypeError):
            max_iocs = 5000
        list_prefix = siemplify.extract_job_param("Reference List Prefix",
                                                   default_value=REFERENCE_LIST_PREFIX)
        environment = siemplify.extract_job_param("Environment",
                                                  default_value=DEFAULT_ENVIRONMENT)

        uuids = _parse_uuids(uuids_raw)
        uuids = list(dict.fromkeys(uuids))  # Deduplicate, preserve order
        if not uuids:
            siemplify.LOGGER.error("No Collection UUIDs configured. Nothing to sync.")
            return

        siemplify.LOGGER.info(f"Starting IOC feed sync for {len(uuids)} collection(s)")
        manager = SOCRadarManager(api_root, api_key, company_id, verify_ssl)

        # Collect IOCs grouped by type
        iocs_by_type = {t: set() for t in IOC_TYPES}
        feed_stats = {"success": 0, "error": 0, "total_iocs": 0}

        for uuid in uuids:
            try:
                feed_data = manager.get_ioc_feed(uuid)
                if not isinstance(feed_data, list):
                    siemplify.LOGGER.warning(f"Unexpected response for UUID {uuid}: {type(feed_data)}")
                    feed_stats["error"] += 1
                    continue

                count = 0
                for ioc in feed_data[:max_iocs]:
                    if not isinstance(ioc, dict):
                        continue
                    ioc_type = FEED_TYPE_MAP.get(str(ioc.get("feed_type") or "").lower().strip())
                    ioc_value = str(ioc.get("feed") or "").strip()
                    if ioc_type and ioc_value:
                        iocs_by_type[ioc_type].add(ioc_value)
                        count += 1

                feed_stats["success"] += 1
                feed_stats["total_iocs"] += count
                siemplify.LOGGER.info(f"UUID {uuid}: {count} IOCs fetched")

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process UUID {uuid}: {e}")
                feed_stats["error"] += 1

        # Write IOCs to SOAR Custom Lists (one category per IOC type).
        lists_written = 0
        lists_failed = 0
        lists_with_values = 0
        for ioc_type in IOC_TYPES:
            values = sorted(iocs_by_type[ioc_type])
            if not values:
                siemplify.LOGGER.info(f"No {ioc_type} IOCs to sync, skipping")
                continue

            lists_with_values += 1
            list_name = f"{list_prefix}_{ioc_type}"
            try:
                for start in range(0, len(values), CUSTOM_LIST_BATCH_SIZE):
                    batch = values[start:start + CUSTOM_LIST_BATCH_SIZE]
                    custom_list_items = [
                        CustomList(value, list_name, environment) for value in batch
                    ]
                    siemplify.add_entities_to_custom_list(custom_list_items)
                lists_written += 1
                siemplify.LOGGER.info(
                    f"Updated custom list '{list_name}' with {len(values)} entries"
                )
            except Exception as e:
                lists_failed += 1
                siemplify.LOGGER.error(f"Failed to update custom list '{list_name}': {e}")

        siemplify.LOGGER.info(
            f"Sync complete. Feeds: {feed_stats['success']} OK / {feed_stats['error']} failed. "
            f"Lists: {lists_written} written / {lists_failed} failed. "
            f"Total IOCs processed: {feed_stats['total_iocs']}"
        )

        # A run that fetched IOCs but wrote none is a failure, not a success.
        if lists_with_values and lists_written == 0:
            raise RuntimeError(
                f"All {lists_failed} custom list update(s) failed; no IOCs were written to SOAR."
            )

    except Exception as e:
        siemplify.LOGGER.error(f"Job failed: {e}")
        siemplify.LOGGER.exception(e)
        raise


if __name__ == "__main__":
    main()
