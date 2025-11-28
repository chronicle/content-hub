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

import unittest
from jinja2 import Environment
from content.response_integrations.power_ups.template_engine.core.Widgets import card

class TestWidgets(unittest.TestCase):
    def test_card_function(self):
        title = "Test Title"
        content = "Test Content"
        html = card(title, content)
        
        self.assertIn(title, html)
        self.assertIn(content, html)
        self.assertIn("background-color:#282828;", html) # Default style check
        self.assertIn("<div", html)
        self.assertIn("<h3", html)
        self.assertIn("<p", html)

    def test_card_custom_style(self):
        title = "Styled Title"
        content = "Styled Content"
        style = {"background-color": "red"}
        html = card(title, content, style=style)
        
        self.assertIn("background-color:red;", html)
        # Check that default styles are overwritten or merged
        self.assertIn("border:1px solid #444;", html) 

    def test_jinja_filter_registration(self):
        env = Environment()
        env.filters["widget_card"] = card
        
        template_str = '{{ "MyTitle" | widget_card("MyContent") }}'
        template = env.from_string(template_str)
        result = template.render()
        
        self.assertIn("MyTitle", result)
        self.assertIn("MyContent", result)
        self.assertIn("background-color:#282828;", result)

if __name__ == '__main__':
    unittest.main()
