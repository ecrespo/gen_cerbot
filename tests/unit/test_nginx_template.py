"""Unit tests for Nginx site.conf.j2 template."""

from __future__ import annotations

from gen_cerbot.utils.templates import TemplateRenderer


class TestNginxTemplate:
    def _render(self, **overrides: object) -> str:
        context = {
            "domain": "app.example.com",
            "port": 8000,
            "project_name": "myapp",
        }
        context.update(overrides)
        renderer = TemplateRenderer()
        return renderer.render("nginx/site.conf.j2", context)

    def test_server_name_present(self) -> None:
        result = self._render()
        assert "server_name app.example.com;" in result

    def test_proxy_pass_with_correct_port(self) -> None:
        result = self._render(port=3000)
        assert "proxy_pass http://localhost:3000;" in result

    def test_default_port(self) -> None:
        result = self._render()
        assert "proxy_pass http://localhost:8000;" in result

    def test_security_headers_present(self) -> None:
        result = self._render()
        assert "X-Frame-Options" in result
        assert "X-Content-Type-Options" in result
        assert "X-XSS-Protection" in result
        assert "Referrer-Policy" in result

    def test_proxy_headers_present(self) -> None:
        result = self._render()
        assert "proxy_set_header Host" in result
        assert "proxy_set_header X-Real-IP" in result
        assert "proxy_set_header X-Forwarded-For" in result
        assert "proxy_set_header X-Forwarded-Proto" in result

    def test_proxy_timeouts_present(self) -> None:
        result = self._render()
        assert "proxy_connect_timeout" in result
        assert "proxy_send_timeout" in result
        assert "proxy_read_timeout" in result

    def test_logging_with_project_name(self) -> None:
        result = self._render(project_name="testproject")
        assert "testproject_access.log" in result
        assert "testproject_error.log" in result

    def test_listens_on_port_80(self) -> None:
        result = self._render()
        assert "listen 80;" in result
        assert "listen [::]:80;" in result

    def test_websocket_upgrade_headers(self) -> None:
        result = self._render()
        assert 'proxy_set_header Upgrade $http_upgrade;' in result
        assert 'proxy_set_header Connection "upgrade";' in result
