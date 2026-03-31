# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`gen_cerbot` is a Python CLI tool that automates TLS/SSL certificate configuration for web servers (Nginx, Apache, Traefik) using Let's Encrypt/Certbot. It supports both an interactive guided menu mode and direct command mode for CI/CD use.

**Status:** Planning phase — SPEC.md, ARCHITECTURE.md, and TASKS.md are defined but source code has not yet been written.

## Development Setup

```bash
# Install in editable mode for development
pip install -e .

# Install with dev dependencies (once pyproject.toml is set up)
pip install -e ".[dev]"
```

## Commands

```bash
# Lint and format
ruff check .
ruff format .

# Type checking
mypy .

# Run all tests
pytest

# Run a single test file
pytest tests/unit/test_distro.py

# Run a single test by name
pytest tests/unit/test_distro.py::test_detect_ubuntu -v

# Build distributions
python -m build          # wheel + sdist for PyPI
dpkg-buildpackage -us -uc -b   # .deb (requires Debian/Ubuntu env)
rpmbuild -bb ~/rpmbuild/SPECS/gen-cerbot.spec  # .rpm (requires Fedora env)
```

## Architecture

The project uses a **bottom-up layered architecture** with clear separation of concerns:

### Layer Stack (top to bottom)

```
CLI Entry Point (cli.py / Typer)
    ↓
i18n: LanguageSelector → LocaleManager.t("key")
    ↓
Interactive Mode (interactive/) OR Direct Commands (Typer subcommands)
    ↓
CertbotService — orchestrates the full flow
    ↓
ServerProvider (Abstract) ← NginxProvider / ApacheProvider / TraefikProvider
CertbotManager             ← install / request / renew / revoke / list
DNSValidator               ← pre-flight DNS check
    ↓
PackageManager (ABC) ← AptPackageManager / DnfPackageManager / ZypperPackageManager
    ↓
SystemRunner — all subprocess calls, prepends ["sudo"] when sudo=True
DistroDetector — reads /etc/os-release → DistroFamily enum
```

### Key Design Decisions

**Provider Pattern:** Each web server (Nginx, Apache, Traefik) is a `ServerProvider` implementation. Adding a new server = new provider file, no core changes.

**Internal sudo:** The CLI runs as a normal user. `SystemRunner.run(cmd, sudo=True)` prepends `sudo` internally. Never run the tool as root.

**src layout:** All source code lives under `src/gen_cerbot/`. Entry point: `src/gen_cerbot/cli.py`.

**i18n:** `LocaleManager.t("key")` returns the translated string with fallback to English. Language preference stored in `~/.config/gen_cerbot/config.toml`. Force with `--lang en|es`.

**CertbotInstaller:** Installs Certbot per distro family. On Debian/Ubuntu: checks snapd is present → `snap install --classic certbot` → `ln -sf /snap/bin/certbot /usr/local/bin/certbot`. On Fedora: `dnf install -y certbot python3-certbot-nginx python3-certbot-apache`. On openSUSE: `zypper install -y certbot python3-certbot-nginx python3-certbot-apache`. Traefik does not use Certbot (ACME is native in traefik.yml).

**CertbotManager:** Requests certificates with `sudo certbot --nginx` or `sudo certbot --apache` (never `--traefik`), always passing `--non-interactive --agree-tos --email`. After a successful request, calls `SystemRunner` to run `systemctl status <service> --no-pager` (nginx / apache2 / httpd depending on distro) for final health check.

**CertRegistry:** JSON file tracking managed certificates (`utils/registry.py`). Operations must be idempotent — re-running on an already-configured system must not break anything.

**Templates:** Jinja2 renders server config files (`utils/templates.py`).

### Module Map

| Module | Responsibility |
|---|---|
| `cli.py` | Typer entry point; `generate`, `list`, `renew`, `remove` subcommands |
| `core/config.py` | Global config via pydantic-settings |
| `core/exceptions.py` | Domain exception hierarchy (incl. `UnsupportedDistroError`, `SudoError`) |
| `domain/models.py` | `CertificateConfig`, `ServerType`, `DistroFamily`, `CertificateRecord` |
| `domain/services.py` | `CertbotService` — main orchestration logic |
| `providers/base.py` | `ServerProvider` ABC |
| `providers/{nginx,apache,traefik}.py` | Web server implementations |
| `certbot/installer.py` | Certbot installation: snap+symlink (Debian/Ubuntu), dnf (Fedora), zypper (openSUSE); snapd pre-check |
| `certbot/manager.py` | Certificate lifecycle management: `request()` runs `certbot --nginx/--apache --non-interactive --agree-tos`; `verify_service()` runs `systemctl status` post-cert |
| `interactive/menu.py` | Main interactive menu (questionary) |
| `interactive/wizard.py` | Step-by-step generate wizard |
| `interactive/output.py` | Real-time output display (rich) |
| `i18n/locale_manager.py` | `LocaleManager` with fallback |
| `i18n/selector.py` | Language selector + config.toml persistence |
| `utils/dns.py` | Pre-flight DNS validation |
| `utils/system.py` | `SystemRunner` — all subprocess calls |
| `utils/distro.py` | `DistroDetector` — reads `/etc/os-release` |
| `utils/package_manager.py` | `PackageManager` ABC + apt/dnf/zypper impls + Factory |
| `utils/templates.py` | Jinja2 template renderer |

## Testing Approach

- **Unit tests** (`tests/unit/`): Mock `SystemRunner` and filesystem; use fixtures in `tests/fixtures/os-release/` for `DistroDetector` tests.
- **Integration tests** (`tests/integration/`): Require actual Linux environment with sudo.
- Target: >80% coverage.
- `DistroDetector` must be tested against all three distro families using the OS-release fixtures.

## Key Dependencies

- `typer` — CLI framework
- `questionary` — interactive menus
- `rich` — real-time output rendering
- `pydantic-settings` — configuration management
- `jinja2` — config file templates
- `ruff` — linting + formatting
- `mypy` — type checking
- `pytest` — testing

## Implementation Phases

See TASKS.md for the full 8-phase plan. Current status: Phase 1 (Foundation) not yet started.