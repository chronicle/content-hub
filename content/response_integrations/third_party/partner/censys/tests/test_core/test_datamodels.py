from __future__ import annotations

import json

from censys.core.datamodels import HostDatamodel, HostEnrichmentDatamodel, ReputationExtractor
from censys.tests.common import REPUTATION_EDGE_CASES, REPUTATION_MULTI_IP_BATCH

SAMPLE_REPUTATION = {
    "score": 0.191,
    "model_version": "2.0.0",
    "label": "BENIGN",
    "score_suppressed": False,
    "evidence": [
        {
            "feature": {
                "id": "distinct_threat_id_count",
                "name": "Distinct Threats",
                "value": "0",
                "contribution": 0.0995,
                "category": "threat_intelligence",
            }
        },
        {
            "feature": {
                "id": "has_threat",
                "name": "Any Threat",
                "value": "false",
                "contribution": 0.063,
                "category": "threat_intelligence",
            }
        },
        {
            "feature": {
                "id": "distinct_port_count",
                "name": "Distinct Ports",
                "value": "0",
                "contribution": 0.0552,
                "category": "service_surface",
            }
        },
        {
            "feature": {
                # No "value" key at all - Censys omits it for some features.
                "id": "max_port",
                "name": "Max Port",
                "contribution": 0.047,
                "category": "service_surface",
            }
        },
        {
            "feature": {
                "id": "greynoise_tag_count",
                "name": "GreyNoise Tags Count",
                "value": "0",
                "contribution": 0.0433,
                "category": "external_reputation",
            }
        },
        {
            "feature": {
                # 6th entry - should be dropped by the top-5 limit.
                "id": "low_signal",
                "name": "Low Signal",
                "value": "0",
                "contribution": 0.0001,
                "category": "service_surface",
            }
        },
    ],
    "class_probabilities": [
        {"label": "HONEYPOT", "probability": 0.0006},
        {"label": "INACTIVE"},  # No "probability" key - Censys omits negligible ones.
        {"label": "BENIGN", "probability": 0.6899},
        {"label": "SUSPICIOUS", "probability": 0.2962},
        {"label": "MALICIOUS", "probability": 0.0133},
    ],
}


class TestReputationExtractorScaling:
    """Score, probability, and contribution are 0-1 fractions in the raw API
    response; the Censys UI displays them multiplied by 100."""

    def test_scale_typical_fraction(self) -> None:
        assert ReputationExtractor._scale(0.666) == 66.6

    def test_scale_zero(self) -> None:
        assert ReputationExtractor._scale(0) == 0

    def test_scale_none_returns_none(self) -> None:
        assert ReputationExtractor._scale(None) is None

    def test_scale_non_numeric_returns_none(self) -> None:
        assert ReputationExtractor._scale("not-a-number") is None

    def test_scale_matches_get_host_json_sample(self) -> None:
        # Verified numerically against Censys-new-support/get_host.json:
        # raw contribution 0.0995 -> displayed 9.95 (not left as 0.0995).
        assert ReputationExtractor._scale(0.0995) == 9.95


