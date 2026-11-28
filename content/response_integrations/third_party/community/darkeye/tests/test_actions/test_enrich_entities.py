from __future__ import annotations

import datetime
import json

from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.types import Entity, SingleJson

from darkeye.actions import enrich_entities
from darkeye.tests.common import CONFIG, CONFIG_PATH, HAVEIBEENRANSOM_ONLY_CONFIG, load_mock
from darkeye.tests.core.product import DarkEye
from darkeye.tests.core.session import DarkEyeSession

DOMAIN: str = "example.com"
EMAIL: str = "bob@example.com"
DOMAIN_ENTITY: Entity = create_entity(DOMAIN, EntityTypesEnum.DOMAIN)
EMAIL_ENTITY: Entity = create_entity(EMAIL, EntityTypesEnum.USER)
USERNAME_ENTITY: Entity = create_entity("bob", EntityTypesEnum.USER)
WILDCARD_ENTITY: Entity = create_entity("*.example.com", EntityTypesEnum.DOMAIN)
DEADLINE: datetime.datetime = datetime.datetime.now() + datetime.timedelta(minutes=10)
INPUT_CONTEXT: SingleJson = {"execution_deadline_unix_time_ms": int(DEADLINE.timestamp() * NUM_OF_MILLI_IN_SEC)}
HAVEIBEENRANSOM_MOCK: SingleJson = load_mock("haveibeenransom.json")
BREACH_HOUSE_MOCK: SingleJson = load_mock("breach_house.json")


def set_domain_data(darkeye: DarkEye) -> None:
    darkeye.set_haveibeenransom_pages("domain", DOMAIN, HAVEIBEENRANSOM_MOCK["domain_pages"])
    darkeye.set_breach_house_search(DOMAIN, BREACH_HOUSE_MOCK["domain"])


def entity_results(action_output: MockActionOutput) -> dict[str, SingleJson]:
    json_result = action_output.results.json_output.json_result
    return {item["Entity"]: item["EntityResult"] for item in json_result}


def requests_to(session: DarkEyeSession, host: str) -> list:
    return [record.request for record in session.request_history if record.request.url.netloc == host]


def product_paths(session: DarkEyeSession) -> list[str]:
    """Paths sent to the products, without the SDK's own calls to the platform."""
    return [
        record.request.url.path
        for record in session.request_history
        if record.request.url.netloc in {"haveibeenransom.com", "breach.house"}
    ]


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    entities=[DOMAIN_ENTITY],
    input_context=dict(INPUT_CONTEXT),
)
def test_enrich_domain_with_both_products(
    script_session: DarkEyeSession,
    action_output: MockActionOutput,
    darkeye: DarkEye,
) -> None:
    set_domain_data(darkeye)

    enrich_entities.main()

    haveibeenransom = requests_to(script_session, "haveibeenransom.com")
    breach_house = requests_to(script_session, "breach.house")
    assert [request.url.path for request in haveibeenransom] == [
        "/api/metadata/domain/example.com",
        "/api/metadata/domain/example.com/2",
    ]
    assert [request.url.path for request in breach_house] == ["/api/v1/search"]
    assert breach_house[0].kwargs["params"] == {"q": DOMAIN, "limit": 25}
    assert all(
        request.kwargs["headers"] == {"Authorization": f"Bearer {CONFIG['HaveIBeenRansom API Key']}"}
        for request in haveibeenransom
    )
    assert breach_house[0].kwargs["headers"] == {"Authorization": f"Bearer {CONFIG['Breach House API Key']}"}

    result: SingleJson = entity_results(action_output)[DOMAIN]
    assert result["found"] is True
    assert result["count"] == 7
    assert result["products"] == ["HaveIBeenRansom", "Breach House"]
    assert result["counts_by_product"] == {"HaveIBeenRansom": 3, "Breach House": 4}
    assert result["counts_by_category"] == {"ransomware": 3, "breach": 2, "leak": 1, "stealer": 1}
    assert result["truncated"] is False
    assert result["errors"] == []
    assert [(record["product"], record["category"], record["id"]) for record in result["records"]] == [
        ("HaveIBeenRansom", "ransomware", "1001"),
        ("HaveIBeenRansom", "breach", "1002"),
        ("HaveIBeenRansom", "leak", "1003"),
        ("Breach House", "ransomware", "AbCdEf123456"),
        ("Breach House", "ransomware", "MnOpQr345678"),
        ("Breach House", "breach", "b-77"),
        ("Breach House", "stealer", "s-9"),
    ]
    assert result["records"][0] == {
        "product": "HaveIBeenRansom",
        "category": "ransomware",
        "id": "1001",
        "title": "Example Corp",
        "website": "example.com",
        "group": "examplegroup",
        "country": "US",
        "discovered": "2026-01-15",
    }
    # Leak-site links and leaked content are never copied into the result.
    raw: str = json.dumps(result)
    assert ".onion" not in raw
    assert "Not kept by the integration" not in raw

    assert action_output.results.output_message == (
        "Successfully enriched the following entities using DarkEye: example.com\n"
        "DarkEye found records for the following entities: example.com"
    )
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    entities=[EMAIL_ENTITY],
    input_context=dict(INPUT_CONTEXT),
)
def test_enrich_email_keeps_only_exact_address_matches(
    script_session: DarkEyeSession,
    action_output: MockActionOutput,
    darkeye: DarkEye,
) -> None:
    darkeye.set_haveibeenransom_pages("email", EMAIL, HAVEIBEENRANSOM_MOCK["email_pages"])
    darkeye.set_breach_house_search(EMAIL, BREACH_HOUSE_MOCK["email"])

    enrich_entities.main()

    paths = product_paths(script_session)
    assert paths == ["/api/metadata/email/bob@example.com", "/api/v1/search"]
    result: SingleJson = entity_results(action_output)[EMAIL]
    assert result["entity_type"] == "email"
    assert [(record["product"], record["id"]) for record in result["records"]] == [
        ("HaveIBeenRansom", "1001"),
        ("Breach House", "b-90"),
    ]
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    entities=[USERNAME_ENTITY],
    input_context=dict(INPUT_CONTEXT),
)
def test_user_entity_that_is_not_an_email_is_skipped(
    script_session: DarkEyeSession,
    action_output: MockActionOutput,
) -> None:
    enrich_entities.main()

    assert not product_paths(script_session)
    assert action_output.results.output_message == "None of the provided entities were enriched."
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    entities=[DOMAIN_ENTITY],
    input_context=dict(INPUT_CONTEXT),
)
def test_one_product_failing_keeps_the_other_results(
    action_output: MockActionOutput,
    darkeye: DarkEye,
) -> None:
    set_domain_data(darkeye)
    darkeye.fail("Breach House", 429)

    enrich_entities.main()

    result: SingleJson = entity_results(action_output)[DOMAIN]
    assert result["products"] == ["HaveIBeenRansom"]
    assert result["counts_by_product"] == {"HaveIBeenRansom": 3}
    assert result["errors"] == [
        {"product": "Breach House", "error": "Breach House: quota or rate limit reached; retry later."}
    ]
    assert "Some products failed for the following entities: example.com" in action_output.results.output_message
    assert action_output.results.result_value is True


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    entities=[DOMAIN_ENTITY],
    input_context=dict(INPUT_CONTEXT),
)
def test_every_product_failing_is_not_an_empty_result(
    action_output: MockActionOutput,
    darkeye: DarkEye,
) -> None:
    darkeye.fail("HaveIBeenRansom", 500)
    darkeye.fail("Breach House", 403)

    enrich_entities.main()

    message: str = action_output.results.output_message
    assert message.startswith("None of the provided entities were enriched.")
    assert "Action wasn't able to enrich the following entities using DarkEye: example.com" in message
    assert "HaveIBeenRansom: returned HTTP 500." in message
    assert CONFIG["Breach House API Key"] not in message
    assert action_output.results.result_value is False


