# gen_cerbot — Product Requirements Document (PRD)

## Metadata

| Field | Value |
|---|---|
| **Product** | gen_cerbot |
| **Author** | Ernesto Crespo |
| **Status** | `DRAFT` |
| **Version** | 1.0 |
| **Date** | 2026-03-31 |
| **Last updated** | 2026-03-31 |
| **Related documents** | [SPEC.md](./SPEC.md) · [ARCHITECTURE.md](./ARCHITECTURE.md) · [TASKS.md](./TASKS.md) |

---

## 1. Executive Summary

`gen_cerbot` is a Python command-line tool (CLI) that automates the complete TLS/SSL configuration for Linux web servers. It converts a 20–30 minute manual task — installing a web server, configuring a reverse proxy, obtaining a Let's Encrypt certificate, and enabling automatic renewal — into a single command or a guided experience of less than 5 minutes. It supports Nginx, Apache, and Traefik on Debian/Ubuntu, Fedora, and openSUSE, and is distributed as an installable package via `pip`, `.deb`, and `.rpm`.

---

## 2. Problem

Configuring HTTPS on a new Linux server involves a manual sequence of error-prone steps:

1. Update the system and install the web server with the correct package manager for the distro
2. Create and enable virtual host or reverse proxy configuration files
3. Install Certbot (different method depending on the distribution: `snap`, `dnf`, or `zypper`)
4. Request the certificate with the correct flags for the web server
5. Verify that the resulting configuration is valid
6. Set up automatic renewal

This process varies in detail depending on the web server and the Linux distribution, is not consistently documented, and is difficult to automate in CI/CD pipelines without a dedicated tool. The original bash script `nginx-setup.sh` solved the problem partially for Nginx on Ubuntu/Debian, but was not extensible or testable.

---

## 3. Product Goals

| Goal | Success metric |
|---|---|
| Reduce TLS/SSL configuration time | < 5 minutes from scratch on a clean server |
| Support the 3 most used web servers | Nginx, Apache, and Traefik working in v1.0 |
| Support the 3 Linux distro families | Debian/Ubuntu, Fedora, and openSUSE working in v1.0 |
| Be usable without additional documentation | Guided interactive mode that does not require reading a manual |
| Integrate into CI/CD pipelines | All steps accessible as CLI flags (`--no-interactive`) |
| Be distributable as a native package | `pip install`, `apt install`, and `dnf install` functional in v1.0 |
| Achieve professional software quality | Test coverage > 80%; `ruff` and `mypy` without errors |

### Out of scope (v1.0)

