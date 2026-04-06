"""Jinja2 template renderer for server configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class TemplateRenderer:
    """Renders Jinja2 templates for server configuration."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        self._dir = templates_dir or _TEMPLATES_DIR
        self._env = Environment(
            loader=FileSystemLoader(str(self._dir)),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template with the given context.

        Args:
            template_name: Relative path to the template (e.g., 'nginx/site.conf.j2').
            context: Dictionary of variables to pass to the template.

        Returns:
            Rendered template string.
        """
        template = self._env.get_template(template_name)
        return template.render(context)

    def render_to_file(
        self, template_name: str, context: dict[str, Any], output_path: Path
    ) -> None:
        """Render a template and write the output to a file."""
        content = self.render(template_name, context)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
