from __future__ import annotations

import dataclasses
from typing import Optional

from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class CywareIntelExchange:
    bulk_lookup_response: Optional[SingleJson] = None
    add_allowed_iocs_response: Optional[SingleJson] = None
    remove_allowed_iocs_response: Optional[SingleJson] = None
    get_allowed_iocs_response: Optional[SingleJson] = None
    add_note_response: Optional[SingleJson] = None
    create_intel_response: Optional[SingleJson] = None
    get_ioc_details_response: Optional[SingleJson] = None
    add_tags_response: Optional[SingleJson] = None
    remove_tags_response: Optional[SingleJson] = None
    mark_false_positive_response: Optional[SingleJson] = None
    quick_intel_status_response: Optional[SingleJson] = None
    create_task_response: Optional[SingleJson] = None
    get_user_by_email_response: Optional[SingleJson] = None

    def get_bulk_lookup(self) -> SingleJson:
        if self.bulk_lookup_response:
            return self.bulk_lookup_response
        return {"results": [], "total": 0}

    def get_add_allowed_iocs(self) -> SingleJson:
        if self.add_allowed_iocs_response:
            return self.add_allowed_iocs_response
        return {
            "status": "success",
            "message": "IOCs added to allowed list",
            "details": {"new_created": [], "already_exists": [], "invalid": []},
        }

    def get_remove_allowed_iocs(self) -> SingleJson:
        if self.remove_allowed_iocs_response:
            return self.remove_allowed_iocs_response
        return {"status": "success", "message": "IOCs removed from allowed list"}

    def get_allowed_iocs(self) -> SingleJson:
        if self.get_allowed_iocs_response:
            return self.get_allowed_iocs_response
        return {"results": [], "page": 1, "page_size": 10, "total": 0}

    def get_add_note(self) -> SingleJson:
        if self.add_note_response:
            return self.add_note_response
        return {"id": "note_123", "note": "Test note", "created_at": "2024-01-01T00:00:00Z"}

    def get_create_intel(self) -> SingleJson:
        if self.create_intel_response:
            return self.create_intel_response
        return {
            "status": "success",
            "task_id": "task_123",
            "message": "Intel creation initiated",
        }

    def get_quick_intel_status(self) -> SingleJson:
        if self.quick_intel_status_response:
            return self.quick_intel_status_response
        return {"status": "completed", "task_id": "task_123", "result": "success"}

    def get_ioc_details(self) -> SingleJson:
        if self.get_ioc_details_response:
            return self.get_ioc_details_response
        return {"results": [], "page": 1, "page_size": 10, "total": 0}

    def get_add_tags(self) -> SingleJson:
        if self.add_tags_response:
            return self.add_tags_response
        return {"status": "success", "message": "Tags added successfully"}

    def get_remove_tags(self) -> SingleJson:
        if self.remove_tags_response:
            return self.remove_tags_response
        return {"status": "success", "message": "Tags removed successfully"}

    def get_mark_false_positive(self) -> SingleJson:
        if self.mark_false_positive_response:
            return self.mark_false_positive_response
        return {"status": "success", "message": "IOCs marked as false positive"}

    def get_create_task(self) -> SingleJson:
        if self.create_task_response:
            return self.create_task_response
        return {
            "id": "task_123",
            "text": "Test task",
            "priority": "medium",
            "status": "not_started",
            "object_id": "ioc_123",
            "created_at": "2024-01-01T00:00:00Z",
        }

    def get_user_by_email(self) -> SingleJson:
        if self.get_user_by_email_response:
            return self.get_user_by_email_response
        return {
            "count": 1,
            "results": [
                {
                    "id": "user_123",
                    "email": "test@example.com",
                    "username": "testuser",
                }
            ],
        }
