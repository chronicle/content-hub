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

import json
import os
import shutil
import stat
from io import StringIO, IOBase
import sys
from typing import TYPE_CHECKING, Union, TextIO, Any
from urllib.parse import urlparse, urlunparse

import dulwich
import paramiko.rsakey
from dulwich import client as _mod_client
from dulwich import porcelain
from dulwich.contrib.paramiko_vendor import _ParamikoWrapper
from dulwich.contrib.requests_vendor import RequestsHttpGitClient
from dulwich.errors import GitProtocolError, HangupException
from dulwich.object_store import tree_lookup_path
from dulwich.objects import Blob, Commit, ShaFile, Tree
from dulwich.refs import HEADREF, LOCAL_BRANCH_PREFIX
from dulwich.repo import Repo
from paramiko.ssh_exception import SSHException
import hashlib
import base64
import paramiko.ed25519key


from .definitions import File, Metadata

if TYPE_CHECKING:
    from soar_sdk.SiemplifyLogger import SiemplifyLogger


PUSH_FAILURE_INDICATORS = (
        "pre-receive hook declined",
        "not allowed to push",
        "push rejected",
        "failed to push",
        "error: failed to push",
        "! [rejected]",
        "! [remote rejected]",
    )

class Git:
    """GitManager"""

    def __init__(
        self,
        repo_url: str,
        branch_name: str,
        working_directory: str,
        password: str,
        username: str,
        author: str,
        verify_ssl: bool,
        logger: SiemplifyLogger,
        git_server_fingerprint: str,
    ):
        """Wrapper for dulwich - a pure python git client.

        Args:
            repo_url (str): repository url. SSH and HTTP urls are supported
            branch_name (str): name of the target branch to push or pull changes from
            working_directory (str): path to local directory to clone or store the repo
            password (str): Api token, SSH key (base64 encoded) or user's password
            username (str): Username. Not used when connecting to a repo using SSH
            author (str): Commit author. Must be in the following format: James Bond
            <james.bond@gmail.com>
            verify_ssl (bool): Whether to verify SSL with the git provider
            logger (Logger): A logger instance
            git_server_fingerprint: SSH fingerprint for verification (SHA256:... or MD5:...)

        """
        self.logger = logger
        self.repo_url = repo_url
        self.branch_name = branch_name.encode("utf-8")
        self.local_branch_ref = b"refs/heads/" + self.branch_name
        self.remote_branch_ref = b"refs/remotes/origin/" + self.branch_name
        self.wd = working_directory
        self.username = username
        self.password = password
        self.author = author.encode("utf-8")
        self.verify_ssl = verify_ssl
        self.git_server_fingerprint = git_server_fingerprint

        self.modify_dulwich_client(logger, git_server_fingerprint)

        if self.repo_url.startswith("ssh://") or self.repo_url.startswith("git@"):
            # When using ssh - the username is ignored
            self.connection_args = {
                "password": self.convert_password_to_private_key(),
                "git_server_fingerprint": git_server_fingerprint,
                "siemplify_logger": self.logger,
            }
        elif "bitbucket.org" in self.repo_url and "x-token-auth" not in self.repo_url:
            parsed = urlparse(self.repo_url)
            netloc = f"x-token-auth:{self.password}@{parsed.hostname}"
            self.repo_url = urlunparse(parsed._replace(netloc=netloc))
            self.connection_args = {
                "siemplify_logger": self.logger,
                "git_server_fingerprint": git_server_fingerprint,
            }

        else:
            self.connection_args = {
                "username": self.username,
                "password": self.password,
                "siemplify_logger": self.logger,
                "git_server_fingerprint": git_server_fingerprint,
            }

        # Check if the git repo is present and pull changes. Otherwise, clone the repo.
        if os.path.isdir(self.wd) and os.path.isdir(os.path.join(self.wd, ".git")):
            self.repo = Repo(self.wd)
            config = self.repo.get_config()
            if config.get_boolean(b"http", b"sslVerify") != self.verify_ssl:
                self.logger.info("Git Verify SSL parameter changed. Writing new value")
                config.set(
                    b"http",
                    b"sslVerify",
                    b"true" if self.verify_ssl else b"false",
                )
                config.write_to_path()
            self.logger.info("Found existing repo. Pulling Repo Changes")
            self.pull()
        else:
            self.logger.info(f"Couldn't find repo. Cloning from {self.repo_url}")
            self._clone()

        if self.local_branch_ref != self.repo.refs.get_symrefs()[HEADREF]:
            self.logger.info(
                f"Git branch parameter changed, checking out branch "
                f"{self.branch_name.decode()}",
            )
            # Branch changed, checking out
            self._checkout()

        self.tree: Tree = self.get_head_tree()

    @staticmethod
    def modify_dulwich_client(logger: SiemplifyLogger, git_server_fingerprint: str, ):
        # dulwich patch to add requests support : https://github.com/jelmer/dulwich/pull/933
        _mod_client.HttpGitClient = RequestsHttpGitClient
        # dulwich patch to add paramiko support (can't pass pkey parameter)
        _mod_client.get_ssh_vendor = lambda **kwargs: SiemplifyParamikoSSHVendor(
            siemplify_logger=logger,
            git_server_fingerprint=git_server_fingerprint or "",
            **{
                k: v
                for k, v in kwargs.items()
                if k not in {"git_server_fingerprint", "siemplify_logger"}
            },
        )
        # dulwich patch to newer paramiko versions returning string and not bytes
        _mod_client._remote_error_from_stderr = remote_error_from_stderr

    @property
    def head(self) -> Commit:
        """Current repo HEAD commit

        Returns:
            Commit: the HEAD commit object

        """
        # noinspection PyTypeChecker
        return self.repo.get_object(self.repo.get_refs()[HEADREF])

    def get_head_tree(self) -> Tree | ShaFile:
        return self.repo.get_object(self.head.tree)

    @property
    def branch_tree(self) -> Tree:
        """Get the current branch tree.
        Used to diff between self.tree to see if any changes where made.

        Returns:
            Tree: Current branch tree

        """
        branch_sha = self.repo.get_refs()[self.local_branch_ref]
        # noinspection PyTypeChecker
        return self.repo.get_object(self.repo.get_object(branch_sha).tree)

    def commit_and_push(self, message: str) -> None:
        """Create a commit and push based on current tree

        Args:
            message (str): Commit message

        """
        if self.branch_tree.id != self.tree.id:
            self.logger.info(f"Committing tree {self.tree.id} with message {message}")
            self.repo.do_commit(
                tree=self.tree.id,
                message=message.encode("utf-8"),
                committer=self.author,
                author=self.author,
            )
            self.push()
        else:
            self.logger.info("No changes found. Nothing to commit.")

    def pull(self) -> None:
        """Pulls changes from the repo. We ignore conflicts and reset local repo to
        the origin one.
        """
        remote_refs = porcelain.fetch(self.repo, **self.connection_args, depth=1)
        for key, value in list(remote_refs.items()):
            self.repo.refs[key] = value

    def push(self, force_push=False) -> None:
        """Push current branch to the repo

        Args:
            force_push (bool, optional): If set to True, the push will overwrite
            remote objects,
            equivalent to 'git push --force'. Defaults to False.

        """
        error_content = ""
        try:
            error_buffer = StringIO()
            tee_stream = TeeStream(sys.stderr, error_buffer)

            try:
                porcelain.push(
                    self.repo,
                    refspecs=[self.local_branch_ref],
                    force=force_push,
                    errstream=tee_stream,
                    **self.connection_args,
                )
            finally:
                tee_stream.flush()
                error_content = error_buffer.getvalue().strip()
                tee_stream.close()

            self._raise_on_push_errors(error_content)

        except porcelain.DivergedBranches:
            self.logger.error("Could not push updates to remote repository!")
            self.logger.warn(
                "Local repo code has diverged from the remote repository, most "
                "likely because of new commits that have been pushed to the remote "
                "repo "
                "and are missing locally. ",
            )
            self.logger.info(
                "Updates will be pushed in the next python script execution",
            )

    def _raise_on_push_errors(self, error_content: str |None) -> None:
        """Check for push failure indicators and raise exception."""
        if not error_content:
            return

        if any(indicator in error_content for indicator in PUSH_FAILURE_INDICATORS):
            self.logger.error(f"Push operation failed: {error_content}")
            raise GitSyncException(f"Push operation failed: {error_content}")

    def _checkout(self) -> None:
        """Checkout a branch

        First, it will try to check out a remote branch if it exists.
        If it doesn't exist, It will use the remote HEAD as a base to a new branch.
        If it doesn't exist, It will use local branch as base for a new branch.
        If it doesn't exist, It assumes the repository is empty and creates an
        initial commit and branch.
        """
        if self.remote_branch_ref in self.repo.refs:
            # Checkout remote branch
            self.logger.info("Checking out remote branch")
            self.repo.refs.add_if_new(
                self.local_branch_ref,
                self.repo.refs[self.remote_branch_ref],
            )
        elif b"refs/remotes/origin/HEAD" in self.repo.refs:
            # No local HEAD - Use remote HEAD
            self.logger.info("Creating new local branch using remote HEAD")
            self.repo.refs.add_if_new(
                self.local_branch_ref,
                self.repo.refs[b"refs/remotes/origin/HEAD"],
            )
        elif HEADREF in self.repo.get_refs():
            # New branch - use local head as base
            self.logger.info("Creating new local branch using local HEAD")
            self.repo.refs.add_if_new(self.local_branch_ref, self.head.id)
        else:
            # Empty repo
            self.logger.info("Empty repo, creating branch from scratch")
            readme_blob = Blob.from_string(b"# GitSync\n")
            metadata_blob = Blob.from_string(
                json.dumps(Metadata().__dict__, indent=4).encode(),
            )
            self.repo.object_store.add_object(readme_blob)
            self.repo.object_store.add_object(metadata_blob)
            tree = Tree()
            tree.add(b"README.md", stat.S_IFREG | 0o644, readme_blob.id)
            tree.add(b"GitSync.json", stat.S_IFREG | 0o644, metadata_blob.id)
            self.repo.object_store.add_object(tree)
            commit = self.repo.do_commit(
                b"Initial commit",
                tree=tree.id,
                ref=b"",
                author=self.author,
                committer=self.author,
            )
            self.repo.refs[self.local_branch_ref] = commit
            self.push()

        self.repo.refs.set_symbolic_ref(HEADREF, self.local_branch_ref)
        self.repo.refs.set_if_equals(
            HEADREF,
            None,
            self.repo.refs[self.local_branch_ref],
        )

    def _clone(self) -> None:
        """Clones a git repository from repo url."""
        if not os.path.exists(self.wd):
            os.mkdir(self.wd)

        self.repo = Repo.init(self.wd)
        try:
            config = self.repo.get_config()
            config.set((b"remote", b"origin"), b"url", self.repo_url.encode("utf-8"))
            config.set(
                (b"remote", b"origin"),
                b"fetch",
                b"+refs/heads/*:refs/remotes/origin/*",
            )
            config.set(b"http", b"sslVerify", b"true" if self.verify_ssl else b"false")
            config.write_to_path()

            fetch_results = porcelain.fetch(self.repo, **self.connection_args, depth=1)

            origin_head_ref = fetch_results.symrefs.get(HEADREF)
            origin_head_sha = fetch_results.refs.get(HEADREF)

            if origin_head_sha and not origin_head_ref:
                # set detached HEAD
                self.repo.refs[HEADREF] = origin_head_sha

            # Set remote HEAD symbolic ref
            # refs/remotes/origin/HEAD => refs/remotes/origin/<remote branch name>
            origin_base = b"refs/remotes/origin/"
            origin_ref = origin_base + HEADREF
            # Check if remote has HEAD
            if origin_head_ref and origin_head_ref.startswith(LOCAL_BRANCH_PREFIX):
                target_ref = origin_base + origin_head_ref[len(LOCAL_BRANCH_PREFIX) :]
                if target_ref in self.repo.refs:
                    self.repo.refs.set_symbolic_ref(origin_ref, target_ref)

            self._checkout()

        except BaseException:
            shutil.rmtree(self.wd)
            self.repo.close()
            raise

    def update_objects(self, files: list[File], base_path: str | bytes = b"") -> Tree:
        """Main method to edit objects in the repo.

        Args:
            files (list[File]): A list or generator of File objects
            base_path (bytes, optional): Relative path in the repo.
                If supplied - All files under that base will be deleted/overwritten.
                If not supplied, files parameter elements must be with absolute paths.
                Files will not be deleted, but will be overwritten.
                Defaults to root path.

        Returns:
            Tree: The modified tree

        """
        if isinstance(base_path, str):
            base_path = base_path.encode("utf-8")
        self.tree = self._modify_tree(files, self.tree, base_path)
        self.repo.object_store.add_object(self.tree)
        return self.tree

    def _modify_tree(self, files: list[File], tree: Tree, base_path=b"") -> Tree:
        """Modifies a given tree, recursively, and adds all objects to the
        repo.object_store

        Args:
            files (list[File]): A list or generator of File objects
            tree (Tree): A tree object to update
            base_path (bytes, optional): Relative path in the repo. If supplied - All
            files under that
                base will be deleted/overwritten. Defaults to root path.

        Returns:
            Tree: The modified tree

        """
        try:
            _, subtree = tree.lookup_path(
                lambda sha: self.repo[sha],
                base_path.split(b"/")[0],
            )
            subtree = self.repo[subtree]
        except KeyError:
            subtree = Tree()

        if not base_path:
            new_tree = self._create_raw_tree(files, tree)
            self.repo.object_store.add_object(new_tree)
            return new_tree

        base_path = base_path.split(b"/")
        folder_name = base_path.pop(0)
        base_path = b"/".join(base_path)
        if not base_path:
            # New Directory
            new_tree = self._create_raw_tree(files)
        else:
            new_tree = self._modify_tree(files, subtree, base_path)
        self.repo.object_store.add_object(new_tree)
        tree.add(folder_name, stat.S_IFDIR, new_tree.id)
        return tree

    def _create_raw_tree(self, files: list[File], tree: Tree = None) -> Tree:
        """It is recommended to use the function update_objects.
        Creates a new tree object or updates the one passed down to it.
        If a tree object is passed down it will inherit all the other objects and
        won't delete files.

        Args:
            files (list[Files]): list or generator of Files object
            tree (Tree, optional): Tree to modify. if not passed, it will create a
            new tree. Defaults to None.

        Returns:
            Tree: The new tree

        """
        if not tree:
            tree = Tree()
        for file in files:
            mode = stat.S_IFREG | 0o644
            obj = Blob()
            obj.data = file.content
            path_items = file.path.encode("utf-8").split(b"/")
            sub_tree = tree
            old_trees = [sub_tree]
            for name in path_items[:-1]:
                try:
                    _, sub_tree_sha = sub_tree[name]
                except KeyError:
                    sub_tree = Tree()
                else:
                    sub_tree = self.repo.get_object(sub_tree_sha)
                old_trees.append(sub_tree)

            for old_tree, name in reversed(
                tuple(zip(old_trees, path_items, strict=False)),
            ):
                old_tree[name] = (mode, obj.id)
                self.repo.object_store.add_object(obj)
                obj = old_tree
                mode = stat.S_IFDIR

            self.repo.object_store.add_object(obj)
            tree = obj

        return tree

    def get_raw_object_from_path(
        self,
        path: str,
        tree: Tree = None,
    ) -> Tree | Blob | ShaFile:
        """Get the raw object from the git object store (Blob, Tree)

        Args:
            path: The path to the file
            tree (optional): The relevant tree. if not supplied the HEAD tree will be
            used. Defaults to None.

        Raises:
            KeyError: Raised if file or folder wasn't found

        Returns:
            (object): Raw dulwich object (Tree, Blob)

        """
        if isinstance(path, str):
            path = path.encode("utf-8")
        if tree is None:
            tree = self.tree
        try:
            return self.repo.get_object(
                tree_lookup_path(self.repo.get_object, tree.id, path)[1],
            )
        except KeyError as e:
            raise KeyError(f"Couldn't find folder or file: {e}")

    def get_file_objects_from_path(self, path: str, tree: Tree = None) -> list[File]:
        """Get a list of File objects from a path

        Args:
            path: Path to get File from
            tree (Tree, optional): Base tree to look for files. If not passed will
            use HEAD tree. Defaults to None.

        Returns:
            list[Files]: All files inside the given path

        """
        tree = self.get_raw_object_from_path(path, tree)
        files = []
        for file in dulwich.object_store.iter_tree_contents(
            self.repo.object_store,
            tree.id,
            include_trees=True,
        ):
            if file.mode == stat.S_IFREG | 0o644:
                files.append(
                    File(
                        file.path.decode("utf-8"),
                        self.repo.object_store.get_raw(file.sha)[1],
                    ),
                )
        return files

    def get_file_contents_from_path(self, path: str, tree: Tree = None) -> bytes:
        """Get a specific file contents from a path

        Returns:
            bytes: File contents

        """
        return self.repo.object_store.get_raw(
            self.get_raw_object_from_path(path, tree).id,
        )[1]

    def convert_password_to_private_key(self) -> paramiko.PKey:
        """If the password parameter is a private key, we convert it to a key object
        that paramiko can handle

        Raises:
            Exception: Raised if the key can't be converted to RSA or Ed25519 Key

        Returns:
            Paramiko Key: Private key object

        """
        self.password = base64.b64decode(self.password).decode("utf-8")
        try:
            return paramiko.rsakey.RSAKey.from_private_key(StringIO(self.password))
        except SSHException:
            try:
                return paramiko.ed25519key.Ed25519Key.from_private_key(
                    StringIO(self.password),
                )
            except SSHException as e:
                raise Exception(e)

    def list_files(self) -> None:
        """Prints list of files in the repo, recursive."""
        for file in dulwich.object_store.iter_tree_contents(
            self.repo.object_store,
            self.tree.id,
        ):
            self.logger.info(file)

    def cleanup(self) -> None:
        """Close Dulwich repository to release file handles."""
        try:
            self.repo.close()
        except Exception as e:
            self.logger.warn(f"Git cleanup failed: {e}", exc_info=True)


