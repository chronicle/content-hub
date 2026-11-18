# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from abc import ABC, abstractmethod

from TIPCommon.base.action import Action
from TIPCommon.data_models import Container

from .GKEServices import GKEBaseService
from .GKEAuth import build_auth_manager
from .GKEManagers import GKEApiManager


class GKEBaseAction(Action, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._auth_params = Container()
        self._gke_service_class = GKEBaseService
        self._service_params = Container()

    def _init_managers(self) -> GKEBaseService:
        auth_manager = build_auth_manager(self.soar_action)
        api_manager = GKEApiManager(
            auth_manager.api_root,
            auth_manager.prepare_session(),
            project_id=(
                getattr(self._service_params, "target_project_id", None)
                or auth_manager.project_id
            ),
            location_id=auth_manager.location_id
        )
        return self._gke_service_class(
            api_manager=api_manager, logger=self.logger, **self._service_params.__dict__
        )

    def _extract_parameters(self) -> None:
        self._extract_service_params()
        self._extract_action_params()

    @abstractmethod
    def _extract_action_params(self) -> None:
        pass

    def _extract_service_params(self) -> None:
        pass
