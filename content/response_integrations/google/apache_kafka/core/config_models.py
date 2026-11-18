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

import dataclasses


@dataclasses.dataclass(slots=True)
class KafkaConfigurationParameters:
    """Dataclass for Kafka connection configuration parameters."""

    bootstrap_servers: str
    use_ssl: bool
    use_sasl_ssl: bool
    sasl_username: str
    sasl_password: str
    ca_certificate: str
    client_certificate: str
    client_certificate_key: str
    client_certificate_key_password: str
