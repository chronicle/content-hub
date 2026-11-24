from __future__ import annotations

from google_cloud_compute.core.GoogleCloudComputeConstants import (
    INTEGRATION_NAME,
    ADD_NETWORK_TAGS_SCRIPT_NAME,
)
from google_cloud_compute.core.GoogleCloudComputeGenerics import UpdateTagsAction


class AddNetworkTags(UpdateTagsAction):

    def _get_success_message(self, resource_path: str) -> str:
        return (
            "Successfully added network tags to the instance "
            f"{resource_path} in {INTEGRATION_NAME}."
        )

    def _get_tags(self, existing_tags: set[str]) -> list[str]:
        return list(existing_tags.union(self.params.network_tags_set))


def main() -> None:
    AddNetworkTags(
        f"{INTEGRATION_NAME} - {ADD_NETWORK_TAGS_SCRIPT_NAME}"
    ).run()


if __name__ == "__main__":
    main()
