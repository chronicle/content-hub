# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from pathlib import Path

# Ensure the 'src' directory is in the python path if running from the root of the package
sys.path.append(str(Path(__file__).parent / "src"))

from mp.dev_env.sub_commands.integration import utils
from mp.dev_env.utils import get_backend_api, load_dev_env_config

# =====================================================================
# CONFIGURATION CONSTANTS
# Edit these variables to change the script's behavior
# =====================================================================

INTEGRATIONS_TO_DOWNLOAD = [
    "xdr-retrieve-file-details",
    "xdr-file-retrieve",
    "SubmitFile",
    "snx-analysis-submit-file",
    "snx-analysis-get-verdict",
    "snx-analysis-get-report",
    "SetOwnerDisplayName",
    "setinitialseverity",
    "SetDateField",
    "Sendmail",
    "ScheduleGenericPollingV2",
    "ScheduleGenericPolling",
    "RunPollingCommandV2",
    "RunPollingCommand",
    "PrintErrorEntry",
    "polygon-upload-file",
    "polygon-export-video",
    "polygon-export-report",
    "polygon-export-pcap",
    "polygon-analysis-info",
    "ParseEmailFilesV2",
    "msgraph-user-get",
    "msgraph-identity-directory-roles-list",
    "msgraph-identity-directory-role-members-list",
    "MicrosoftGraphIdentityandAccess",
    "metadefender-sandbox-scan-file",
    "JoeSecurityV2SubmitSample",
    "JoeSecurityV2DownloadReport",
    "JoeSecurityV2",
    "JoeSandboxGetSampleDetails",
    "JoeSandboxDownloadReport",
    "joe-analysis-info",
    "IsIntegrationAvailable",
    "GoogleChronicleBackstory",
    "gcb-get-rule",
    "ExportToXLSX",
    "EmailAbuseSeverity",
    "EmailAbusejoesubmitsample",
    "EmailAbuseJoeReportLinks",
    "EmailAbuseGCBURL",
    "EmailAbuseCreateIndicators",
    "DeleteContext",
    "CuratedDetectionsFieldConversion",
    "CuratedDetectionsDetectionLogic",
    "CuratedDetectionsChangeName",
    "cs-falcon-search-device",
    "cs-falcon-contain-host",
    "CrowdStrikeFalconGetReportSummary",
    "CrowdStrikeFalconGetFullReport",
    "CreateNewIndicatorsOnly",
    "ConvertCountryCodeCountryName",
    "azure-vm-get-public-ip-details",
    "azure-vm-get-nic-details",
    "azure-vm-get-instance-details",
    "azure-rg-query",
    "associateIndicatorsToIncident",
]

# Destination path for the unzipped integrations
DESTINATION_PATH = Path("/Users/amitjoseph/Desktop/Google/xsoar-migration-project/custom-artifacts")

# Set to True if you want to keep the downloaded .zip files
KEEP_ZIP = False

# =====================================================================


def download_and_unzip_integrations(
    integration_names: list[str], destination: Path, keep_zip: bool = False
):
    """Downloads and unzips a list of integrations.

    Args:
        integration_names: List of integration names to download.
        destination: Path where integrations should be unzipped.
        keep_zip: Whether to keep the downloaded zip files.
    """
    destination.mkdir(parents=True, exist_ok=True)

    try:
        config = load_dev_env_config()
        backend_api = get_backend_api(config)
    except Exception as e:
        print(f"Failed to initialize backend API: {e}")
        return

    for integration in integration_names:
        print(f"Processing integration: {integration}...")
        zip_path = None
        try:
            # Download integration
            print(f"  Downloading {integration}...")
            resp = backend_api.download_integration(integration)

            # Save as zip
            zip_path = utils.save_integration_as_zip(integration, resp, destination)
            print(f"  Saved zip to {zip_path}")

            # Unzip integration
            # unzip_integration(zip_path, temp_path) extracts to temp_path / zip_path.stem
            unzipped_path = utils.unzip_integration(zip_path, destination)
            print(f"  Unzipped to {unzipped_path}")

            if not keep_zip:
                zip_path.unlink()
                print(f"  Removed zip file {zip_path}")

            print(f"Successfully processed {integration}")

        except Exception as e:
            print(f"Error processing integration {integration}: {e}")
            if zip_path and zip_path.exists() and not keep_zip:
                zip_path.unlink()


if __name__ == "__main__":
    print(f"Starting download to {DESTINATION_PATH.resolve()}")
    download_and_unzip_integrations(
        integration_names=INTEGRATIONS_TO_DOWNLOAD, destination=DESTINATION_PATH, keep_zip=KEEP_ZIP
    )
    print("Done!")