class TestGetEntityEnrichmentFields:
    def test_none_reputation_returns_empty_dict(self) -> None:
        assert ReputationExtractor.get_entity_enrichment_fields(None) == {}

    def test_empty_dict_reputation_returns_empty_dict(self) -> None:
        assert ReputationExtractor.get_entity_enrichment_fields({}) == {}

    def test_full_reputation_produces_expected_fields(self) -> None:
        fields = ReputationExtractor.get_entity_enrichment_fields(SAMPLE_REPUTATION)

        assert fields["Censys_reputation_label"] == "BENIGN"
        assert fields["Censys_reputation_score_percent"] == 19.1
        assert fields["Censys_reputation_score_suppressed"] is False

        class_probabilities = json.loads(
            fields["Censys_reputation_class_probabilities"]
        )
        assert {"label": "BENIGN", "probability": 68.99} in class_probabilities
        # INACTIVE has no probability in the raw payload - must not crash and
        # must come through as None rather than being silently dropped.
        inactive = next(
            p for p in class_probabilities if p["label"] == "INACTIVE"
        )
        assert inactive["probability"] is None

        evidence = json.loads(fields["Censys_reputation_evidence"])
        assert len(evidence) == 5  # top-5 limit applied
        # Compact entity shape: feature_id is dropped (redundant with the
        # human-readable feature name) to keep the entity property small.
        assert "feature_id" not in evidence[0]
        assert evidence[0]["feature"] == "Distinct Threats"
        assert evidence[0]["contribution"] == 9.95
        # The 6th/lowest-contribution entry must be dropped.
        assert all(e["feature"] != "Low Signal" for e in evidence)
        # max_port has no "value" key - must surface as None, not raise.
        max_port_evidence = next(
            e for e in evidence if e["feature"] == "Max Port"
        )
        assert max_port_evidence["value"] is None

    def test_entity_evidence_json_is_smaller_than_full_table_shape(self) -> None:
        # SecOps truncates long entity property values (confirmed by manual
        # QA against a live tenant, not just a display artifact - the value
        # was genuinely unavailable even after expanding the row). The
        # entity property must therefore be meaningfully smaller than the
        # fuller shape used for table rows, which have no such constraint.
        reputation = {
            "evidence": [
                {
                    "feature": {
                        "id": "distinct_threat_id_count",
                        "name": "Distinct Threats",
                        "value": "0",
                        "contribution": 0.1025,
                        "category": "threat_intelligence",
                    }
                }
            ]
        }
        fields = ReputationExtractor.get_entity_enrichment_fields(reputation)
        entity_evidence_json = fields["Censys_reputation_evidence"]
        table_row_json = json.dumps(
            ReputationExtractor.get_evidence_rows("1.1.1.1", reputation)
        )
        assert len(entity_evidence_json) < len(table_row_json)

        entry = json.loads(entity_evidence_json)[0]
        assert set(entry.keys()) == {"feature", "value", "contribution", "category"}
        assert "feature_id" not in entry
        assert "feature_name" not in entry
        assert entry["feature"] == "Distinct Threats"

    def test_score_suppressed_false_is_kept_not_dropped(self) -> None:
        # score_suppressed=False is a meaningful, valid value - the shared
        # "drop falsy/None" filtering elsewhere in this module must not
        # accidentally swallow it (False is falsy but not None).
        fields = ReputationExtractor.get_entity_enrichment_fields(
            {"score_suppressed": False}
        )
        assert fields["Censys_reputation_score_suppressed"] is False

    def test_missing_evidence_and_class_probabilities_keys(self) -> None:
        # Only label/score present - evidence/class_probabilities keys absent
        # entirely (not just empty lists).
        fields = ReputationExtractor.get_entity_enrichment_fields(
            {"label": "SUSPICIOUS", "score": 0.5}
        )
        assert fields["Censys_reputation_label"] == "SUSPICIOUS"
        assert "Censys_reputation_class_probabilities" not in fields
        assert "Censys_reputation_evidence" not in fields

    def test_explicitly_empty_evidence_and_class_probabilities_lists(self) -> None:
        # Distinct from the key being absent: a host can have a reputation
        # score with zero contributing signals, so Censys may send
        # "evidence": [] / "class_probabilities": [] rather than omitting
        # the keys. Must behave the same as "absent" - no JSON property for
        # an empty list, not an empty "[]" string.
        fields = ReputationExtractor.get_entity_enrichment_fields(
            {"label": "BENIGN", "score": 0.05, "evidence": [], "class_probabilities": []}
        )
        assert fields["Censys_reputation_label"] == "BENIGN"
        assert "Censys_reputation_class_probabilities" not in fields
        assert "Censys_reputation_evidence" not in fields

    def test_evidence_entries_missing_feature_key_are_skipped_safely(self) -> None:
        reputation = {"evidence": [{"not_a_feature_key": {}}, {"feature": None}]}
        fields = ReputationExtractor.get_entity_enrichment_fields(reputation)
        # Both entries have no usable "feature" dict; contribution defaults to
        # 0 for sorting purposes and the entries still serialize without error.
        evidence = json.loads(fields.get("Censys_reputation_evidence", "[]"))
        assert len(evidence) == 2

    def test_non_dict_evidence_entries_are_ignored(self) -> None:
        # Malformed API payload: evidence is a list of non-dict junk.
        reputation = {"evidence": ["not-a-dict", 123, None]}
        fields = ReputationExtractor.get_entity_enrichment_fields(reputation)
        assert "Censys_reputation_evidence" not in fields

    def test_non_dict_class_probability_entries_are_ignored(self) -> None:
        reputation = {"class_probabilities": ["not-a-dict", None]}
        fields = ReputationExtractor.get_entity_enrichment_fields(reputation)
        assert "Censys_reputation_class_probabilities" not in fields


