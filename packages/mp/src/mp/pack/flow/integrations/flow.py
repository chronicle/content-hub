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

import logging
import pathlib
import tempfile
from typing import NamedTuple

from mp.core.file_utils import create_or_get_out_dir

from .beta import apply_beta_modifications
from .build import build_integration_for_pack, set_is_custom
from .components import interactive_component_selection
from .git import create_git_worktree, get_git_repo_root, remove_git_worktree
from .utils import create_zip, find_integration_src_path, is_tty

logger: logging.Logger = logging.getLogger(__name__)


class GitWorktreeContext(NamedTuple):
    """Context for a checked-out Git worktree."""

    context: tempfile.TemporaryDirectory
    path: pathlib.Path
    build_src: pathlib.Path


class PackConfig(NamedTuple):
    """Configuration options for packing an integration."""

    version: str | None = None
    beta_name: str | None = None
    zip_dst: pathlib.Path | None = None
    interactive: bool = True


class IntegrationPacker:
    """Manages the packing flow of an integration."""

    def __init__(self, integration_name: str, config: PackConfig) -> None:
        """Initialize the packer.

        Args:
            integration_name: The name of the integration to pack.
            config: Configuration options for packing.

        """
        self.integration_name: str = integration_name
        self.config: PackConfig = config

    def pack(self) -> None:
        """Execute the packing flow."""
        src_path, resolved_name = find_integration_src_path(self.integration_name)
        self.integration_name = resolved_name
        repo_root: pathlib.Path = get_git_repo_root(src_path)

        worktree_ctx: GitWorktreeContext | None = None
        build_src: pathlib.Path = src_path

        if self.config.version is not None:
            worktree_ctx = self._checkout_version_from_git(src_path, repo_root, self.config.version)
            build_src = worktree_ctx.build_src

        try:
            self._build_and_process_integration(build_src)
        finally:
            if worktree_ctx:
                logger.debug("Cleaning up temporary Git worktree...")
                remove_git_worktree(worktree_ctx.path, repo_root)
                worktree_ctx.context.cleanup()

    def _checkout_version_from_git(
        self, src_path: pathlib.Path, repo_root: pathlib.Path, version: str
    ) -> GitWorktreeContext:
        """Check out a specific version from git into a temporary worktree.

        Args:
            src_path: The source path.
            repo_root: The git repo root.
            version: The version to check out.

        Returns:
            GitWorktreeContext: The worktree context, path, and build source path.

        """
        logger.info("Fetching version %s via Git...", version)
        temp_ctx = tempfile.TemporaryDirectory(prefix=f"mp_worktree_{self.integration_name}_{version}_")
        temp_path = pathlib.Path(temp_ctx.name)
        create_git_worktree(src_path, version, temp_path)
        rel_path: pathlib.Path = src_path.relative_to(repo_root)
        build_src: pathlib.Path = temp_path / rel_path
        logger.info("Checked out version %s to temporary worktree.", version)
        return GitWorktreeContext(temp_ctx, temp_path, build_src)

    def _build_and_process_integration(self, build_src: pathlib.Path) -> None:
        """Build the integration, apply modifications and package it.

        Args:
            build_src: Source path.

        Raises:
            RuntimeError: If an integration def file is not found.

        """
        logger.info("Building integration '%s'...", self.integration_name)
        with tempfile.TemporaryDirectory(prefix=f"mp_pack_{self.integration_name}_") as temp_build_dir:
            temp_build_path: pathlib.Path = pathlib.Path(temp_build_dir)

            build_integration_for_pack(self.integration_name, self.config.version, build_src, temp_build_path)

            def_files: list[pathlib.Path] = list(temp_build_path.rglob("Integration-*.def"))
            if not def_files:
                msg: str = f"Build failed: No Integration-*.def found in {temp_build_path}"
                raise RuntimeError(msg)

            built_dir: pathlib.Path = def_files[0].parent
            identifier: str = built_dir.name

            set_is_custom(def_files[0])

            if self.config.beta_name:
                logger.info("Applying custom beta identifier '%s'...", self.config.beta_name)
                apply_beta_modifications(built_dir, identifier, self.config.beta_name, self.config.version)
                identifier = self.config.beta_name

            if self.config.interactive and is_tty():
                interactive_component_selection(built_dir)
            elif self.config.interactive:
                logger.info("Non-TTY environment detected. Skipping interactive component selection (including all).")

            zip_dst = self.config.zip_dst
            if zip_dst is None:
                zip_dst = create_or_get_out_dir() / "pack"
            zip_dst.mkdir(parents=True, exist_ok=True)

            zip_path: pathlib.Path = create_zip(built_dir, identifier, zip_dst)
            logger.info("Successfully created integration zip: %s", zip_path)


def pack_integration(
    integration_name: str,
    *,
    version: str | None = None,
    beta_name: str | None = None,
    zip_dst: pathlib.Path | None = None,
    interactive: bool = True,
) -> None:
    """Flow for packing an integration into a SOAR-supported ZIP.

    Args:
        integration_name: The name of the integration to pack.
        version: Old version to fetch from the repo and create the ZIP.
        beta_name: Name of the custom beta integration.
        zip_dst: Destination directory to save the ZIP file.
        interactive: Enable or disable interactive component selection.

    """
    config = PackConfig(
        version=version,
        beta_name=beta_name,
        zip_dst=zip_dst,
        interactive=interactive,
    )
    packer = IntegrationPacker(integration_name, config)
    packer.pack()
