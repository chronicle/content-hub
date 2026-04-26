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

import io
from typing import TYPE_CHECKING

from mp.core import constants

from .job import JobPromptConstructor

if TYPE_CHECKING:
    from string import Template

    import anyio

DEFAULT_FILE_CONTENT: str = "N/A"


class BuiltPromptConstructor(JobPromptConstructor):
    __slots__: tuple[str, ...] = ()

    async def construct(self) -> str:
        """Construct the prompt for built jobs.

        Returns:
            str: The constructed prompt.

        """
        manager_names, manager_content = await self._get_managers_names_and_content()
        template: Template = await self.task_prompt
        return template.safe_substitute({
            "json_file_name": f"{self.resource_file_name}.json",
            "json_file_content": await self._get_built_job_def_content(),
            "python_file_name": f"{self.resource_file_name}.py",
            "python_file_content": await self._get_built_job_content(),
            "manager_file_names": manager_names or DEFAULT_FILE_CONTENT,
            "manager_files_content": manager_content or DEFAULT_FILE_CONTENT,
        })

    async def _get_managers_names_and_content(self) -> tuple[str, str]:
        names: list[str] = []
        content: io.StringIO = io.StringIO()
        managers_dir: anyio.Path = self.out_path / constants.OUT_MANAGERS_SCRIPTS_DIR
        if await managers_dir.exists():
            async for core_file in managers_dir.glob("*.py"):
                names.append(core_file.name)
                content.write("```python\n")
                content.write(await core_file.read_text(encoding="utf-8"))
                content.write("\n```\n\n")

        return ", ".join(names), content.getvalue()

    async def _get_built_job_def_content(self) -> str:
        job_def: anyio.Path = (
            self.out_path / constants.OUT_JOBS_META_DIR / f"{self.resource_file_name}{constants.JOBS_META_SUFFIX}"
        )
        if await job_def.exists():
            return await job_def.read_text(encoding="utf-8")

        return DEFAULT_FILE_CONTENT

    async def _get_built_job_content(self) -> str:
        job_script: anyio.Path = self.out_path / constants.OUT_JOB_SCRIPTS_DIR / f"{self.resource_file_name}.py"
        if await job_script.exists():
            return await job_script.read_text(encoding="utf-8")

        return DEFAULT_FILE_CONTENT