- Support for Windows or macOS
- Paid certificates or other CAs (Let's Encrypt / ACME only)
- Management of multiple remote servers (SSH)
- Graphical interface (GUI or web)
- Support for distributions other than those declared (CentOS, Arch, Alpine, etc.)
- Integration with DNS services for DNS-01 validation

---

## 4. Target Users

### Primary profile — DevOps / System Administrator

- **Context:** Manages multiple Linux servers, regularly sets up new environments, works across different distributions
- **Pain point:** Manually configuring HTTPS consumes time and is a source of errors; needs to automate it in scripts or pipelines
- **Key needs:** Direct command mode, `--no-interactive` flag, multi-distro compatibility, verbose real-time output

### Secondary profile — Developer

- **Context:** Develops dockerized web applications, configures their own staging or production server
- **Pain point:** Does not know in detail the difference between Nginx and Apache configurations, does not know which Certbot plugin to use
- **Key needs:** Guided interactive mode that asks what is needed, clear and actionable error messages

### Tertiary profile — International team

- **Context:** Teams with members in different countries or languages
- **Pain point:** English-only tools create friction in Spanish-speaking teams
- **Key needs:** Interactive interface available in Spanish and English, language selection on first use

---

## 5. Product Features

### 5.1 Core capabilities (MUST — v1.0)

| Feature | Description |
|---|---|
| TLS/SSL certificate generation | Installs Certbot (per-distro: snap+symlink on Debian/Ubuntu, dnf on Fedora, zypper on openSUSE), requests a Let's Encrypt certificate with `--non-interactive --agree-tos`, configures the web server, and verifies the service with `systemctl status` |
| Nginx support | Full provider: installation, virtual host configuration, reverse proxy, syntax verification, site activation |
| Apache support | Full provider with different templates per distro family; `mod_proxy` and `mod_ssl` modules automatically enabled |
| Traefik support | Generation of `docker-compose.yml` and `traefik.yml` with integrated ACME; `acme.json` with 600 permissions |
| Multi-distro | Automatic distro detection via `/etc/os-release`; invocation of the correct package manager (`apt`, `dnf`, `zypper`) |
| Internal sudo | The CLI runs as a normal user; elevated privileges obtained granularly and transparently via `sudo` |
| Interactive mode | Navigable main menu + step-by-step wizard (6 fields with validation) + real-time execution output |
| Direct command mode | All parameters available as CLI flags; compatible with scripts and CI/CD pipelines |
| `--no-interactive` flag | Disables all prompts; fails with error if any required parameter is missing |
| Prior DNS validation | Verifies that the domain resolves to the server's IP before requesting the certificate |
| Local certificate registry | JSON at `~/.config/gen_cerbot/registry.json` tracking managed certificates |
| Lifecycle operations | `generate`, `list`, `renew`, and `remove` for complete lifecycle management |
| Multi-language support (i18n) | Interactive interface in English (default) and Spanish; language selector on first use; `--lang` flag |
| PyPI distribution | `pip install gen-cerbot` and `pipx install gen-cerbot` functional |
| .deb distribution | Native package for Debian/Ubuntu installable with `apt` or `dpkg` |
| .rpm distribution | Native package for Fedora/openSUSE installable with `dnf` or `zypper` |

### 5.2 Quality features (MUST — v1.0)

| Feature | Description |
|---|---|
| Automated test suite | 80 unit test cases (TC-001..TC-070) + 10 integration tests (TI-001..TI-010); coverage > 80% |
| CI with GitHub Actions | Tests on Ubuntu 22.04/24.04 and Fedora 40 on each PR; automatic release when publishing a tag |
| Type hints and linting | `mypy --strict` and `ruff check` without errors throughout the codebase |
| Idempotency | Re-running the command on an already-configured system does not produce errors or unnecessary changes |
| Dry-run mode | `--dry-run` shows what the command would do without applying any real changes |

### 5.3 Desirable (SHOULD — backlog v1.1+)

- Support for wildcard certificates (`*.example.com`) via DNS-01
- Integration with package repositories (PPA for Ubuntu, COPR for Fedora)
- Support for more languages (Portuguese, French)
- Plugin for `ansible` or `terraform`

---

## 6. Key Non-Functional Requirements

| Attribute | Requirement |
|---|---|
| **Performance** | `generate` completes in < 5 min (excludes package download on first installation) |
| **Security** | Rejects execution as root; `sudo` only on commands that require it; private keys never in stdout |
| **Compatibility** | Python 3.11+; Debian 11/12, Ubuntu 20.04/22.04/24.04, Fedora 38/39/40, openSUSE Leap 15.5+ |
| **Usability** | Detailed `--help` on each subcommand; clear errors indicating how to resolve them |
| **Portability** | Installable via `pip`, `.deb`, and `.rpm` without exposing Python details to the end user |
| **Maintainability** | Coverage > 80%; zero `TODO` or `FIXME` without an associated ticket in the release |

---

## 7. Constraints

- Requires internet access to contact Let's Encrypt ACME servers
- Port 80 must be free during HTTP-01 validation
- The user must have access to `sudo` (running as root is not required)
- **Certbot installation is per distro:**
  - Debian/Ubuntu: `snapd` must be installed → `snap install --classic certbot` → symlink at `/usr/local/bin/certbot`
  - Fedora: `dnf install -y certbot python3-certbot-nginx python3-certbot-apache`
  - openSUSE: `zypper install -y certbot python3-certbot-nginx python3-certbot-apache`
  - Traefik does **not** use Certbot — ACME is handled natively inside `traefik.yml`
- The Certbot `--non-interactive` flag is always used; `--agree-tos` and `--email` are required parameters

---

## 8. Success Metrics

| Metric | v1.0 target |
|---|---|
| Average TLS/SSL configuration time (interactive mode) | < 5 minutes on a clean server |
| Automated test coverage | > 80% global; critical modules > 90% |
| Supported Linux distributions | 3 families (Debian, RedHat/Fedora, SUSE) |
| Supported web servers | 3 (Nginx, Apache, Traefik) |
| Distribution formats | 3 (pip/PyPI, .deb, .rpm) |
| E2E tests passing on clean VM | Ubuntu 22.04, Fedora 40, openSUSE Leap 15.5 |
| Interactive interface languages | 2 (English, Spanish) |

---

## 9. High-Level Roadmap

| Phase | Duration | Main deliverable |
|---|---|---|
| **Phase 1:** Foundation | 1 week | Project structure, models, utils (SystemRunner, DistroDetector, PackageManager) |
| **Phase 2:** Nginx Provider | 1 week | Complete and tested Nginx provider on all 3 distros |
| **Phase 3:** Apache + Traefik | 1 week | Apache (3 templates per distro) and Traefik providers |
| **Phase 4:** Certbot Manager | 1 week | Complete certificate installation and lifecycle management |
| **Phase 5:** Full CLI | 1 week | `generate`, `list`, `renew`, `remove` subcommands functional |
| **Phase 6:** Testing & Packaging | 2 weeks | Coverage > 80%; PyPI wheel + .deb package + .rpm package |
| **Phase 7:** Interactive Mode | 1 week | Menu, guided wizard, real-time output |
| **Phase 8:** i18n Support | 1 week | Language selector, LocaleManager, en/es locales |
| **Total** | **9 weeks** | **Release v1.0.0** (target: 2026-06-02) |

---

## 10. Approvals

| Role | Name | Date | Status |
|---|---|---|---|
| Product Owner | Ernesto Crespo | — | ☐ Pending |
| Tech Lead | To be defined | — | ☐ Pending |

---

## Change History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-03-31 | Ernesto Crespo | Initial version: problem, goals, personas, MUST/SHOULD features table, NFR, constraints, success metrics, 9-phase roadmap |
| 1.1 | 2026-03-31 | Ernesto Crespo | Certbot installation detail: per-distro install method (snap+symlink/dnf/zypper), --non-interactive flag, post-cert service verification; Traefik uses ACME natively (no Certbot); snapd prerequisite for Debian/Ubuntu |
