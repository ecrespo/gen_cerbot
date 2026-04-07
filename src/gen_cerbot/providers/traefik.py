"""TraefikProvider — web server provider for Traefik (Docker-based)."""

from __future__ import annotations

from pathlib import Path

from gen_cerbot.core.exceptions import ServerConfigError
from gen_cerbot.domain.models import CertificateConfig, DistroFamily
from gen_cerbot.providers.base import ServerProvider
from gen_cerbot.utils.package_manager import PackageManager
from gen_cerbot.utils.system import SystemRunner
from gen_cerbot.utils.templates import TemplateRenderer

# Default directory where Traefik config files are generated.
_DEFAULT_OUTPUT_DIR = Path.home() / "traefik"


def _sanitize(name: str) -> str:
    """Make a string safe for use as a Docker Compose project/service name."""
    return name.replace(".", "_").replace("-", "_")


class TraefikProvider(ServerProvider):
    """Provider for Traefik, which runs as a Docker container.

    Unlike Nginx and Apache, Traefik is distro-agnostic: it runs in Docker,
    so `install()` only verifies that Docker is present (it does NOT install
    Traefik via the system package manager). ACME/Let's Encrypt is handled
    natively by Traefik via `traefik.yml`, so Certbot is not used.

    Accepts an optional output_dir for testing, which redirects all
    generated files (docker-compose.yml, traefik.yml, acme.json) to a
    local directory instead of the default ~/traefik.
    """

    def __init__(
        self,
        runner: SystemRunner,
        pkg_manager: PackageManager,
        template_renderer: TemplateRenderer,
        distro_family: DistroFamily,
        *,
        output_dir: Path | None = None,
    ) -> None:
        super().__init__(runner, pkg_manager, template_renderer, distro_family)
        self._output_dir = output_dir
        self._last_compose_path: Path | None = None

    def _project_dir(self, config: CertificateConfig | None = None) -> Path:
        if self._output_dir is not None:
            return self._output_dir
        if config is not None and config.project_name:
            return _DEFAULT_OUTPUT_DIR / config.project_name
        return _DEFAULT_OUTPUT_DIR

    def install(self) -> None:
        """Verify that Docker is installed (distro-agnostic).

        Traefik itself is not installed via the system package manager —
        it runs as a Docker container declared in `docker-compose.yml`.
        This method only checks that `docker` is available on the PATH.

        Raises:
            ServerConfigError: If Docker is not installed.
        """
        result = self._runner.run(
            ["docker", "--version"], sudo=False, check=False
        )
        if not result.success:
            raise ServerConfigError(
                "Docker is not installed or not available on PATH. "
                "Install Docker before using the Traefik provider: "
                "https://docs.docker.com/engine/install/"
            )

    def get_service_name(self) -> str:
        """Traefik has no systemd service — it runs as a Docker container."""
        return "traefik"

    def configure(self, config: CertificateConfig) -> None:
        """Generate docker-compose.yml, traefik.yml, and acme.json.

        Creates the project directory (default `~/traefik/<project>`) and
        writes three files:
          - `docker-compose.yml` — Traefik service definition with labels
            pointing to the target application on `localhost:{port}`.
          - `traefik.yml` — Static configuration with ACME/Let's Encrypt
            resolver using HTTP-01 challenge.
          - `acme.json` — Empty file with `chmod 600` permissions, where
            Traefik will store issued certificates.
        """
        project_dir = self._project_dir(config)
        project_dir.mkdir(parents=True, exist_ok=True)

        context = {
            "domain": config.domain,
            "port": config.port,
            "project_name": config.project_name or _sanitize(config.domain),
            "email": config.email,
        }

        compose_path = project_dir / "docker-compose.yml"
        traefik_path = project_dir / "traefik.yml"
        acme_path = project_dir / "acme.json"

        compose_content = self._template_renderer.render(
            "traefik/docker-compose.yml.j2", context
        )
        traefik_content = self._template_renderer.render(
            "traefik/traefik.yml.j2", context
        )

        compose_path.write_text(compose_content, encoding="utf-8")
        traefik_path.write_text(traefik_content, encoding="utf-8")

        # Create acme.json (empty) and set 600 permissions — REQUIRED by Traefik.
        acme_path.touch(exist_ok=True)
        self._runner.run(["chmod", "600", str(acme_path)], sudo=True)

        # Remember where we wrote things so verify()/remove() can find them.
        self._last_compose_path = compose_path

    def verify(self) -> None:
        """Verify the generated `docker-compose.yml` with `docker compose config`.

        Runs without sudo — Docker Compose only needs to parse the file,
        not touch the daemon for this check.

        Raises:
            ServerConfigError: If no compose file has been generated yet,
                or if `docker compose config` reports a validation error.
        """
        compose_path = self._last_compose_path or (
            self._project_dir() / "docker-compose.yml"
        )
        if not compose_path.exists():
            raise ServerConfigError(
                f"docker-compose.yml not found at {compose_path}. "
                "Run configure() before verify()."
            )

        result = self._runner.run(
            ["docker", "compose", "-f", str(compose_path), "config"],
            sudo=False,
            check=False,
        )
        if not result.success:
            raise ServerConfigError(
                f"Traefik docker-compose validation failed:\n{result.stderr}"
            )

    def remove(self, domain: str) -> None:
        """Tear down the Traefik deployment and remove generated files.

        Steps:
          1. If a `docker-compose.yml` exists for this project, bring the
             stack down with `docker compose -f <path> down` (without sudo;
             `check=False` so a not-running stack does not raise).
          2. Delete the three generated files: `docker-compose.yml`,
             `traefik.yml`, and `acme.json`.
          3. Remove the project directory itself if it ends up empty.

        Idempotent: missing files/directories are silently ignored.
        """
        project_dir = (
            self._last_compose_path.parent
            if self._last_compose_path is not None
            else self._project_dir()
        )
        compose_path = project_dir / "docker-compose.yml"
        traefik_path = project_dir / "traefik.yml"
        acme_path = project_dir / "acme.json"

        # 1. Tear down the running stack (no-op if not running).
        if compose_path.exists():
            self._runner.run(
                ["docker", "compose", "-f", str(compose_path), "down"],
                sudo=False,
                check=False,
            )

        # 2. Remove generated files.
        for path in (compose_path, traefik_path, acme_path):
            if path.exists():
                path.unlink()

        # 3. Remove the project directory if empty.
        if project_dir.exists() and not any(project_dir.iterdir()):
            project_dir.rmdir()

        self._last_compose_path = None
