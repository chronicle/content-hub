from __future__ import annotations
from unittest.mock import MagicMock
from anomali_threat_stream.core.datamodels import (
    Indicator,
    IndicatorsGroup,
)


def test_indicators_group_as_enrichment_disjoint_keys():
    # Setup mock indicators with disjoint keys
    # Indicator 1 has trusted_circle_ids but no latitude, longitude
    ind1 = Indicator(
        raw_data={
            "id": 1,
            "status": "active",
            "itype": "ip",
            "type": "ip",
            "value": "1.1.1.1",
            "trusted_circle_ids": [34, 12],
            "severity": "medium",
            "confidence": 80,
        },
        severity="medium",
        web_root="http://localhost",
    )

    # Indicator 2 has latitude but no trusted_circle_ids
    ind2 = Indicator(
        raw_data={
            "id": 2,
            "status": "active",
            "itype": "ip",
            "type": "ip",
            "value": "1.1.1.1",
            "latitude": "34.0522",
            "severity": "low",
            "confidence": 60,
        },
        severity="low",
        web_root="http://localhost",
    )

    # Indicator 3 has longitude, and different trusted_circle_ids
    ind3 = Indicator(
        raw_data={
            "id": 3,
            "status": "active",
            "itype": "ip",
            "type": "ip",
            "value": "1.1.1.1",
            "longitude": "-118.2437",
            "trusted_circle_ids": [56],
            "severity": "high",
            "confidence": 100,
        },
        severity="high",
        web_root="http://localhost",
    )

    mock_entity = MagicMock()
    group = IndicatorsGroup(entity=mock_entity, indicators=[ind1, ind2, ind3])

    assert group.active_indicators_count == 3

    enrichment = group.as_enrichment(prefix="AnomaliTS")
    assert enrichment["AnomaliTS_id"] == "1, 2, 3"
    assert enrichment["AnomaliTS_trusted_circle_ids"] == "34, 12, 56"
    assert enrichment["AnomaliTS_latitude"] == "34.0522"
    assert enrichment["AnomaliTS_longitude"] == "-118.2437"
    assert enrichment["AnomaliTS_severity"] == "high"


def test_indicators_group_as_enrichment_falsy_values():
    # Indicator 1 has threat_score 0
    ind1 = Indicator(
        raw_data={
            "id": 1,
            "status": "active",
            "itype": "ip",
            "type": "ip",
            "value": "1.1.1.1",
            "threatscore": 0,
            "severity": "medium",
            "confidence": 80,
        },
        severity="medium",
        web_root="http://localhost",
    )

    mock_entity = MagicMock()
    group = IndicatorsGroup(entity=mock_entity, indicators=[ind1])

    enrichment = group.as_enrichment(prefix="AnomaliTS")
    assert enrichment["AnomaliTS_threat_score"] == "0"