class TestSummaryRow:
    def test_none_reputation_returns_none(self) -> None:
        assert ReputationExtractor.get_summary_row("1.1.1.1", None) is None

    def test_empty_reputation_returns_none(self) -> None:
        assert ReputationExtractor.get_summary_row("1.1.1.1", {}) is None

    def test_full_reputation_row(self) -> None:
        row = ReputationExtractor.get_summary_row("1.1.1.1", SAMPLE_REPUTATION)
        assert row == {
            "IP": "1.1.1.1",
            "Label": "BENIGN",
            "Score": 19.1,
            "Score Suppressed": False,
        }

    def test_missing_label_falls_back_to_na(self) -> None:
        row = ReputationExtractor.get_summary_row("1.1.1.1", {"score": 0.5})
        assert row["Label"] == "N/A"
        assert row["Score Suppressed"] == "N/A"

    def test_empty_evidence_and_class_probabilities_do_not_suppress_summary_row(
        self,
    ) -> None:
        # A host with a real score/label but zero signals must still get a
        # Reputation Summary row - only the Class Probabilities/Evidence
        # tables should end up empty for it, not the summary too.
        row = ReputationExtractor.get_summary_row(
            "1.1.1.1",
            {"label": "BENIGN", "score": 0.05, "evidence": [], "class_probabilities": []},
        )
        assert row == {
            "IP": "1.1.1.1",
            "Label": "BENIGN",
            "Score": 5.0,
            "Score Suppressed": "N/A",
        }


class TestClassProbabilityRows:
    def test_none_reputation_returns_empty_list(self) -> None:
        assert ReputationExtractor.get_class_probability_rows("1.1.1.1", None) == []

    def test_full_reputation_rows(self) -> None:
        rows = ReputationExtractor.get_class_probability_rows(
            "1.1.1.1", SAMPLE_REPUTATION
        )
        assert len(rows) == 5
        assert {"IP": "1.1.1.1", "Label": "BENIGN", "Probability (%)": 68.99} in rows
        inactive_row = next(r for r in rows if r["Label"] == "INACTIVE")
        assert inactive_row["Probability (%)"] is None


class TestEvidenceRows:
    def test_none_reputation_returns_empty_list(self) -> None:
        assert ReputationExtractor.get_evidence_rows("1.1.1.1", None) == []

    def test_rows_sorted_by_contribution_descending_and_limited_to_five(self) -> None:
        rows = ReputationExtractor.get_evidence_rows("1.1.1.1", SAMPLE_REPUTATION)
        assert len(rows) == 5
        contributions = [r["Contribution (%)"] for r in rows]
        assert contributions == sorted(contributions, reverse=True)
        assert rows[0]["Feature"] == "Distinct Threats"
        assert rows[0]["IP"] == "1.1.1.1"

    def test_feature_falls_back_to_id_when_name_missing(self) -> None:
        reputation = {
            "evidence": [
                {"feature": {"id": "some_id", "contribution": 0.1}},
            ]
        }
        rows = ReputationExtractor.get_evidence_rows("1.1.1.1", reputation)
        assert rows[0]["Feature"] == "some_id"

    def test_explicitly_empty_evidence_list_yields_no_rows(self) -> None:
        # A host can have a reputation score with zero contributing signals -
        # "evidence": [] is valid and distinct from the key being absent.
        rows = ReputationExtractor.get_evidence_rows(
            "1.1.1.1", {"label": "BENIGN", "score": 0.05, "evidence": []}
        )
        assert rows == []


