# Copyright 2026 RansomLeak
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

# Import soar_sdk before anything else so its bare module aliases (SiemplifyAction, SiemplifyBase, ...)
# resolve to the same module objects TIPCommon's base Action uses; otherwise the test patches miss them.
import soar_sdk  # noqa: F401