class SiemplifyParamikoSSHVendor:
    def __init__(
        self, siemplify_logger: SiemplifyLogger, git_server_fingerprint: str, **kwargs: Any
    ):
        """SSH client for dulwich that supports private keys instead of user:password"""
        self.kwargs = kwargs
        self.git_server_fingerprint = (
            git_server_fingerprint.strip() if git_server_fingerprint else None
        )

        self.siemplify_logger = siemplify_logger

    def _verify_host_key_fingerprint(self, received_key) -> bool:
        """Verify the received key against the expected fingerprint"""
        if not self.git_server_fingerprint:
            return False

        fingerprint = self.git_server_fingerprint.strip()
        self.siemplify_logger.info(f"Verifying fingerprint: {fingerprint}")

        try:
            if fingerprint.startswith("SHA256:"):
                expected_fingerprint = fingerprint.replace("SHA256:", "")
                key_hash = hashlib.sha256(received_key.asbytes()).digest()
                actual_fingerprint = base64.b64encode(key_hash).decode("ascii").rstrip("=")
                self.siemplify_logger.info(f"Actual SHA256 fingerprint: {actual_fingerprint}")
                return actual_fingerprint == expected_fingerprint
            elif fingerprint.startswith("MD5:"):
                expected_fingerprint = fingerprint.replace("MD5:", "").lower()
                key_hash = hashlib.md5(received_key.asbytes()).digest()
                actual_fingerprint = ":".join(f"{b:02x}" for b in key_hash)
                self.siemplify_logger.info(f"Actual MD5 fingerprint: {actual_fingerprint}")
                return actual_fingerprint == expected_fingerprint
            else:
                self.siemplify_logger.error(f"Unsupported fingerprint format: {fingerprint}")
                return False
        except Exception as e:
            self.siemplify_logger.exception(e)
            self.siemplify_logger.error(f"Failed to verify host key fingerprint: {e}", exc_info=True)
            return False

    def run_command(
        self,
        host,
        command,
        username=None,
        port=None,
        password=None,
        key_filename=None,
        protocol_version=None,
        **kwargs,
    ):
        client = paramiko.SSHClient()

        connection_kwargs = {"hostname": host}
        connection_kwargs.update(self.kwargs)
        if username:
            connection_kwargs["username"] = username
        if port:
            connection_kwargs["port"] = port
        if password:
            connection_kwargs["pkey"] = password
        if key_filename:
            connection_kwargs["key_filename"] = key_filename

        connection_kwargs.update(kwargs)

        # Handle host key verification based on whether git_server_fingerprint is provided
        if self.git_server_fingerprint:
            client.get_host_keys().clear() # FORCE unknown host behavior
            client.set_missing_host_key_policy(AlwaysVerifyPolicy(self))

        else:
            self.siemplify_logger.warn("No fingerprint provided - using insecure mode")

            # Legacy mode: keep existing insecure behavior
            client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())

        client.connect(**connection_kwargs)
        channel = client.get_transport().open_session()

        if protocol_version is None or protocol_version == 2:
            channel.set_environment_variable(name="GIT_PROTOCOL", value="version=2")

        self.siemplify_logger.error(f"Successfully connected to {host}")

        channel.exec_command(command)

        return _ParamikoWrapper(client, channel)


