from __future__ import annotations
import abc

from typing import Any
from proofpoint_threat_protection.core.data_models import (
    AllowEntry,
    BlockEntry,
)


class ProofpointThreatProtection(abc.ABC):
    def __init__(self) -> None:
        self._allow_list_entries: list[AllowEntry] = []
        self._block_list_entries: list[BlockEntry] = []
        self._fail_on_add_value: str | None = None

    def add_allow_list_entries(self, entries: list[dict[str, Any]]) -> bool:
        """
        Add entries to the mock allow list.

        Args:
            entries: A list of allow list entries to add.

        Returns:
            A boolean indicating if the operation was successful.
        """
        for entry_to_add in entries:
            if (
                self._fail_on_add_value
                and entry_to_add.get("value") == self._fail_on_add_value
            ):
                return False

            is_duplicate = any(
                existing_entry.value == entry_to_add.get("value")
                and existing_entry.attribute == entry_to_add.get("attribute")
                for existing_entry in self._allow_list_entries
            )
            if not is_duplicate:
                self._allow_list_entries.append(AllowEntry.from_json(entry_to_add))
        return True

    def get_allow_list_entries(self) -> list[dict[str, Any]]:
        return [entry.to_json() for entry in self._allow_list_entries]

    def cleanup_allow_list_entries(self) -> None:
        self._allow_list_entries = []

    def remove_allow_list_entry(self, entry_to_remove: dict[str, Any]) -> bool:
        """
        Remove an entry from the mock allow list.

        Args:
            entry_to_remove: The allow list entry to remove.

        Returns:
            A boolean indicating if an entry was removed.
        """
        initial_len = len(self._allow_list_entries)
        self._allow_list_entries = [
            entry
            for entry in self._allow_list_entries
            if not (
                entry.value == entry_to_remove.get("value")
                and entry.attribute == entry_to_remove.get("attribute")
            )
        ]
        return len(self._allow_list_entries) < initial_len

    def add_block_list_entries(self, entries: list[dict[str, Any]]) -> bool:
        """
        Add entries to the mock block list.

        Args:
            entries: A list of block list entries to add.

        Returns:
            A boolean indicating if the operation was successful.
        """
        for entry_to_add in entries:
            if (
                self._fail_on_add_value
                and entry_to_add.get("value") == self._fail_on_add_value
            ):
                return False
            is_duplicate = any(
                existing_entry.value == entry_to_add.get("value")
                and existing_entry.attribute == entry_to_add.get("attribute")
                for existing_entry in self._block_list_entries
            )
            if not is_duplicate:
                self._block_list_entries.append(BlockEntry.from_json(entry_to_add))
        return True

    def remove_block_list_entry(self, entry_to_remove: dict[str, Any]) -> bool:
        """
        Remove an entry from the mock block list.

        Args:
            entry_to_remove: The block list entry to remove.

        Returns:
            A boolean indicating if an entry was removed.
        """
        initial_len = len(self._block_list_entries)
        self._block_list_entries = [
            entry
            for entry in self._block_list_entries
            if not (
                entry.value == entry_to_remove.get("value")
                and entry.attribute == entry_to_remove.get("attribute")
            )
        ]
        return len(self._block_list_entries) < initial_len

    def get_block_list_entries(self) -> list[dict[str, Any]]:
        return [entry.to_json() for entry in self._block_list_entries]

    def cleanup_block_list_entries(self) -> None:
        self._block_list_entries = []

    def set_fail_on_add(self, value: str) -> None:
        self._fail_on_add_value = value