class TestHostDatamodelReputationIntegration:
    """HostDatamodel (Get Host API) previously extracted no reputation data
    at all; it must now include the same reputation fields as
    HostEnrichmentDatamodel (Get Host Enrichment API), including the raw
    Censys_reputation_score/score_level fields for parity between the two
    actions - Get Host API never had these before, so this is a pure
    addition with no backward-compatibility constraint of its own."""

    def test_reputation_fields_present_in_enrichment_data(self) -> None:
        model = HostDatamodel(
            {
                "result": {
                    "resource": {
                        "ip": "1.1.4.3",
                        "reputation": SAMPLE_REPUTATION,
                    }
                }
            }
        )
        enrichment = model.get_enrichment_data()
        assert enrichment["Censys_reputation_score"] == 0.191
        assert enrichment["Censys_reputation_label"] == "BENIGN"
        assert enrichment["Censys_reputation_score_percent"] == 19.1
        assert "Censys_reputation_evidence" in enrichment

    def test_reputation_score_level_present_when_in_payload(self) -> None:
        model = HostDatamodel(
            {
                "result": {
                    "resource": {
                        "ip": "1.1.4.3",
                        "reputation": {**SAMPLE_REPUTATION, "score_level": "benign"},
                    }
                }
            }
        )
        enrichment = model.get_enrichment_data()
        assert enrichment["Censys_reputation_score_level"] == "benign"

    def test_null_reputation_does_not_raise(self) -> None:
        # Censys can return explicit JSON null for unset sub-objects.
        model = HostDatamodel(
            {"result": {"resource": {"ip": "1.1.4.3", "reputation": None}}}
        )
        enrichment = model.get_enrichment_data()
        assert "Censys_reputation_label" not in enrichment
        assert "Censys_reputation_score" not in enrichment

    def test_missing_reputation_key_does_not_raise(self) -> None:
        model = HostDatamodel({"result": {"resource": {"ip": "1.1.4.3"}}})
        enrichment = model.get_enrichment_data()
        assert "Censys_reputation_label" not in enrichment


class TestHostEnrichmentDatamodelReputationIntegration:
    """HostEnrichmentDatamodel previously only extracted score/score_level;
    the pre-existing fields must be unchanged (backward compatibility) while
    the new fields are added alongside them."""

    def test_existing_fields_unchanged_and_new_fields_added(self) -> None:
        model = HostEnrichmentDatamodel(
            {
                "result": {
                    "resource": {
                        "ip": "1.1.4.3",
                        "reputation": {**SAMPLE_REPUTATION, "score_level": "benign"},
                    }
                }
            }
        )
        enrichment = model.get_enrichment_data()

        # Pre-existing, unchanged fields (raw score, not scaled).
        assert enrichment["Censys_reputation_score"] == 0.191
        assert enrichment["Censys_reputation_score_level"] == "benign"

        # New fields added alongside.
        assert enrichment["Censys_reputation_label"] == "BENIGN"
        assert enrichment["Censys_reputation_score_percent"] == 19.1
        assert enrichment["Censys_reputation_score_suppressed"] is False

    def test_null_reputation_subobject_does_not_raise(self) -> None:
        # Regression guard for the null-safety bug flagged in prior review:
        # {"reputation": null} must not raise AttributeError.
        model = HostEnrichmentDatamodel(
            {"result": {"resource": {"ip": "1.1.4.3", "reputation": None}}}
        )
        enrichment = model.get_enrichment_data()
        assert "Censys_reputation_score" not in enrichment
        assert "Censys_reputation_label" not in enrichment


