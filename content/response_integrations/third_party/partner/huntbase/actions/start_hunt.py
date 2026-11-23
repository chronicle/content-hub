from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.base.action.data_models import Link
from TIPCommon.extraction import extract_action_param

from ..core import constants
from ..core.base_action import HuntbaseAction
from ..core.utils import entity_value, external_ref, guess_value_type, is_http_url, seed_values_from_entities

if TYPE_CHECKING:
    from typing import NoReturn


class StartHunt(HuntbaseAction):
    """Start a Huntbase hunt seeded with the case's entities."""

    def __init__(self) -> None:
        super().__init__(constants.START_HUNT_SCRIPT_NAME)
        self.error_output_message = f'Error executing action "{constants.START_HUNT_SCRIPT_NAME}"'

    def _extract_action_parameters(self) -> None:
        self.params.title = extract_action_param(self.soar_action, param_name="Title", print_value=True)
        self.params.hypothesis = extract_action_param(self.soar_action, param_name="Hypothesis", print_value=True)
        self.params.session_mode = extract_action_param(
            self.soar_action,
            param_name="Session Mode",
            default_value=constants.DEFAULT_HUNT_SESSION_MODE,
            print_value=True,
        )
        self.params.severity = extract_action_param(self.soar_action, param_name="Severity", print_value=True)
        self.params.additional_values = extract_action_param(
            self.soar_action,
            param_name="Additional Seed Values",
            print_value=True,
        )
        self.params.case_link = extract_action_param(self.soar_action, param_name="Case Link", print_value=True)
        self.params.reuse_open = extract_action_param(
            self.soar_action,
            param_name="Reuse Open Hunt",
            input_type=bool,
            default_value=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        mode = (self.params.session_mode or "").strip().lower()
        if mode not in constants.HUNT_SESSION_MODES:
            msg = f"Session Mode must be one of: {', '.join(constants.HUNT_SESSION_MODES)}."
            raise ValueError(msg)
        self.params.session_mode = mode
        if self.params.severity:
            self.params.severity = self.params.severity.strip().lower()
        self.params.case_link = (self.params.case_link or "").strip() or None
        if self.params.case_link and not is_http_url(self.params.case_link):
            msg = "Case Link must be an absolute http(s) URL."
            raise ValueError(msg)

    def _perform_action(self, _: object) -> None:
        seeds = seed_values_from_entities(self.soar_action.target_entities)
        for raw in (self.params.additional_values or "").split(","):
            value = raw.strip()
            if value and all(seed["value"].lower() != value.lower() for seed in seeds):
                seeds.append({"type": guess_value_type(value), "value": value})
        if not seeds:
            msg = (
                "No seeds for the hunt: the case has no IP, domain, URL, hash, hostname or user "
                "entities and no Additional Seed Values were given."
            )
            raise ValueError(msg)
        if len(seeds) > constants.MAX_HUNT_SEED_VALUES:
            self.logger.info(
                f"{len(seeds)} seed values found; Huntbase takes the first {constants.MAX_HUNT_SEED_VALUES}."
            )
            seeds = seeds[: constants.MAX_HUNT_SEED_VALUES]

        title = self.params.title or self._default_title()
        hunt = self.manager.start_hunt(
            seed_values=seeds,
            title=title,
            hypothesis=self.params.hypothesis,
            session_mode=self.params.session_mode,
            severity=self.params.severity,
            external_ref=external_ref(self.soar_action, self.params.case_link, title),
            reuse_open=self.params.reuse_open,
        )
        self.json_results = {
            "hunt_id": hunt.hunt_id,
            "title": hunt.title,
            "status": hunt.status,
            "session_mode": self.params.session_mode,
            "seed_values": seeds,
            "seed_resolution": hunt.raw_data.get("seed_values"),
            "url": hunt.url,
        }
        self.links.append(Link(link=hunt.url, title=f"Huntbase hunt: {hunt.title or hunt.hunt_id}"))
        self.result_value = True
        self.output_message = (
            f"Successfully {'reopened' if hunt.status == 'reopened' else 'started'} Huntbase hunt "
            f"{hunt.hunt_id} with {len(seeds)} seed value(s). "
            f"Follow it with Get Hunt or open {hunt.url}"
        )

    def _default_title(self) -> str:
        case_id = getattr(self.soar_action, "case_id", None)
        first = next(iter(self.soar_action.target_entities), None)
        subject = entity_value(first) if first is not None else "case entities"
        return f"Google SecOps case {case_id}: {subject}" if case_id else f"Google SecOps: {subject}"


def main() -> NoReturn:
    StartHunt().run()


if __name__ == "__main__":
    main()
