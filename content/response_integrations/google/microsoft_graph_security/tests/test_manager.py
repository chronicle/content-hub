import json
import os

import pytest

from core.datamodels import Incident

# Constants
_MOCK_FILE = os.path.join(os.path.dirname(__file__), "mock_data.json")
with open(_MOCK_FILE, encoding="UTF-8") as f:
    MOCK_DATA = json.loads(f.read())


@pytest.mark.parametrize(
    "alert_id, comment",
    [("daec919a5f-df0c-4da0-b888-628b19c20f70_1", "Hello")],
)
def test_add_comment(
    microsoft_graph_security_manager, mocker, alert_id, comment
):
    mock_post = mocker.Mock()
    mocker.patch(
        (
            "tests.core.session."
            "MicrosoftGraphSecuritySession.post"
        ),
        return_value=mock_post,
    )
    result = microsoft_graph_security_manager.add_comment_to_alert(alert_id, comment)

    assert result is None


@pytest.mark.parametrize("incident_id", [115142000000219090])
def test_get_ticket(
    microsoft_graph_security_manager,
    mocker,
    incident_id,
):
    res = mocker.spy(
        microsoft_graph_security_manager.parser,
        "build_siemplify_incident_obj"
    )
    mock_data = MOCK_DATA.get("incident")
    mock_get = mocker.Mock()
    mock_get.json.return_value = mock_data
    mocker.patch(
        (
            "tests.core.session."
            "MicrosoftGraphSecuritySession.get"
        ),
        return_value=mock_get,
    )
    incident_data = microsoft_graph_security_manager.get_incident(
        incident_id=incident_id
    )
    mock_incident = Incident(
        raw_data=incident_data,
        incident_id=mock_data.get("id"),
        display_name=mock_data.get("displayName"),
        description=mock_data.get("description"),
        summary=mock_data.get("summary"),
        system_tags=mock_data.get("systemTags"),
        status=mock_data.get("status"),
        severity=mock_data.get("severity"),
        assigned_to=mock_data.get("assignedTo"),
        comments=mock_data.get("comments"),
        created_date_time=mock_data.get("createdDateTime"),
        last_update_date_time=mock_data.get("lastUpdateDateTime"),
    )

    assert mock_incident.incident_id == incident_data.incident_id
    assert mock_incident.display_name == incident_data.display_name
    assert mock_incident.system_tags == incident_data.system_tags
    assert mock_incident.created_date_time == incident_data.created_date_time
    assert mock_incident.comments == incident_data.comments
    assert mock_incident.description == incident_data.description
    assert res.call_count == 1


@pytest.mark.parametrize("key, logic", [("Not Specified", "Not Specified")])
def test_list_ticket(
    microsoft_graph_security_manager,
    mocker,
    key,
    logic,
):
    res = mocker.spy(
        microsoft_graph_security_manager.parser,
        "build_siemplify_incident_obj"
    )
    mock_data = MOCK_DATA.get("list_incidents")
    mock_get = mocker.Mock()
    mock_get.json.return_value = mock_data
    mocker.patch(
        (
            "tests.core.session."
            "MicrosoftGraphSecuritySession.get"
        ),
        return_value=mock_get,
    )
    filter_dict = {
        "key": key,
        "logic": logic,
        "value": "",
    }
    incident_list = microsoft_graph_security_manager.list_incidents(
        filter_dict=filter_dict
    )
    mock_incident = Incident(
        raw_data=incident_list,
        incident_id=mock_data.get("value")[0].get("id"),
        display_name=mock_data.get("value")[0].get("displayName"),
        description=mock_data.get("value")[0].get("description"),
        summary=mock_data.get("value")[0].get("summary"),
        system_tags=mock_data.get("value")[0].get("systemTags"),
        status=mock_data.get("value")[0].get("status"),
        severity=mock_data.get("value")[0].get("severity"),
        assigned_to=mock_data.get("value")[0].get("assignedTo"),
        comments=mock_data.get("value")[0].get("comments"),
        created_date_time=mock_data.get("value")[0].get("createdDateTime"),
        last_update_date_time=mock_data.get("value")[0].get("lastUpdateDateTime"),
    )

    assert mock_incident.incident_id == incident_list[0].incident_id
    assert mock_incident.display_name == incident_list[0].display_name
    assert mock_incident.system_tags == incident_list[0].system_tags
    assert mock_incident.created_date_time == incident_list[0].created_date_time
    assert mock_incident.comments == incident_list[0].comments
    assert mock_incident.description == incident_list[0].description
    assert res.call_count == 2