# ---------------------------------------------------------------------------
# End-to-end edge case coverage, backed by shared fixtures in
# tests/mocks/mock_responses.json ("reputation_edge_cases"). These exercise
# the full HostDatamodel/HostEnrichmentDatamodel + ReputationExtractor
# pipeline against realistic raw API payloads, not synthetic dicts, so a
# schema/behavior regression here would also be caught by a hand walkthrough
# with the same fixtures in the SecOps UI.
# ---------------------------------------------------------------------------


class TestReputationEdgeCasesBothDatamodels:
    """Absent key, explicit null, and empty object must all behave
    identically on both datamodels: no reputation properties, no exception,
    other enrichment data for the host is unaffected."""

    EDGE_CASE_KEYS = [
        "no_reputation_key",
        "null_reputation",
        "empty_reputation_object",
    ]

    def test_host_datamodel_produces_no_reputation_fields(self) -> None:
        for key in self.EDGE_CASE_KEYS:
            model = HostDatamodel(REPUTATION_EDGE_CASES[key])
            enrichment = model.get_enrichment_data()
            rep_fields = {k: v for k, v in enrichment.items() if "reputation" in k}
            assert rep_fields == {}, f"{key} leaked reputation fields: {rep_fields}"
            # The host's other enrichment data (location/ASN) must still work.
            assert enrichment.get("Censys_location_country") == "Germany"

    def test_host_enrichment_datamodel_produces_no_reputation_fields(self) -> None:
        for key in self.EDGE_CASE_KEYS:
            model = HostEnrichmentDatamodel(REPUTATION_EDGE_CASES[key])
            enrichment = model.get_enrichment_data()
            rep_fields = {k: v for k, v in enrichment.items() if "reputation" in k}
            assert rep_fields == {}, f"{key} leaked reputation fields: {rep_fields}"
            assert enrichment.get("Censys_location_country") == "Germany"

    def test_no_reputation_tables_produced(self) -> None:
        for key in self.EDGE_CASE_KEYS:
            reputation = REPUTATION_EDGE_CASES[key]["result"]["resource"].get(
                "reputation"
            )
            ip = REPUTATION_EDGE_CASES[key]["result"]["resource"]["ip"]
            assert ReputationExtractor.get_summary_row(ip, reputation) is None
            assert ReputationExtractor.get_class_probability_rows(ip, reputation) == []
            assert ReputationExtractor.get_evidence_rows(ip, reputation) == []


class TestReputationMissingOptionalSubfields:
    """A single host missing label/score_suppressed/model_version at the top
    level, one class label missing "probability", and one evidence feature
    missing "value" - all in one realistic payload."""

    FIXTURE = REPUTATION_EDGE_CASES["missing_optional_subfields"]
    IP = "203.0.113.13"

    def test_entity_properties_omit_missing_label_but_keep_present_fields(
        self,
    ) -> None:
        model = HostDatamodel(self.FIXTURE)
        enrichment = model.get_enrichment_data()

        assert "Censys_reputation_label" not in enrichment
        assert enrichment["Censys_reputation_score_percent"] == 55.2

    def test_summary_table_falls_back_to_na_for_missing_fields(self) -> None:
        reputation = self.FIXTURE["result"]["resource"]["reputation"]
        row = ReputationExtractor.get_summary_row(self.IP, reputation)
        assert row == {
            "IP": self.IP,
            "Label": "N/A",
            "Score": 55.2,
            "Score Suppressed": "N/A",
        }

    def test_class_probability_missing_entry_renders_as_none_not_dropped(
        self,
    ) -> None:
        reputation = self.FIXTURE["result"]["resource"]["reputation"]
        rows = ReputationExtractor.get_class_probability_rows(self.IP, reputation)
        assert len(rows) == 5
        honeypot = next(r for r in rows if r["Label"] == "HONEYPOT")
        assert honeypot["Probability (%)"] == 0.06

    def test_evidence_missing_value_renders_as_none_not_dropped(self) -> None:
        reputation = self.FIXTURE["result"]["resource"]["reputation"]
        rows = ReputationExtractor.get_evidence_rows(self.IP, reputation)
        max_port_row = next(r for r in rows if r["Feature"] == "Max Port")
        assert max_port_row["Value"] is None


