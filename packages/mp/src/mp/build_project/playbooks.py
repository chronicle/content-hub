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

import multiprocessing
from pathlib import Path

from mp.core.file_utils import get_playbooks_dir_path, create_or_get_playbook_out_dir
import mp.core.config


class Playbooks:
    def __init__(self, playbooks_dir: Path) -> None:
        """Class constructor.

        Args:
            playbooks_dir: The path to a marketplace's playbooks folder.

        """
        self.name: str = playbooks_dir.name
        self.paths: list[Path] = get_playbooks_dir_path()
        self.out_dir: Path = create_or_get_playbook_out_dir()

    def build_playbooks(self) -> None:
        """Build all playbooks in the marketplace."""

        processes: int = mp.core.config.get_processes_number()
        for playbook in self.paths:
            pass