@set_metadata(
    integration_config=HAVEIBEENRANSOM_ONLY_CONFIG,
    parameters={"Max Pages": "1"},
    entities=[DOMAIN_ENTITY],
    input_context=dict(INPUT_CONTEXT),
)
def test_page_limit_marks_the_result_as_truncated(
    script_session: DarkEyeSession,
    action_output: MockActionOutput,
    darkeye: DarkEye,
) -> None:
    set_domain_data(darkeye)

    enrich_entities.main()

    assert product_paths(script_session) == ["/api/metadata/domain/example.com"]
    result: SingleJson = entity_results(action_output)[DOMAIN]
    assert result["products"] == ["HaveIBeenRansom"]
    assert result["count"] == 2
    assert result["truncated"] is True
    assert "More records exist than were read" in action_output.results.output_message


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={"Max Records": "2"},
    entities=[DOMAIN_ENTITY],
    input_context=dict(INPUT_CONTEXT),
)
def test_record_limit_applies_per_product(
    action_output: MockActionOutput,
    darkeye: DarkEye,
) -> None:
    set_domain_data(darkeye)

    enrich_entities.main()

    result: SingleJson = entity_results(action_output)[DOMAIN]
    assert result["counts_by_product"] == {"HaveIBeenRansom": 2, "Breach House": 2}
    assert result["truncated"] is True


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    entities=[WILDCARD_ENTITY],
    input_context=dict(INPUT_CONTEXT),
)
def test_wildcard_domain_is_not_queried(
    script_session: DarkEyeSession,
    action_output: MockActionOutput,
) -> None:
    enrich_entities.main()

    assert not product_paths(script_session)
    assert "is not a plain domain name" in action_output.results.output_message
    assert action_output.results.result_value is False


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={"Limit": "abc"},
    entities=[DOMAIN_ENTITY],
    input_context=dict(INPUT_CONTEXT),
)
def test_invalid_number_parameter_fails(
    script_session: DarkEyeSession,
    action_output: MockActionOutput,
) -> None:
    enrich_entities.main()

    assert not product_paths(script_session)
    assert "'Limit' must be a positive whole number." in action_output.results.output_message
    assert action_output.results.execution_state == ExecutionState.FAILED
