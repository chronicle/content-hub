# Copyright 2025 Google LLC
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

import logging
import shutil
from typing import TYPE_CHECKING

import mp.core.config
import mp.core.file_utils
import mp.core.utils
from mp.core.data_models.playbooks.playbook import Playbook

from .restructure.playbooks.build import PlaybookBuilder
from .restructure.playbooks.deconstruct import PlaybookDeconstructor

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


logger: logging.Logger = logging.getLogger(__name__)


class PlaybooksRepo:
    def __init__(self, playbook_repository_path: Path, dst: Path | None = None, *, default_src: bool = True) -> None:
        self.name: str = playbook_repository_path.name
        if default_src:
            self.base_folders: list[Path] = mp.core.file_utils.get_playbook_base_folders_paths(
                playbook_repository_path.name, playbook_repository_path
            )
        else:
            self.base_folders: list[Path] = [playbook_repository_path]

        for dir_name in self.base_folders:
            dir_name.mkdir(exist_ok=True, parents=True)

        if dst is None:
            self.out_dir: Path = mp.core.file_utils.get_playbook_out_dir()
        else:
            self.out_dir = dst
        self.out_dir.mkdir(exist_ok=True, parents=True)

    def build_playbooks(self, playbook_paths: Iterable[Path]) -> None:
        """Build all playbooks provided by `playbook_paths`.

        Args:
            playbook_paths: The paths of playbooks to build

        """
        paths: list[Path] = [p for p in playbook_paths if p.exists()]
        processes: int = mp.core.config.get_processes_number()

        mp.core.utils.run_in_parallel(
            func=self.build_playbook,
            items=paths,
            max_workers=processes,
            error_message_template="Failed to build playbook '%s'",
        )

    def build_playbook(self, playbook_path: Path) -> None:
        """Build a single playbook provided by `playbook_path`.

        Args:
            playbook_path: The path of the playbook to build.

        Raises:
            FileNotFoundError: If `playbook_path` does not exist.

        """
        if not playbook_path.exists():
            msg: str = f"Invalid playbook {playbook_path}"
            raise FileNotFoundError(msg)

        self._build_playbook(playbook_path)

    def _build_playbook(self, playbook_path: Path) -> None:
        if mp.core.file_utils.is_built_playbook(playbook_path):
            logger.info("---------- Playbook %s is already built ----------", playbook_path.name)
            self.out_dir.mkdir(exist_ok=True)
            shutil.copy(playbook_path, self.out_dir / playbook_path.name)
            return

        logger.info("---------- Building %s ----------", playbook_path.stem)
        playbook: Playbook = Playbook.from_non_built_path(playbook_path)
        build_playbook: PlaybookBuilder = PlaybookBuilder(playbook, playbook_path, self.out_dir)
        build_playbook.build()
        logger.info("----------Done Building %s ----------", playbook_path.stem)

    def deconstruct_playbooks(self, playbooks_paths: Iterable[Path]) -> None:
        """Deconstruct all playbooks provided by `integration_paths`.

        Args:
            playbooks_paths: The paths of playbook to deconstruct

        """
        paths: list[Path] = [p for p in playbooks_paths if p.exists()]
        processes: int = mp.core.config.get_processes_number()

        mp.core.utils.run_in_parallel(
            func=self.deconstruct_playbook,
            items=paths,
            max_workers=processes,
            error_message_template="Failed to deconstruct playbook '%s'",
        )

    def deconstruct_playbook(self, playbook_path: Path) -> None:
        """Deconstruct a single playbook provided by `playbook_path`.

        Args:
            playbook_path: The path of the playbook to deconstruct.

        Raises:
            FileNotFoundError: If `playbook_path` does not exist.

        """
        if not playbook_path.exists():
            msg: str = f"Invalid playbook {playbook_path}"
            raise FileNotFoundError(msg)

        playbook_out_path: Path = self.out_dir / playbook_path.stem.lower()
        playbook_out_path.mkdir(exist_ok=True)
        _deconstruct_playbook(playbook_path, playbook_out_path)


def _deconstruct_playbook(playbook_path: Path, playbook_out_path: Path) -> None:
    if mp.core.file_utils.is_non_built_playbook(playbook_path):
        logger.info("---------- Playbook %s is already deconstructed ----------", playbook_path.name)
        mp.core.file_utils.recreate_dir(playbook_out_path)
        shutil.copytree(playbook_path, playbook_out_path, dirs_exist_ok=True)
        return

    logger.info("---------- Deconstructing %s ----------", playbook_path.stem)
    playbook: Playbook = Playbook.from_built_path(playbook_path)
    deconstruct_playbook: PlaybookDeconstructor = PlaybookDeconstructor(playbook, playbook_out_path)
    deconstruct_playbook.deconstruct()
    logger.info("----------Done Deconstructing %s ----------", playbook_path.stem)
