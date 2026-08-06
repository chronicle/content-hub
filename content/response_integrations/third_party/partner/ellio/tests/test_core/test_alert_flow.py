from __future__ import annotations

from ...core.alert_flow import flow_footer_html, relations_for


class FakeRelation:
    def __init__(self, from_identifier: str, to_identifier: str) -> None:
        self.from_identifier = from_identifier
        self.to_identifier = to_identifier


class FakeAlert:
    def __init__(self, relations: list) -> None:
        self.relations = relations


class FakeSiemplify:
    def __init__(self, alert) -> None:
        self.current_alert = alert


def test_relations_for_source_role():
    siemplify = FakeSiemplify(FakeAlert([FakeRelation("27.43.204.10", "203.0.113.7")]))
    role, flows = relations_for(siemplify, "27.43.204.10")
    assert role == "source"
    assert flows == [("27.43.204.10", "203.0.113.7")]


def test_relations_for_both_roles_and_dedup():
    relations = [
        FakeRelation("27.43.204.10", "203.0.113.7"),
        FakeRelation("27.43.204.10", "203.0.113.7"),   # duplicate pair collapses
        FakeRelation("203.0.113.7", "27.43.204.10"),
    ]
    siemplify = FakeSiemplify(FakeAlert(relations))
    role, flows = relations_for(siemplify, "27.43.204.10")
    assert role == "source & destination"
    assert flows == [("27.43.204.10", "203.0.113.7"), ("203.0.113.7", "27.43.204.10")]


def test_relations_for_uninvolved_ip():
    siemplify = FakeSiemplify(FakeAlert([FakeRelation("198.51.100.1", "203.0.113.7")]))
    role, flows = relations_for(siemplify, "27.43.204.10")
    assert role == ""
    assert flows == []


def test_flow_footer_empty_without_flows():
    assert flow_footer_html("27.43.204.10", []) == ""


def test_flow_footer_renders_flows_and_overflow():
    flows = [(f"192.0.2.{i}", "203.0.113.7") for i in range(1, 6)]
    html = flow_footer_html("203.0.113.7", flows)
    assert "In this alert:" in html
    assert "192.0.2.1" in html
    assert "+2 more" in html                     # 5 flows, 3 shown
