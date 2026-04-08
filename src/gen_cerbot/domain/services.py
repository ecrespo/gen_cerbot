"""CertbotService — top-level orchestration of the certificate flow.

``generate()`` wires together distro detection, DNS validation, provider
install/configure/verify, certbot install + request, and the post-issuance
service health check. It is the single entry point the CLI invokes.
"""

from __future__ import annotations

from gen_cerbot.certbot.installer import CertbotInstaller
from gen_cerbot.certbot.manager import CertbotManager
from gen_cerbot.domain.models import CertificateConfig, ServerType
from gen_cerbot.providers.factory import ProviderFactory
from gen_cerbot.utils.distro import DistroDetector
from gen_cerbot.utils.dns import DNSValidator
from gen_cerbot.utils.system import SystemRunner
from gen_cerbot.utils.templates import TemplateRenderer


class CertbotService:
    """High-level orchestrator that drives a full certificate generation.

    Dependencies are constructor-injected so tests can supply mocks for any
    step of the flow (distro detection, DNS, provider, certbot).
    """

    def __init__(
        self,
        runner: SystemRunner | None = None,
        distro_detector: DistroDetector | None = None,
        dns_validator: DNSValidator | None = None,
        certbot_installer: CertbotInstaller | None = None,
        certbot_manager: CertbotManager | None = None,
        provider_factory: ProviderFactory | None = None,
        template_renderer: TemplateRenderer | None = None,
    ) -> None:
        self._runner = runner or SystemRunner()
        self._distro_detector = distro_detector or DistroDetector()
        self._dns_validator = dns_validator or DNSValidator()
        self._certbot_installer = certbot_installer or CertbotInstaller(self._runner)
        self._certbot_manager = certbot_manager or CertbotManager(self._runner)
        self._template_renderer = template_renderer or TemplateRenderer()
        self._provider_factory = provider_factory or ProviderFactory(
            self._runner, self._template_renderer
        )

    def generate(self, config: CertificateConfig) -> None:
        """Run the full certificate generation flow.

        Steps (in order):
          1. Detect the Linux distribution family.
          2. Validate DNS (unless ``config.skip_dns_check`` is set).
          3. Build the provider for the target server (PackageManager is
             constructed inside the factory using the detected distro).
          4. Provider.install() — install the web server packages.
          5. Provider.configure() — render templates and activate the site.
          6. Provider.verify() — syntactic check (e.g. ``nginx -t``).
          7. CertbotInstaller.ensure_installed() — idempotent, per-distro
             (skipped for Traefik).
          8. CertbotManager.request() — issue the cert via ``--nginx`` /
             ``--apache`` with ``--non-interactive --agree-tos`` (skipped
             for Traefik — ACME is native in ``traefik.yml``).
          9. CertbotManager.verify_service() — post-cert health check
             (``systemctl status`` or ``docker compose ps``).

        When ``config.dry_run`` is set, the shared :class:`SystemRunner`
        is flipped into dry-run mode for the duration of the call so every
        subprocess is printed instead of executed, then restored on exit.

        Args:
            config: Validated certificate request parameters.
        """
        previous_dry_run = self._runner.dry_run
        self._runner.dry_run = previous_dry_run or config.dry_run
        try:
            self._generate(config)
        finally:
            self._runner.dry_run = previous_dry_run

    def _generate(self, config: CertificateConfig) -> None:
        """Internal generate flow (runner dry-run state already applied)."""
        distro_family = self._distro_detector.detect()

        self._dns_validator.check(config.domain, skip=config.skip_dns_check)

        provider = self._provider_factory.get(config.server_type, distro_family)
        provider.install()
        provider.configure(config)
        provider.verify()

        self._certbot_installer.ensure_installed(distro_family, config.server_type)

        if config.server_type != ServerType.TRAEFIK:
            self._certbot_manager.request(
                domain=config.domain,
                email=config.email,
                server_type=config.server_type,
                staging=config.staging,
            )

        self._certbot_manager.verify_service(config.server_type, distro_family)
