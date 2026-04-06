"""Unit tests for TemplateRenderer."""

from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import UndefinedError

from gen_cerbot.utils.templates import TemplateRenderer


class TestTemplateRenderer:
    def test_render_basic_template(self, tmp_path: Path) -> None:
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        template_file = templates_dir / "test.conf.j2"
        template_file.write_text("server {{ domain }} on port {{ port }};")

        renderer = TemplateRenderer(templates_dir)
        result = renderer.render("test.conf.j2", {"domain": "example.com", "port": 8080})
        assert "server example.com on port 8080;" in result

    def test_render_raises_on_missing_variable(self, tmp_path: Path) -> None:
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        template_file = templates_dir / "test.j2"
        template_file.write_text("Hello {{ name }}")

        renderer = TemplateRenderer(templates_dir)
        with pytest.raises(UndefinedError):
            renderer.render("test.j2", {})

    def test_render_to_file(self, tmp_path: Path) -> None:
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        template_file = templates_dir / "out.j2"
        template_file.write_text("content: {{ value }}")

        output = tmp_path / "output" / "result.conf"
        renderer = TemplateRenderer(templates_dir)
        renderer.render_to_file("out.j2", {"value": "test123"}, output)
        assert output.exists()
        assert "content: test123" in output.read_text()
