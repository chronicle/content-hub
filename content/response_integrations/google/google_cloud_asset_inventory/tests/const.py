import os

CONFIG_FILE_NAME = os.path.join(os.path.dirname(__file__), "config.json")
DUMMY_CONTENT = {"status": "200"}
RESOURCES_NAME = (
    "//iam.googleapis.com/projects/matanhayun-test-project/"
    "serviceAccounts/xxxxxx/keys/xxxxxx"
)
DEFAULT_VALUE = "Default Value"
ASSET_NAME = ["Default"]
ASSET_NAME_VALUE = "//cloudresourcemanager.googleapis.com/projects/xxxxx"
ATTACHED_RESOURCE_NAME = "//cloudresourcemanager.googleapis.com/projects/xxxxx"