def remote_error_from_stderr(stderr):
    """Patch for dulwich error handling in newer paramiko versions"""
    if stderr is None:
        return HangupException()
    lines = [line.rstrip("\n") for line in stderr.readlines()]
    for line in lines:
        if line.startswith("ERROR: "):
            return GitProtocolError(line[len("ERROR: ") :])
    try:
        return HangupException(lines)
    except AttributeError:
        return HangupException([line.encode("utf-8") for line in lines])

class TeeStream(IOBase):
    """Stream multiplexer with protected system streams.
    Duplicates writes to multiple streams while protecting
    sys.stdout/stderr/stdin from accidental closure.
    """

    def __init__(self, *streams: Union[TextIO, IOBase]) -> None:
        super().__init__()
        self._streams = tuple(streams)
        self._closed = False
        # Protect standard streams from closure
        self._protected_streams = frozenset({sys.stdout, sys.stderr, sys.stdin})

    @property
    def closed(self) -> bool:
        """Stream closed state."""
        return self._closed

    def write(self, data: Union[str, bytes]) -> int:
        """Write to all streams, converting bytes to string if needed."""
        if self._closed:
            raise ValueError("I/O operation on closed stream")

        content = self._normalize_content(data)

        for stream in self._streams:
            self._safe_write(stream, content)

        return len(content)

    def flush(self) -> None:
        """Flush all streams that support flushing."""
        if not self._closed:
            for stream in self._streams:
                self._safe_flush(stream)

    def close(self) -> None:
        """Close only non-protected streams, mark tee as closed."""
        if self._closed:
            return

        # Close only streams we're allowed to close
        for stream in self._streams:
            if (stream not in self._protected_streams and
                    hasattr(stream, 'close') and
                    not getattr(stream, 'closed', False)):
                try:
                    stream.close()
                except Exception:
                    pass

        self._closed = True
        super().close()

    def writable(self) -> bool:
        """Check if stream is writable."""
        return not self._closed

    def __enter__(self) -> 'TeeStream':
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with guaranteed cleanup."""
        self.close()

    @staticmethod
    def _normalize_content(data: Union[str, bytes]) -> str:
        """Convert data to string format."""
        if isinstance(data, bytes):
            return data.decode('utf-8', errors='replace')
        return str(data)

    @staticmethod
    def _safe_write(stream: Union[TextIO, IOBase], content: str) -> None:
        """Write to stream with error suppression."""
        if not getattr(stream, 'closed', False):
            try:
                stream.write(content)
            except Exception:
                pass

    @staticmethod
    def _safe_flush(stream: Union[TextIO, IOBase]) -> None:
        """Flush stream with error suppression."""
        if hasattr(stream, 'flush') and not getattr(stream, 'closed', False):
            try:
                stream.flush()
            except Exception:
                pass


class GitSyncException(Exception):
    """Exception raised for GitSync operations failures."""


class AlwaysVerifyPolicy(paramiko.client.MissingHostKeyPolicy):
    def __init__(self, vendor_instance : SiemplifyParamikoSSHVendor) -> None:
        self.vendor = vendor_instance

    def missing_host_key(self, client, hostname, key) -> None:
        """Called for unknown hosts"""
        self._verify_and_decide(client, hostname, key)

    def _verify_and_decide(self, client, hostname, key) -> None:
        self.vendor.siemplify_logger.info(f"Verifying fingerprint for {hostname}")

        if self.vendor._verify_host_key_fingerprint(key):
            self.vendor.siemplify_logger.info("Fingerprint verified - accepting connection")
            client.get_host_keys().add(hostname, key.get_name(), key)
        else:
            self.vendor.siemplify_logger.error("Fingerprint verification failed.")
            raise paramiko.ssh_exception.SSHException(
                f"Host key verification failed for {hostname}")