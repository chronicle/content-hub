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
JWM_TEMPLATE = """
{% if explanation is defined and explanation and exception_instructions is defined and exception_instructions %}
    h2. Finding Explanation
    {{ explanation }}
    h2. Exception Instructions
    {{ exception_instructions }}
{% elif show_description_based_params is defined and show_description_based_params %}
    {% if documentation is defined and documentation %}
        h2. Finding Documentation
        {{ documentation }}
    {% endif %}
    {% if statement is defined and statement %}
        h2. Finding Statement
        {{ statement }}
    {% endif %}
    {% if mitigation is defined and mitigation %}
        h2. Finding Mitigation
        {{ mitigation }}
    {% endif %}
{% else %}
    h2. Finding Description
    {% if description is defined and description %}
        {{ description }}
    {% else %}
        N/A
    {% endif %}
{% endif %}
{% if recommended_steps is defined and recommended_steps %}
    h2. Recommended Steps
    {{ recommended_steps }}
{% else %}
    h2. Next Steps
    {% if next_steps is defined and next_steps %}
        {{ next_steps }}
    {% else %}
        N/A
    {% endif %}
{% endif %}
{% if cvss is defined and cvss %}
    h2. CVSS V3 Information

    {% for name, value in cvss.items() %}
        {% if name and value %}
            {{ name }}: {{ value }}
        {% endif %}
    {% endfor %}
{% endif %}
{% if cve is defined and cve %}
    h2. Additional Information

    {% for name, value in cve.items() %}
        {% if name and value %}
            {{ name }}: {{ value }}
        {% endif %}
    {% endfor %}
{% endif %}
{% if references is defined and references %}
    h2. Reference Links

    {% for reference in references %}
        - [{{ reference.source }}|{{ reference.uri }}]
    {% endfor %}

{% endif %}
h2. Impacted Resources

{anchor:resource_table_start}{anchor:resource_table_end}
"""
