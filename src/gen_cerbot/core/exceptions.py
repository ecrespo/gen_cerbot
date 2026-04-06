"""Domain exception hierarchy for gen_cerbot."""


class GenCerbotError(Exception):
    """Base exception for all gen_cerbot errors."""


class UnsupportedDistroError(GenCerbotError):
    """Raised when the detected Linux distribution is not supported."""

    def __init__(self, distro_id: str) -> None:
        self.distro_id = distro_id
        super().__init__(
            f"Unsupported distribution: '{distro_id}'. Supported: Debian/Ubuntu, Fedora, openSUSE."
        )


class SudoError(GenCerbotError):
    """Raised when a sudo command fails or sudo is not available."""

    def __init__(self, command: str, returncode: int, stderr: str = "") -> None:
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"sudo command failed (exit {returncode}): {command}"
            + (f"\n{stderr}" if stderr else "")
        )


class CommandError(GenCerbotError):
    """Raised when a system command fails."""

    def __init__(self, command: str, returncode: int, stderr: str = "") -> None:
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"Command failed (exit {returncode}): {command}" + (f"\n{stderr}" if stderr else "")
        )


class CertbotError(GenCerbotError):
    """Raised when a Certbot operation fails."""


class ServerConfigError(GenCerbotError):
    """Raised when server configuration is invalid or service is not running."""


class DNSValidationError(GenCerbotError):
    """Raised when DNS pre-flight check fails."""

    def __init__(self, domain: str, expected_ip: str | None = None) -> None:
        self.domain = domain
        self.expected_ip = expected_ip
        msg = f"DNS validation failed for '{domain}'."
        if expected_ip:
            msg += f" Expected IP: {expected_ip}"
        super().__init__(msg)


class RootExecutionError(GenCerbotError):
    """Raised when the tool is run as root user."""

    def __init__(self) -> None:
        super().__init__(
            "gen-cerbot must not be run as root. "
            "Run as a normal user; sudo is invoked internally when needed."
        )


class PackageInstallError(GenCerbotError):
    """Raised when a package installation fails."""

    def __init__(self, package: str, distro: str, stderr: str = "") -> None:
        self.package = package
        self.distro = distro
        super().__init__(
            f"Failed to install package '{package}' on {distro}" + (f"\n{stderr}" if stderr else "")
        )
