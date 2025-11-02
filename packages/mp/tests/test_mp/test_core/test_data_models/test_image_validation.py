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

from pathlib import Path
from unittest import mock

import pytest
from PIL import UnidentifiedImageError

import mp.core.constants
from mp.core.validators import validate_png_content, validate_svg_content


class TestValidateSvgContent:
    def test_valid_svg(self, non_built_integration: Path) -> None:
        """Test that a valid SVG file is parsed correctly."""
        svg_path: Path = (
            non_built_integration / mp.core.constants.RESOURCES_DIR / mp.core.constants.LOGO_FILE
        )
        assert validate_svg_content(svg_path)

    @mock.patch("Path.read_text")
    def test_empty_svg_raises_error(self, mock_read_text: mock.MagicMock) -> None:
        """Test that an empty SVG file raises a ValueError."""
        mock_read_text.return_value = ""
        with pytest.raises(ValueError, match="SVG file is empty"):
            validate_svg_content(Path("fake.svg"))

    @mock.patch("Path.read_text")
    def test_invalid_xml_svg_raises_error(self, mock_read_text: mock.MagicMock) -> None:
        """Test that a non-XML file raises a ValueError."""
        mock_read_text.return_value = "this is not xml"
        with pytest.raises(ValueError, match="Invalid XML syntax"):
            validate_svg_content(Path("fake.svg"))

    @mock.patch("Path.read_text")
    def test_invalid_root_tag(self, mock_read_text: mock.MagicMock) -> None:
        """Test that an XML file without an <svg> root tag fails."""
        mock_read_text.return_value = "<doc><item/></doc>"
        with pytest.raises(ValueError, match="missing <svg> root tag"):
            validate_svg_content(Path("fake.svg"))


class TestValidatePngContent:
    def test_valid_png(self, non_built_integration: Path) -> None:
        """Test that a valid PNG file is parsed correctly."""
        png_path: Path = (
            non_built_integration / mp.core.constants.RESOURCES_DIR / mp.core.constants.IMAGE_FILE
        )
        assert validate_png_content(png_path)

    @mock.patch("mp.core.validators.Image.open")
    def test_jpeg_named_as_png_raises_error(self, mock_image_open: mock.MagicMock) -> None:
        """Test that a JPEG file with a .png extension raises a ValueError."""
        mock_image = mock.MagicMock()
        mock_image.format = "jpeg"
        mock_image_open.return_value.__enter__.return_value = mock_image
        with pytest.raises(ValueError, match="Invalid image format"):
            validate_png_content(Path("fake.png"))

    @mock.patch("mp.core.validators.Image.open")
    def test_not_an_image_raises_error(self, mock_image_open: mock.MagicMock) -> None:
        """Test that a non-image file raises a ValueError."""
        mock_image_open.side_effect = UnidentifiedImageError

        with pytest.raises(ValueError, match="File is not a valid image or is corrupted:"):
            validate_png_content(Path("fake.png"))
