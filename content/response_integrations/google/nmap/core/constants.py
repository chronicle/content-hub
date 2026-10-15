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
INTEGRATION_NAME: str = "Nmap"

PING_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ping"
SCAN_ENTITIES_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Scan Entities"

ERROR_MESSAGE_FOR_INVALID_TARGET: str = "WARNING"
ERROR_MESSAGE_FOR_FAIL_NMAP_SCAN: str = "QUITTING"

TEST_COMMAND: list[str] = ["nmap", "--version"]

SUCCESS_RETURN_CODE: int = 0

NMAP_ROOT_REQUIRED_OPTIONS: list[str] = [
    # Scan Types (Raw Packet Scans)
    "-sS",  # TCP SYN scan
    "-sF",  # FIN scan
    "-sX",  # Xmas scan
    "-sN",  # NULL scan
    "-sA",  # ACK scan
    "-sW",  # Window scan
    "-sM",  # Maimon scan
    "-sU",  # UDP scan
    "-sY",  # SCTP INIT scan
    "-sZ",  # SCTP COOKIE-ECHO scan
    # Advanced OS and Network Features
    "-O",  # OS detection
    "--osscan-guess",  # Guess OS aggressively
    "--osscan-limit",  # Limit OS detection
    # Routing and Host Discovery
    "--traceroute",  # Trace network route
    "--reason",  # Show reasons for port/host state
    "--ip-options",  # Add IP options to packets
    # Packet Manipulation & Evasion
    "-f",  # Fragment packets
    "--mtu",  # Set packet MTU
    "--data-length",  # Append random data
    "--ttl",  # Set TTL
    "--spoof-mac",  # Spoof MAC address
    "--badsum",  # Send bad checksums
    "--send-eth",  # Send at Ethernet layer
    "--send-ip",  # Send at IP layer
    # Source and Interface Control
    "-e",  # Specify interface
    "-S",  # Spoof source IP
    "--source-port",  # Spoof source port
    "--interface",  # Alias for -e
    # Decoys and Idle Scan
    "-D",  # Decoy scan
    "-sI",  # Idle scan
]