class TestReputationBackwardCompatibility:
    """The pre-existing thin reputation shape (score + score_level only,
    no label/evidence/class_probabilities) matches what production traffic
    looked like before this feature - Censys_reputation_score and
    Censys_reputation_score_level must resolve exactly as they did before."""

    FIXTURE = REPUTATION_EDGE_CASES["backward_compat_legacy_shape"]

    def test_legacy_fields_unchanged_via_host_enrichment_datamodel(self) -> None:
        model = HostEnrichmentDatamodel(self.FIXTURE)
        enrichment = model.get_enrichment_data()

        assert enrichment["Censys_reputation_score"] == 0.12
        assert enrichment["Censys_reputation_score_level"] == "benign"
        # New field added alongside, without disturbing the legacy ones.
        assert enrichment["Censys_reputation_score_percent"] == 12.0

    def test_no_new_structured_fields_when_absent_from_payload(self) -> None:
        model = HostEnrichmentDatamodel(self.FIXTURE)
        enrichment = model.get_enrichment_data()

        assert "Censys_reputation_label" not in enrichment
        assert "Censys_reputation_class_probabilities" not in enrichment
        assert "Censys_reputation_evidence" not in enrichment


class TestSixPlusEvidenceEntriesTruncatedToTop5:
    """Censys can return more than 5 evidence entries; only the top 5 by
    contribution should ever be surfaced, matching the reference Censys UI
    ("Evidence (5)" / "Top Signals") the customer asked us to match."""

    FIXTURE = REPUTATION_EDGE_CASES["six_plus_evidence_entries"]
    IP = "203.0.113.15"

    def test_eight_entries_reduced_to_top_five_by_contribution(self) -> None:
        reputation = self.FIXTURE["result"]["resource"]["reputation"]
        assert len(reputation["evidence"]) == 8  # sanity check on the fixture itself

        rows = ReputationExtractor.get_evidence_rows(self.IP, reputation)

        assert len(rows) == 5
        contributions = [r["Contribution (%)"] for r in rows]
        assert contributions == [11.23, 9.52, 8.91, 7.65, 6.88]

    def test_lowest_contribution_entries_are_dropped(self) -> None:
        reputation = self.FIXTURE["result"]["resource"]["reputation"]
        rows = ReputationExtractor.get_evidence_rows(self.IP, reputation)
        kept_features = {r["Feature"] for r in rows}

        # The 3 lowest-contribution features (Distinct Banner Hashes 5.03,
        # Distinct Ports 2.84, Max DNS Name Length 1.17) must not appear.
        assert "Distinct Banner Hashes" not in kept_features
        assert "Distinct Ports" not in kept_features
        assert "Max DNS Name Length" not in kept_features

    def test_entity_json_property_also_capped_at_five(self) -> None:
        model = HostDatamodel(self.FIXTURE)
        enrichment = model.get_enrichment_data()
        evidence = json.loads(enrichment["Censys_reputation_evidence"])
        assert len(evidence) == 5


