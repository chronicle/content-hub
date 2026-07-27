from __future__ import annotations

mapping_config = {
    "violation/list": {
        "uid": "id",
        "fake_uri": "violation.uri",
        "detection_sources": "violation.source",
        "status": "violation.status",
        "violation_type": "violation.violationSubtype",
        "approve_state": "violation.approveState",
        "status_date": "violation.dates.currentStatusDate",
        "title": "violation.title",
        "created_date": "violation.dates.createdDate",
        "found_date": "violation.dates.foundDate",
        "detected_date": "violation.dates.detectedDate",
        "approved_date": "violation.dates.approvedDate",
        "drp_link": "link",
        "subscription": "violation.violationType",
        "seqUpdate": "violation.seqUpdate",
    }
}