class TestMultiIpMixedBatch:
    """One case/alert with 4 IPs in a single batch: full reputation, missing
    optional fields, no reputation key, and explicit null reputation. Only
    the first two should ever contribute rows to the combined tables; the
    other two must not appear anywhere and must not affect the batch's
    overall success."""

    IP_A_FULL = REPUTATION_MULTI_IP_BATCH["ip_a_full"]
    IP_B_MISSING_FIELDS = REPUTATION_MULTI_IP_BATCH["ip_b_missing_fields"]
    IP_C_NO_REPUTATION = REPUTATION_MULTI_IP_BATCH["ip_c_no_reputation"]
    IP_D_NULL_REPUTATION = REPUTATION_MULTI_IP_BATCH["ip_d_null_reputation"]

    ALL_FIXTURES = [
        IP_A_FULL,
        IP_B_MISSING_FIELDS,
        IP_C_NO_REPUTATION,
        IP_D_NULL_REPUTATION,
    ]

    def _reputation_and_ip(self, fixture: dict) -> tuple[dict | None, str]:
        resource = fixture["result"]["resource"]
        return resource.get("reputation"), resource["ip"]

    def test_all_four_ips_still_produce_other_enrichment_data(self) -> None:
        # A host with no/null reputation must still enrich normally on its
        # other fields - reputation is additive, never a gate.
        for fixture in self.ALL_FIXTURES:
            model = HostDatamodel(fixture)
            enrichment = model.get_enrichment_data()
            assert enrichment.get("Censys_asn_name"), (
                f"{fixture['result']['resource']['ip']} lost non-reputation "
                "enrichment data"
            )

    def test_only_two_of_four_ips_get_reputation_entity_properties(self) -> None:
        model_a = HostDatamodel(self.IP_A_FULL)
        model_b = HostDatamodel(self.IP_B_MISSING_FIELDS)
        model_c = HostDatamodel(self.IP_C_NO_REPUTATION)
        model_d = HostDatamodel(self.IP_D_NULL_REPUTATION)

        assert "Censys_reputation_label" in model_a.get_enrichment_data()
        assert "Censys_reputation_score_percent" in model_b.get_enrichment_data()
        assert not any(
            "reputation" in k for k in model_c.get_enrichment_data()
        )
        assert not any(
            "reputation" in k for k in model_d.get_enrichment_data()
        )

    def test_combined_summary_table_has_exactly_two_rows(self) -> None:
        rows = []
        for fixture in self.ALL_FIXTURES:
            reputation, ip = self._reputation_and_ip(fixture)
            row = ReputationExtractor.get_summary_row(ip, reputation)
            if row:
                rows.append(row)

        assert len(rows) == 2
        assert {r["IP"] for r in rows} == {"198.51.100.1", "198.51.100.2"}
        ip_a_row = next(r for r in rows if r["IP"] == "198.51.100.1")
        assert ip_a_row["Label"] == "MALICIOUS"
        assert ip_a_row["Score"] == 88.1

    def test_combined_class_probability_table_has_exactly_ten_rows(self) -> None:
        rows = []
        for fixture in self.ALL_FIXTURES:
            reputation, ip = self._reputation_and_ip(fixture)
            rows.extend(ReputationExtractor.get_class_probability_rows(ip, reputation))

        assert len(rows) == 10  # 5 labels x 2 IPs with reputation data
        assert {r["IP"] for r in rows} == {"198.51.100.1", "198.51.100.2"}

    def test_combined_evidence_table_has_exactly_four_rows(self) -> None:
        rows = []
        for fixture in self.ALL_FIXTURES:
            reputation, ip = self._reputation_and_ip(fixture)
            rows.extend(ReputationExtractor.get_evidence_rows(ip, reputation))

        # IP A contributes 3 evidence entries, IP B contributes 1 (with a
        # missing "value"); IPs C/D contribute none.
        assert len(rows) == 4
        assert all(r["IP"] in {"198.51.100.1", "198.51.100.2"} for r in rows)
        ip_b_row = next(r for r in rows if r["IP"] == "198.51.100.2")
        assert ip_b_row["Feature"] == "Max Port"
        assert ip_b_row["Value"] is None

    def test_no_row_anywhere_references_ips_without_reputation(self) -> None:
        no_reputation_ips = {"198.51.100.3", "198.51.100.4"}
        all_rows = []
        for fixture in self.ALL_FIXTURES:
            reputation, ip = self._reputation_and_ip(fixture)
            summary = ReputationExtractor.get_summary_row(ip, reputation)
            if summary:
                all_rows.append(summary)
            all_rows.extend(
                ReputationExtractor.get_class_probability_rows(ip, reputation)
            )
            all_rows.extend(ReputationExtractor.get_evidence_rows(ip, reputation))

        referenced_ips = {row["IP"] for row in all_rows}
        assert referenced_ips.isdisjoint(no_reputation_ips)
