# gen_cerbot — Implementation Plan

## Metadata

| Field | Value |
|---|---|
| **Author** | Ernesto Crespo |
| **Status** | `DRAFT` |
| **Version** | 1.6 |
| **Date** | 2026-03-31 |
| **SPEC** | [SPEC.md](./SPEC.md) |
| **Architecture** | [ARCHITECTURE.md](./ARCHITECTURE.md) |

---

## 1. Implementation Summary

The implementation of `gen_cerbot` is divided into **8 phases** (Phase 6 is 2 weeks duration; the rest 1 week each), with an estimated total of 9 weeks. The approach is bottom-up: first the project foundation is established, then web server providers are implemented, Certbot integration, certificate management operations, hardening and three packaging formats (PyPI + .deb + .rpm), interactive mode with navigable menu, and finally multi-language support.

**Total estimated duration:** 9 weeks
**Required team:** 1 Python developer
**Target date for first release:** 2026-06-02

---

## 2. Prerequisites

| Prerequisite | Owner | Status | Deadline |
|---|---|---|---|
| SPEC.md approved | Ernesto | ☐ Pending | 2026-04-07 |
| ARCHITECTURE.md approved | Ernesto | ☐ Pending | 2026-04-07 |
| Python 3.11+ development environment | Ernesto | ☐ Pending | Phase 1 |
| Ubuntu 22.04 VM for E2E tests | Ernesto | ☐ Pending | Phase 4 |
| PyPI account (for distribution) | Ernesto | ☐ Pending | Phase 6 |
| Debian 12 (Bookworm) VM for .deb package build | Ernesto | ☐ Pending | Phase 6 |
| Fedora 40 VM for .rpm package build | Ernesto | ☐ Pending | Phase 6 |
| `fakeroot`, `dpkg-dev`, `debhelper>=13`, `dh-python` installed on Debian VM | Ernesto | ☐ Pending | Phase 6 |
| `rpm-build`, `python3-devel`, `rpmlint` installed on Fedora VM | Ernesto | ☐ Pending | Phase 6 |
| PyPI API token for upload with Twine | Ernesto | ☐ Pending | Phase 6 |

---

## 3. Implementation Phases

---

### Phase 1: Foundation & Project Setup

**Duration:** 1 week
**Goal:** Establish project structure, skeleton CLI, data models, and testing system.

#### Tasks

| ID | Task | Estimate | Dependency | Status |
|---|---|---|---|---|
| F1-01 | Create project directory structure | 2h | — | ✅ Done |
| F1-02 | Configure `pyproject.toml` with dependencies and entry point | 1h | F1-01 | ✅ Done |
| F1-03 | Configure ruff, mypy, and pre-commit hooks | 1h | F1-02 | ✅ Done |
| F1-04 | Implement `core/exceptions.py` with complete hierarchy (incl. `UnsupportedDistroError`, `SudoError`) | 1h | F1-01 | ✅ Done |
| F1-05 | Implement `core/config.py` with pydantic-settings | 2h | F1-01 | ✅ Done |
| F1-06 | Implement `domain/models.py` (CertificateConfig, ServerType, DistroFamily, CertificateRecord) | 2h | F1-04 | ✅ Done |
| F1-07 | Implement `utils/system.py` (SystemRunner with `run(cmd, sudo=False)` — prepends `["sudo"]` when `sudo=True`) | 3h | F1-04 | ✅ Done |
| F1-08 | Implement `utils/distro.py` (DistroDetector: reads `/etc/os-release` → `DistroFamily`) | 2h | F1-06 | ✅ Done |
| F1-09 | Implement `utils/package_manager.py` (PackageManager ABC + AptPackageManager + DnfPackageManager + ZypperPackageManager + Factory) | 4h | F1-07, F1-08 | ✅ Done |
| F1-10 | Implement `utils/registry.py` (CertRegistry JSON) | 2h | F1-06 | ✅ Done |
| F1-11 | Implement `utils/templates.py` (Jinja2 renderer) | 2h | F1-01 | ✅ Done |
| F1-12 | Create skeleton CLI with Typer: subcommands `generate`, `list`, `renew`, `remove` (stubs) | 3h | F1-06 | ✅ Done |
| F1-13 | Configure pytest with base fixtures and test structure | 2h | F1-07 | ✅ Done |
| F1-14 | Unit tests: SystemRunner (verify prepending sudo), DistroDetector (mock /etc/os-release), PackageManager (3 implementations) | 4h | F1-07, F1-08, F1-09 | ✅ Done |
| F1-15 | Unit tests: CertRegistry, TemplateRenderer | 2h | F1-10, F1-11 | ✅ Done |

#### Done Criteria

- [x] `gen-cerbot --help` works and displays all subcommands
- [x] `gen-cerbot generate --help` shows all documented flags
- [x] `DistroDetector` correctly detects Ubuntu, Fedora, and openSUSE with `/etc/os-release` fixtures
- [x] `PackageManager` generates correct command with `sudo` for each distro
- [x] `SystemRunner.run(cmd, sudo=True)` prepends `["sudo"]` verified in tests
- [x] Utils unit tests pass with `pytest`
- [x] `ruff check .` and `mypy .` with no errors
- [x] `pyproject.toml` installable with `pip install -e .`

---

### Phase 2: Nginx Provider

**Duration:** 1 week
**Goal:** Implement Nginx Provider with config generation, installation, and validation.

#### Tasks

| ID | Task | Estimate | Dependency | Status |
|---|---|---|---|---|
| F2-01 | Implement `providers/base.py` (ServerProvider ABC — receives `PackageManager` in constructor) | 2h | F1-06 | ✅ Done |
| F2-02 | Create Jinja2 template `templates/nginx/site.conf.j2` | 2h | F1-11 | ✅ Done |
| F2-03 | Implement `providers/nginx.py`: `install()` method using `pkg_manager.install(["nginx"])` with sudo | 2h | F2-01, F1-09 | ✅ Done |
| F2-04 | Implement `providers/nginx.py`: `configure()` method — generates config and enables site (symlink on Debian, include on Fedora/SUSE) | 3h | F2-02, F2-03 | ✅ Done |
| F2-05 | Implement `providers/nginx.py`: `verify()` method — `runner.run(["nginx", "-t"], sudo=True)` | 1h | F2-04 | ✅ Done |
| F2-06 | Implement `providers/nginx.py`: `remove()` method | 2h | F2-04 | ✅ Done |
| F2-07 | Implement `providers/factory.py` (ProviderFactory.get(server_type, pkg_manager)) | 1h | F2-01 | ✅ Done |
| F2-08 | Unit tests: NginxProvider with PackageManager and SystemRunner mocked (verify sudo calls) | 4h | F2-06 | ✅ Done |
| F2-09 | Integration test: config file generation with tmp_path | 2h | F2-04 | ✅ Done |
| F2-10 | Validate generated Nginx template is syntactically correct | 1h | F2-02 | ✅ Done |

#### Done Criteria

- [x] `NginxProvider` implements all methods from `ServerProvider`
- [x] `NginxProvider` receives `PackageManager` via injection (does not instantiate directly)
- [x] Nginx template generates valid config (with reverse proxy, headers, and timeouts from original script)
- [x] `NginxProvider` tests pass with mocked PackageManager and SystemRunner
- [x] Tests verify that `install()` calls `pkg_manager.install()` and `verify()` uses `sudo=True`
- [x] Test coverage in `providers/nginx.py` > 80%

---

### Phase 3: Apache and Traefik Providers ✅

**Duration:** 1 week
**Goal:** Implement Apache and Traefik Providers.
**Status:** ✅ Done

#### Tasks

| ID | Task | Estimate | Dependency | Status |
|---|---|---|---|---|
| F3-01 | Create Apache Jinja2 templates: `vhost-debian.conf.j2`, `vhost-redhat.conf.j2`, `vhost-suse.conf.j2` | 3h | F1-11 | ✅ |
| F3-02 | Implement `providers/apache.py`: `install()` method — per-distro packages via `pkg_manager`, `sudo a2enmod` on Debian or modules via conf on Fedora/SUSE | 3h | F2-01, F1-09 | ✅ |
| F3-03 | Implement `providers/apache.py`: `configure()` method — selects template per distro + `verify()` (`sudo apachectl -t`) | 3h | F3-01, F3-02 | ✅ |
| F3-04 | Implement `providers/apache.py`: `remove()` method (`sudo a2dissite` on Debian; `rm` config on Fedora/SUSE) | 2h | F3-03 | ✅ |
| F3-05 | Unit tests: ApacheProvider with mocked PackageManager and SystemRunner — verify correct behavior for each `DistroFamily` | 4h | F3-04 | ✅ |
| F3-06 | Create Jinja2 templates for Traefik: `docker-compose.yml.j2` and `traefik.yml.j2` | 3h | F1-11 | ✅ |
| F3-07 | Implement `providers/traefik.py`: `install()` method (checks Docker — distro-agnostic) | 1h | F2-01, F1-07 | ✅ |
| F3-08 | Implement `providers/traefik.py`: `configure()` method (generates files + `acme.json` with `chmod 600`) | 3h | F3-06, F3-07 | ✅ |
| F3-09 | Implement `providers/traefik.py`: `verify()` method (`docker compose config` without sudo) | 1h | F3-08 | ✅ |
| F3-10 | Implement `providers/traefik.py`: `remove()` method | 1h | F3-08 | ✅ |
| F3-11 | Unit tests: TraefikProvider with mocked SystemRunner | 3h | F3-10 | ✅ |
| F3-12 | Register Apache and Traefik in ProviderFactory (with pkg_manager) | 1h | F3-04, F3-10, F2-07 | ✅ |

#### Done Criteria

- [x] All three providers are registered in `ProviderFactory`
- [x] `ApacheProvider` selects correct template per `DistroFamily`
- [x] `ApacheProvider` tests cover 3 `DistroFamily` with mocked PackageManager
- [x] `TraefikProvider` tests pass with mocked SystemRunner
- [x] Generated Traefik template is valid YAML
- [x] All 3 Apache templates generate valid config for their distro
- [x] `acme.json` created with 600 permissions in `TraefikProvider`

---

### Phase 4: Certbot Manager and DNS Integration

**Duration:** 1 week
**Goal:** Implement complete Certbot integration and DNS validation.

#### Tasks

| ID | Task | Estimate | Dependency | Status |
|---|---|---|---|---|
| F4-01 | Implement `utils/dns.py`: DNS resolution and comparison against local IPs | 3h | F1-07 | ☐ |
| F4-02 | Unit tests: DNSValidator with mocked socket.getaddrinfo | 2h | F4-01 | ☐ |
| F4-03 | Implement `certbot/installer.py`: `ensure_installed(distro_family, server_type)` — check if certbot is already installed via `certbot --version`; if yes, skip (idempotent) | 1h | F1-07, F1-08 | ☐ |
| F4-03a | Implement Debian/Ubuntu branch in `CertbotInstaller`: (1) check if snapd is installed via `dpkg -l snapd`; (2) if missing, `sudo apt install -y snapd`; (3) `sudo snap install --classic certbot`; (4) `sudo ln -sf /snap/bin/certbot /usr/local/bin/certbot` | 3h | F4-03 | ☐ |
| F4-03b | Implement Fedora branch in `CertbotInstaller`: `sudo dnf install -y certbot python3-certbot-nginx python3-certbot-apache` | 1h | F4-03 | ☐ |
| F4-03c | Implement openSUSE branch in `CertbotInstaller`: `sudo zypper install -y certbot python3-certbot-nginx python3-certbot-apache` | 1h | F4-03 | ☐ |
| F4-03d | Implement Traefik exception in `CertbotInstaller`: if `server_type == TRAEFIK`, skip all installation steps and return immediately | 0.5h | F4-03 | ☐ |
| F4-04 | Implement `certbot/manager.py`: method `request(domain, email, server_type, staging)` — build command per server: `--nginx` for Nginx, `--apache` for Apache; always add `--non-interactive --agree-tos --email email`; append `--staging` if `staging=True`; raise `CertbotError` on non-zero exit code | 3h | F4-03, F1-07 | ☐ |
| F4-04a | Implement `certbot/manager.py`: method `verify_service(server_type, distro_family)` — run `sudo systemctl status nginx --no-pager` for Nginx; `sudo systemctl status apache2 --no-pager` for Apache on Debian; `sudo systemctl status httpd --no-pager` for Apache on Fedora/openSUSE; `docker compose ps` for Traefik; raise `ServerConfigError` if service not active | 2h | F4-04 | ☐ |
| F4-05 | Implement `certbot/manager.py`: `renew()` and `renew_all()` methods | 2h | F4-04 | ☐ |
| F4-06 | Implement `certbot/manager.py`: `revoke()` and `delete()` methods | 2h | F4-04 | ☐ |
| F4-07 | Implement `certbot/manager.py`: `get_certificates()` method (parsing certbot certificates) | 3h | F4-04 | ☐ |
| F4-08 | Unit tests: CertbotManager with Certbot output fixtures (staging/prod) | 4h | F4-07 | ☐ |
| F4-09 | Implement `domain/services.py`: `CertbotService.generate()` — includes distro detection step + PackageManager construction before creating Provider | 5h | F4-04, F4-01, F2-07 | ☐ |
| F4-10 | Implement `--dry-run` support in CertbotService and all Providers | 2h | F4-09 | ☐ |
| F4-11 | Implement `--staging` support in CertbotManager | 1h | F4-04 | ☐ |

#### Done Criteria

- [ ] `CertbotInstaller` on Debian/Ubuntu: installs snapd if missing, runs snap install, creates symlink at `/usr/local/bin/certbot`
- [ ] `CertbotInstaller` on Fedora: runs `dnf install -y certbot python3-certbot-nginx python3-certbot-apache`
- [ ] `CertbotInstaller` on openSUSE: runs `zypper install -y certbot python3-certbot-nginx python3-certbot-apache`
- [ ] `CertbotInstaller` skips all steps if certbot is already installed (idempotent)
- [ ] `CertbotInstaller` skips all steps when `server_type == TRAEFIK`
- [ ] `CertbotManager.request()` calls `certbot --nginx` or `certbot --apache` with `--non-interactive --agree-tos --email`
- [ ] `CertbotManager.request()` functions with `--staging` flag (verified in VM)
- [ ] `CertbotManager.verify_service()` runs `systemctl status` correct service name per server+distro

---

### Phase 5: Full CLI Subcommands

**Duration:** 1 week
**Goal:** Implement `generate`, `list`, `renew`, and `remove` subcommands fully functional.

#### Tasks

| ID | Task | Estimate | Dependency | Status |
|---|---|---|---|---|
| F5-01 | Implement `generate` subcommand in `cli.py` with all flags | 3h | F4-09 | ☐ |
| F5-02 | Implement `list` subcommand in `cli.py` with rich table | 3h | F4-07, F1-08 | ☐ |
| F5-03 | Implement `CertbotService.renew()` | 2h | F4-05 | ☐ |
| F5-04 | Implement `renew` subcommand in `cli.py` | 1h | F5-03 | ☐ |
| F5-05 | Implement `CertbotService.remove()` | 3h | F4-06 | ☐ |
| F5-06 | Implement `remove` subcommand in `cli.py` with interactive confirmation | 2h | F5-05 | ☐ |
| F5-07 | Implement output with colors and progress spinners (rich) | 2h | F5-01 | ☐ |
| F5-08 | Implement logging to file `~/.local/share/gen_cerbot/gen_cerbot.log` | 2h | F5-01 | ☐ |
| F5-09 | Unit tests: CLI subcommands with Typer CliRunner | 4h | F5-06 | ☐ |
| F5-10 | Review and complete `--help` for all subcommands and flags | 1h | F5-06 | ☐ |

#### Done Criteria

- [ ] All 4 subcommands implemented and functional
- [ ] `gen-cerbot list` shows status with colors (green/yellow/red)
- [ ] `gen-cerbot remove` prompts for confirmation before executing
- [ ] Logging to file works correctly
- [ ] CLI tests pass with CliRunner
- [ ] `gen-cerbot --help` and each subcommand have complete documentation

---

### Phase 6: Testing, Hardening and Packaging

**Duration:** 2 weeks
**Goal:** Achieve test coverage > 80%, test in real environment (staging Let's Encrypt), and distribute tool in three formats: wheel on PyPI, native `.deb` package for Debian/Ubuntu, and native `.rpm` package for Fedora/openSUSE.

#### Tasks — Week 1: Testing and Hardening

| ID | Task | Estimate | Dependency | Status |
|---|---|---|---|---|
| F6-01 | Review coverage with `pytest --cov` and complete missing tests until > 80% | 4h | F5-09 | ☐ |
| F6-02 | E2E test on Ubuntu 22.04 VM: Nginx + Apache + Traefik flow with `--staging` | 3h | F5-01 | ☐ |
| F6-03 | E2E test on Fedora 40 VM: Nginx + Apache flow with `--staging` (verify `dnf` and `sudo`) | 3h | F5-01 | ☐ |
| F6-04 | E2E test on openSUSE Leap 15.5 VM: Nginx flow with `--staging` (verify `zypper` and `sudo`) | 3h | F5-01 | ☐ |
| F6-05 | Review and strengthen error handling: clear messages for unsupported distro, sudo denied, and port 80 occupied | 3h | F5-09 | ☐ |
| F6-06 | Verify CLI rejects execution as root (EUID check) on all 3 distros | 1h | F5-01 | ☐ |
| F6-07 | Verify private keys do not appear in logs or stdout | 1h | F5-08 | ☐ |
| F6-08 | Add `/etc/os-release` fixtures for Ubuntu, Fedora, and openSUSE in `tests/fixtures/` | 1h | F6-01 | ☐ |
| F6-09 | Configure GitHub Actions CI: unit tests + matrix Ubuntu 22.04/24.04 + Fedora 40 (push/PR) | 3h | F6-01 | ☐ |

#### Tasks — Week 2: Packaging PyPI + .deb + .rpm

**PyPI (wheel)**

| ID | Task | Estimate | Dependency | Status |
|---|---|---|---|---|
| F6-10 | Complete `pyproject.toml`: classifiers, `project.urls`, `project.scripts`, version-ranged dependencies | 2h | F6-01 | ☐ |
| F6-11 | Install `python-build` and `twine`; run `python -m build` → verify `.whl` + `.tar.gz` in `dist/` | 1h | F6-10 | ☐ |
| F6-12 | Publish to TestPyPI (`twine upload --repository testpypi dist/*`) and verify installation with `pip install --index-url https://test.pypi.org/simple/ gen-cerbot` | 1h | F6-11 | ☐ |
| F6-13 | Publish release v1.0.0 on PyPI (`twine upload dist/*`) and verify with `pip install gen-cerbot` from scratch | 1h | F6-12 | ☐ |
| F6-14 | Configure GitHub Actions `release.yml`: on `push tag v*` → `python -m build` + `twine upload` automatic | 2h | F6-13 | ☐ |

**Debian/Ubuntu Package (.deb)**

| ID | Task | Estimate | Dependency | Status |
|---|---|---|---|---|
| F6-15 | Create `packaging/debian/` directory with base files: `control`, `rules`, `changelog`, `compat`, `copyright`, `install` | 2h | F6-10 | ☐ |
| F6-16 | Write `packaging/debian/control`: `Package: gen-cerbot`, `Architecture: all`, `Depends: python3 (>= 3.11), python3-pip`, multi-line `Description` | 1h | F6-15 | ☐ |
| F6-17 | Write `packaging/debian/rules` with `dh $@` and `override_dh_auto_install` target that installs with `pip install --prefix=/usr --no-deps .` | 2h | F6-15 | ☐ |
| F6-18 | Write `packaging/debian/changelog` in Debian format (`dch --create`) with initial version `1.0.0-1` | 1h | F6-15 | ☐ |
| F6-19 | Write `packaging/debian/copyright` in DEP-5 format with project license | 1h | F6-15 | ☐ |
| F6-20 | Build `.deb` on Debian 12 VM: `dpkg-buildpackage -us -uc -b` → verify `gen-cerbot_1.0.0-1_all.deb` generated | 2h | F6-17, F6-18 | ☐ |
| F6-21 | Validate package with `lintian --no-tag-display-limit gen-cerbot_*.deb` — resolve critical errors | 2h | F6-20 | ☐ |
| F6-22 | Installation test on clean Ubuntu 22.04 VM: `sudo dpkg -i gen-cerbot_*.deb && gen-cerbot --version` | 1h | F6-21 | ☐ |
| F6-23 | Clean uninstallation test: `sudo apt remove gen-cerbot` leaves no residual files | 1h | F6-22 | ☐ |
| F6-24 | Add step in `release.yml` to build `.deb` and upload to GitHub Releases as artifact | 2h | F6-14, F6-21 | ☐ |

**RPM Package for Fedora/openSUSE (.rpm)**

| ID | Task | Estimate | Dependency | Status |
|---|---|---|---|---|
| F6-25 | Create `packaging/rpm/gen-cerbot.spec` with complete header: `Name`, `Version`, `Release`, `Summary`, `License`, `BuildArch: noarch`, `URL`, `Source0` | 2h | F6-10 | ☐ |
| F6-26 | Define `%description` section and `Requires: python3 >= 3.11`; add `BuildRequires: python3-pip python3-build` | 1h | F6-25 | ☐ |
| F6-27 | Implement `%prep` (uncompress tarball), `%build` (empty for pure Python package), `%install` (`pip install --prefix=%{buildroot}/usr --no-deps .`) sections in `.spec` | 2h | F6-26 | ☐ |
| F6-28 | Implement `%files` section in `.spec`: `/usr/bin/gen-cerbot`, `/usr/lib/python3*/site-packages/gen_cerbot*`; add `%license LICENSE`, `%doc README.md` | 2h | F6-27 | ☐ |
| F6-29 | Build `.rpm` on Fedora 40 VM: configure `~/rpmbuild/` with `rpmdev-setuptree`, copy tarball to `SOURCES/`, run `rpmbuild -bb packaging/rpm/gen-cerbot.spec` | 2h | F6-28 | ☐ |
| F6-30 | Validate package with `rpmlint gen-cerbot-*.noarch.rpm` — resolve critical errors | 2h | F6-29 | ☐ |
| F6-31 | Installation test on clean Fedora 40 VM: `sudo dnf install ./gen-cerbot-*.rpm && gen-cerbot --version` | 1h | F6-30 | ☐ |
| F6-32 | Installation test on openSUSE Leap 15.5 VM: `sudo zypper install ./gen-cerbot-*.rpm && gen-cerbot --version` | 1h | F6-30 | ☐ |
| F6-33 | Uninstallation test: `sudo dnf remove gen-cerbot` and `sudo zypper remove gen-cerbot` on their respective VMs | 1h | F6-31, F6-32 | ☐ |
| F6-34 | Add step in `release.yml` to build `.rpm` and upload to GitHub Releases as artifact | 2h | F6-24, F6-30 | ☐ |

#### Packaging file structure generated

```
packaging/
├── debian/
│   ├── changelog       # Version history in Debian format
│   ├── compat          # debhelper compatibility level (13)
│   ├── control         # Package metadata and dependencies
│   ├── copyright       # License in DEP-5 format
│   ├── install         # List of files to include in package
│   └── rules           # Build script (Makefile with dh helper)
└── rpm/
    └── gen-cerbot.spec # Complete spec file for rpmbuild
```

#### Done Criteria

- [ ] `pytest --cov` reports coverage > 80%
- [ ] E2E tests pass on Ubuntu 22.04 (staging), Fedora 40, and openSUSE Leap 15.5
- [ ] `pip install gen-cerbot` works from PyPI — `gen-cerbot --version` OK
- [ ] `pip install gen-cerbot` works from TestPyPI before final publication
- [ ] `python -m build` generates `.whl` + `.tar.gz` without errors
- [ ] `sudo dpkg -i gen-cerbot_*.deb && gen-cerbot --version` works on clean Ubuntu 22.04
- [ ] `lintian gen-cerbot_*.deb` no critical errors (level E)
- [ ] `sudo dnf install ./gen-cerbot-*.rpm && gen-cerbot --version` works on clean Fedora 40
- [ ] `sudo zypper install ./gen-cerbot-*.rpm && gen-cerbot --version` works on openSUSE Leap 15.5
- [ ] `rpmlint gen-cerbot-*.rpm` no critical errors
- [ ] GitHub Releases v1.0.0 contains `.whl`, `.tar.gz`, `.deb`, and `.rpm` as artifacts
- [ ] `release.yml` automates build and upload of all 4 artifacts on each `v*` tag
- [ ] CI green on GitHub Actions for Ubuntu 22.04, 24.04, and Fedora 40

---

### Phase 7: Interactive Mode

**Duration:** 1 week
**Goal:** Implement interactive mode with main menu, guided wizard for generating certificates, and real-time execution output.

#### Tasks

| ID | Task | Estimate | Dependency | Status |
|---|---|---|---|---|
| F7-01 | Add `questionary>=2.0` to `pyproject.toml` and verify compatibility with Typer/rich | 1h | F5-01 | ☐ |
| F7-02 | Implement `interactive/output.py` (LiveOutputRenderer): capture SystemRunner stdout and render with `rich.live` showing `[✔]`/`[→]`/`[✗]` per step | 4h | F5-08 | ☐ |
| F7-03 | Implement `interactive/wizard.py` (GenerateWizard): sequentially request subdomain, port, pkg-family (`deb`/`rpm`), web server, email, and project name; validate each field inline | 4h | F7-01 | ☐ |
| F7-04 | Add summary screen and confirmation `Continue?` at end of GenerateWizard | 1h | F7-03 | ☐ |
| F7-05 | Implement `interactive/menu.py` (InteractiveMenu): main menu with 5 options (Generate, List, Renew, Delete, Exit); navigate with arrows and Enter | 3h | F7-03 | ☐ |
| F7-06 | Modify `cli.py`: detect invocation without arguments → launch `InteractiveMenu.run()`; with arguments → existing Typer behavior | 2h | F7-05 | ☐ |
| F7-07 | Add `--no-interactive` flag to `generate` to disable prompts in CI/CD (fails if required parameter missing) | 1h | F7-06 | ☐ |
| F7-08 | Add `--pkg-family deb\|rpm` flag to `generate` to specify family from command line | 1h | F7-06 | ☐ |
| F7-09 | Connect LiveOutputRenderer with CertbotService: each flow step emits events that renderer captures and displays | 3h | F7-02, F5-01 | ☐ |
| F7-10 | Error handling in interactive mode: `[✗]` with message + "Retry / Back to menu" option | 2h | F7-05, F7-09 | ☐ |
| F7-11 | Handle `Ctrl+C` in interactive mode: clean exit with message | 1h | F7-05 | ☐ |
| F7-12 | Unit tests: GenerateWizard with mocked responses via `questionary`'s `unsafe_ask` | 3h | F7-04 | ☐ |
| F7-13 | Unit tests: InteractiveMenu with simulated navigation | 2h | F7-05 | ☐ |
| F7-14 | Unit tests: LiveOutputRenderer with `rich.Console(file=io.StringIO())` | 2h | F7-02 | ☐ |
| F7-15 | Manual E2E test of complete interactive mode flow in real terminal (Ubuntu + Fedora) | 2h | F7-10 | ☐ |

#### Done Criteria

- [ ] `gen-cerbot` without arguments shows navigable main menu
- [ ] Wizard requests 6 fields (subdomain, port, pkg-family, server, email, project) with validation
- [ ] `deb`/`rpm` selection determines PackageManager used internally
- [ ] Summary screen displays all values before executing
- [ ] Real-time output shows each step with `[✔]`/`[→]`/`[✗]`
- [ ] Executed `sudo` commands visible on screen
- [ ] `Ctrl+C` terminates cleanly without stack trace
- [ ] `gen-cerbot generate --no-interactive ...` works for CI/CD
- [ ] Tests of `interactive/` module pass without real terminal (mocked questionary)
- [ ] Interactive mode works correctly on Ubuntu 22.04 and Fedora 40

---

### Phase 8: Multi-language Support (i18n)

**Duration:** 1 week
**Goal:** Implement internationalization system with `LocaleManager`, JSON locale files, language selector before menu, `--lang` flag, and user preference persistence.

#### Tasks

| ID | Task | Estimate | Dependency | Status |
|---|---|---|---|---|
| F8-01 | Create `i18n/` module with `__init__.py`; add dependencies (no extra — stdlib `json` + `tomllib`/`tomli` only) | 1h | F7-01 | ☐ |
| F8-02 | Implement `i18n/locale_manager.py` (singleton `LocaleManager`): `set_lang(code)`, `t(key, **kwargs)` with `str.format_map` interpolation, fallback to `en` if key missing | 3h | F8-01 | ☐ |
| F8-03 | Create `i18n/locales/en.json` with all interactive interface strings in English (~40 keys: menu, wizard, output, errors) | 2h | F8-02 | ☐ |
| F8-04 | Create `i18n/locales/es.json` with Spanish translation of all keys defined in `en.json` | 2h | F8-03 | ☐ |
| F8-05 | Implement `i18n/selector.py` (LanguageSelector): read lang from `config.toml`; if missing → prompt `questionary.select` with options "English / Español"; save selection in `config.toml` | 3h | F8-02 | ☐ |
| F8-06 | Modify `cli.py`: add global `--lang <code>` flag (Typer callback); if present → `LocaleManager.set_lang(code)` and skip selector; integrate `LanguageSelector.resolve()` before `InteractiveMenu.run()` | 2h | F8-05 | ☐ |
| F8-07 | Replace all hardcoded strings in `interactive/menu.py`, `interactive/wizard.py`, and `interactive/output.py` with `LocaleManager.t("key")` calls | 3h | F8-06 | ☐ |
| F8-08 | Add `SupportedLang` enum to `domain/models.py`; add `lang: str = "en"` field to `CertificateConfig` | 1h | F8-02 | ☐ |
| F8-09 | Read/write language preference in `~/.config/gen_cerbot/config.toml` via `core/config.py` | 2h | F8-05 | ☐ |
| F8-10 | Unit tests: `LocaleManager` — fallback to `en` for missing key, `{variable}` interpolation, runtime language change | 3h | F8-04 | ☐ |
| F8-11 | Unit tests: `LanguageSelector` — mock existing `config.toml`, mock `questionary`, verify persistence | 2h | F8-05 | ☐ |
| F8-12 | Manual E2E test: `gen-cerbot` without args shows language selector → select `es` → menu in Spanish; second run does not show selector | 1h | F8-07 | ☐ |
| F8-13 | Manual test: `gen-cerbot --lang en` and `gen-cerbot --lang es` skip selector and show menu in corresponding language | 1h | F8-06 | ☐ |

#### Done Criteria

- [ ] `gen-cerbot` without args (first run) shows language selector before menu
- [ ] After selecting language, all menu and wizard strings display in that language
- [ ] Preference saved in `config.toml`; subsequent sessions do not show selector
- [ ] `gen-cerbot --lang es` forces language without selector
- [ ] Missing key in `es.json` → transparent fallback to English text
- [ ] Variable interpolation works: `t("output.done", domain="app.example.com")`
- [ ] Tests of `i18n/` module pass with coverage > 90%

---

## 4. Dependency Map

```
Phase 1: Foundation & Setup
  │
  ├──▶ Phase 2: Nginx Provider
  │       │
  │       └──▶ Phase 3: Apache and Traefik Providers
  │                 │
  ├──▶ Phase 4: Certbot Manager + DNS ◀───────────┘
  │       │
  │       └──▶ Phase 5: Full CLI Subcommands
  │                 │
  │                 ├──▶ Phase 6: Testing, Hardening & PyPI
  │                 │
  └─────────────────└──▶ Phase 7: Interactive Mode
                               │
                               └──▶ Phase 8: i18n Support
```

---

## 5. Implementation Risks

| Risk | Probability | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Let's Encrypt rate limit during testing | High | Medium | Always use `--staging` in development; unit tests with mocks | Ernesto |
| Certbot behavior differences across distros (snap vs dnf vs zypper) | High | High | E2E tests on 3 VMs; CertbotInstaller abstracts per-distro installation | Ernesto |
| Different package names across distros | Medium | Medium | Explicit mapping in each PackageManager implementation; tests with real packages in VMs | Ernesto |
| sudo with interactive password in CI | Medium | High | Configure `NOPASSWD` in CI runner sudoers; document requirement | Ernesto |
| Changes in `certbot certificates` output (parsing) | Low | Medium | Tests with real output fixtures; minimum Certbot version pinned | Ernesto |
| Port 80 occupied in E2E test environment | Medium | Medium | Document test environment prerequisites; use clean VMs | Ernesto |
| Complexity of edge cases in Traefik config | Medium | Medium | Iterate with real cases; resolve open ARCHITECTURE.md questions before Phase 3 | Ernesto |
| Terminal without ANSI support (SSH headless) | Medium | Medium | questionary and rich degrade gracefully; add `--no-interactive` flag for these cases | Ernesto |
| Interactive mode tests without real terminal | Medium | Medium | Use `questionary`'s `unsafe_ask` with fixtures; `rich.Console(file=StringIO())` to capture output | Ernesto |
| Incomplete translations in `es.json` break UX | Low | Medium | Automatic fallback to `en` key in `LocaleManager.t()`; CI verifies `es.json` has all keys from `en.json` | Ernesto |

---

## 6. Global Definition of Done

- [ ] Code implemented, tested, and merged to `main`
- [ ] Unit and integration tests pass (`pytest`)
- [ ] `ruff check .` with no errors
- [ ] `mypy .` with no errors (strict mode)
- [ ] Test coverage > 80% (`pytest --cov`)
- [ ] Documentation updated (README.md, --help for each subcommand, menu mockup in README)
- [ ] Interactive mode functional: menu, wizard, and real-time output verified manually
- [ ] `gen-cerbot` without args opens menu; with args works as direct command
- [ ] Language selector appears on first run; preference persisted in `config.toml`
- [ ] `gen-cerbot --lang es` and `gen-cerbot --lang en` work correctly
- [ ] All interactive texts use `LocaleManager.t("key")` — zero hardcoded strings
- [ ] `pip install gen-cerbot` works from PyPI
- [ ] `sudo dpkg -i gen-cerbot_*.deb && gen-cerbot --version` OK on Ubuntu 22.04
- [ ] `sudo dnf install ./gen-cerbot-*.rpm && gen-cerbot --version` OK on Fedora 40
- [ ] `sudo zypper install ./gen-cerbot-*.rpm && gen-cerbot --version` OK on openSUSE Leap 15.5
- [ ] GitHub Releases v1.0.0 contains `.whl`, `.tar.gz`, `.deb`, and `.rpm`
- [ ] Manual E2E tests passing on Ubuntu 22.04 VM
- [ ] SPEC.md and ARCHITECTURE.md updated if changes during implementation
- [ ] No `TODO` or `FIXME` without corresponding ticket in code

---

## 7. Test Case Catalog

Reference catalog of all required tests. Serves as contract between design (ARCHITECTURE.md §8) and implementation. Each test case corresponds to a test function in the indicated file.

### 7.1 Unit Tests — `utils/`

| ID | File | Test | Input / Scenario | Expected result | Mock |
|---|---|---|---|---|---|
| TC-001 | `test_system_runner.py` | `test_run_prepends_sudo` | `run(["nginx", "-t"], sudo=True)` | `subprocess.run` called with `["sudo", "nginx", "-t"]` | `subprocess.run` |
| TC-002 | `test_system_runner.py` | `test_run_without_sudo` | `run(["ls"], sudo=False)` | `subprocess.run` called with `["ls"]` (no sudo) | `subprocess.run` |
| TC-003 | `test_system_runner.py` | `test_run_nonzero_raises` | `subprocess.run` returns `returncode=1` | Raises `SystemCommandError` with exit code and cmd | `subprocess.run` |
| TC-004 | `test_system_runner.py` | `test_run_captures_stdout` | `subprocess.run` returns `stdout="output"` | `result.stdout == "output"` | `subprocess.run` |
| TC-005 | `test_distro_detector.py` | `test_detect_ubuntu_2204` | fixture `ubuntu-22.04` in `tmp_path` | `DistroFamily.DEBIAN` | `/etc/os-release` via `tmp_path` |
| TC-006 | `test_distro_detector.py` | `test_detect_debian_12` | fixture `debian-12` in `tmp_path` | `DistroFamily.DEBIAN` | `/etc/os-release` via `tmp_path` |
| TC-007 | `test_distro_detector.py` | `test_detect_fedora_40` | fixture `fedora-40` in `tmp_path` | `DistroFamily.REDHAT` | `/etc/os-release` via `tmp_path` |
| TC-008 | `test_distro_detector.py` | `test_detect_opensuse_leap` | fixture `opensuse-leap-15.5` in `tmp_path` | `DistroFamily.SUSE` | `/etc/os-release` via `tmp_path` |
| TC-009 | `test_distro_detector.py` | `test_detect_unknown_raises` | fixture `unknown-distro` in `tmp_path` | Raises `UnsupportedDistroError` | `/etc/os-release` via `tmp_path` |
| TC-010 | `test_package_manager.py` | `test_apt_install_cmd` | `apt.install(["nginx", "certbot"])` | cmd contains `apt-get install -y nginx certbot` with sudo | `SystemRunner` mock |
| TC-011 | `test_package_manager.py` | `test_dnf_install_cmd` | `dnf.install(["httpd"])` | cmd contains `dnf install -y httpd` with sudo | `SystemRunner` mock |
| TC-012 | `test_package_manager.py` | `test_zypper_install_cmd` | `zypper.install(["nginx"])` | cmd contains `zypper install -y nginx` with sudo | `SystemRunner` mock |
| TC-013 | `test_package_manager.py` | `test_is_installed_no_sudo` | `apt.is_installed("nginx")` | cmd does not contain sudo | `SystemRunner` mock |
| TC-014 | `test_dns_validator.py` | `test_dns_ok` | `socket.getaddrinfo` returns server IP | Does not raise exception | `socket.getaddrinfo` |
| TC-015 | `test_dns_validator.py` | `test_dns_mismatch_raises` | `getaddrinfo` returns different IP from local | Raises `DNSValidationError` with IPs in message | `socket.getaddrinfo` |
| TC-016 | `test_dns_validator.py` | `test_skip_dns_check_bypasses` | `CertificateConfig(skip_dns_check=True)` | Does not call `socket.getaddrinfo` | `socket.getaddrinfo` (not called) |
| TC-017 | `test_cert_registry.py` | `test_add_creates_entry` | `registry.add(record)` on `tmp_config` | JSON on disk contains the record | `tmp_path` |
| TC-018 | `test_cert_registry.py` | `test_list_empty` | `registry.list()` with no previous records | Returns empty list | `tmp_path` |
| TC-019 | `test_cert_registry.py` | `test_remove_existing` | `registry.remove("app.example.com")` | Record deleted from JSON | `tmp_path` |
| TC-020 | `test_cert_registry.py` | `test_add_idempotent` | `registry.add(record)` twice | Only one record in JSON | `tmp_path` |
| TC-021 | `test_template_renderer.py` | `test_render_nginx_contains_domain` | `render("nginx/site.conf.j2", config)` | Output contains `server_name app.example.com` | `tmp_path` |
| TC-022 | `test_template_renderer.py` | `test_render_apache_debian_uses_apache2` | `render("apache/vhost-debian.conf.j2", ...)` | Output contains `DocumentRoot` and `ProxyPass` | `tmp_path` |
| TC-023 | `test_template_renderer.py` | `test_render_traefik_compose_has_service` | `render("traefik/docker-compose.yml.j2", ...)` | Output valid YAML with `traefik` and `app` services | `tmp_path` |

### 7.2 Unit Tests — `providers/`

| ID | File | Test | Scenario | Expected result | Mock |
|---|---|---|---|---|---|
| TC-024 | `test_nginx_provider.py` | `test_install_calls_pkg_manager` | `nginx.install()` | `pkg_manager.install(["nginx", ...])` called | `PackageManager`, `SystemRunner` |
| TC-025 | `test_nginx_provider.py` | `test_configure_calls_template_renderer` | `nginx.configure(config)` | `template_renderer.render(...)` called with `config` | `TemplateRenderer` mock |
| TC-026 | `test_nginx_provider.py` | `test_verify_uses_sudo` | `nginx.verify()` | `runner.run(["nginx", "-t"], sudo=True)` | `SystemRunner` |
| TC-027 | `test_nginx_provider.py` | `test_remove_unlinks_site` | `nginx.remove("myapp")` | `runner.run(["unlink", ...], sudo=True)` and `reload` | `SystemRunner` |
| TC-028 | `test_apache_provider.py` | `test_install_debian_uses_apache2` | `DistroFamily.DEBIAN` | `pkg_manager.install(["apache2", ...])` | `PackageManager`, `SystemRunner` |
| TC-029 | `test_apache_provider.py` | `test_install_redhat_uses_httpd` | `DistroFamily.REDHAT` | `pkg_manager.install(["httpd", ...])` | `PackageManager`, `SystemRunner` |
| TC-030 | `test_apache_provider.py` | `test_install_suse_uses_apache2` | `DistroFamily.SUSE` | `pkg_manager.install(["apache2", ...])` | `PackageManager`, `SystemRunner` |
| TC-031 | `test_apache_provider.py` | `test_configure_uses_distro_template` | `configure(config, DistroFamily.REDHAT)` | Template `vhost-redhat.conf.j2` selected | `TemplateRenderer` mock |
| TC-032 | `test_traefik_provider.py` | `test_configure_creates_files` | `traefik.configure(config)` | docker-compose.yml and traefik.yml created in `tmp_path` | `SystemRunner`, `tmp_path` |
| TC-033 | `test_traefik_provider.py` | `test_acme_json_permissions` | `traefik.configure(config)` | `runner.run(["chmod", "600", "acme.json"], sudo=True)` | `SystemRunner` |

### 7.3 Unit Tests — `certbot/`

| ID | File | Test | Scenario | Expected result | Mock |
|---|---|---|---|---|---|
| TC-034 | `test_certbot_installer.py` | `test_install_debian_checks_snapd` | `DistroFamily.DEBIAN`, snapd not installed | cmd contains `apt install -y snapd` before snap install | `SystemRunner` |
| TC-034a | `test_certbot_installer.py` | `test_install_debian_runs_snap_install` | `DistroFamily.DEBIAN` | cmd contains `snap install --classic certbot` with sudo | `SystemRunner` |
| TC-034b | `test_certbot_installer.py` | `test_install_debian_creates_symlink` | `DistroFamily.DEBIAN` | cmd contains `ln -sf /snap/bin/certbot /usr/local/bin/certbot` with sudo | `SystemRunner` |
| TC-035 | `test_certbot_installer.py` | `test_install_fedora_uses_dnf` | `DistroFamily.REDHAT` | cmd contains `dnf install -y certbot python3-certbot-nginx python3-certbot-apache` with sudo | `SystemRunner` |
| TC-036 | `test_certbot_installer.py` | `test_install_suse_uses_zypper` | `DistroFamily.SUSE` | cmd contains `zypper install -y certbot python3-certbot-nginx python3-certbot-apache` with sudo | `SystemRunner` |
| TC-037 | `test_certbot_installer.py` | `test_skip_if_already_installed` | `certbot --version` returns `returncode=0` | No installation commands executed | `SystemRunner` |
| TC-037a | `test_certbot_installer.py` | `test_skip_for_traefik` | `server_type=TRAEFIK` | No commands executed at all | `SystemRunner` (not called) |
| TC-038 | `test_certbot_manager.py` | `test_request_nginx_cmd` | `request(domain, email, server_type=NGINX)` | cmd is `certbot --nginx -d domain --non-interactive --agree-tos --email email` with sudo | `SystemRunner` |
| TC-038a | `test_certbot_manager.py` | `test_request_apache_cmd` | `request(domain, email, server_type=APACHE)` | cmd is `certbot --apache -d domain --non-interactive --agree-tos --email email` with sudo | `SystemRunner` |
| TC-039 | `test_certbot_manager.py` | `test_request_staging_flag` | `staging=True` | cmd contains `--staging` appended | `SystemRunner` |
| TC-039a | `test_certbot_manager.py` | `test_verify_service_nginx` | `verify_service(NGINX, any)` | cmd is `systemctl status nginx --no-pager` with sudo | `SystemRunner` |
| TC-039b | `test_certbot_manager.py` | `test_verify_service_apache_debian` | `verify_service(APACHE, DEBIAN)` | cmd is `systemctl status apache2 --no-pager` with sudo | `SystemRunner` |
| TC-039c | `test_certbot_manager.py` | `test_verify_service_apache_fedora` | `verify_service(APACHE, REDHAT)` | cmd is `systemctl status httpd --no-pager` with sudo | `SystemRunner` |
| TC-039d | `test_certbot_manager.py` | `test_verify_service_raises_on_inactive` | `runner.run` returns `returncode=3` | raises `ServerConfigError` | `SystemRunner` |
| TC-040 | `test_certbot_manager.py` | `test_renew_cmd` | `manager.renew()` | cmd contains `certbot renew` with sudo | `SystemRunner` |
| TC-041 | `test_certbot_manager.py` | `test_revoke_cmd` | `manager.revoke("app.example.com")` | cmd contains `certbot revoke --cert-name` with sudo | `SystemRunner` |
| TC-042 | `test_certbot_manager.py` | `test_list_parses_fixture_ok` | stdout = fixture `certificates_ok.txt` | returns list with 2 `CertificateRecord` | `SystemRunner` with fixture |
| TC-043 | `test_certbot_manager.py` | `test_list_returns_empty_when_no_certs` | stdout = fixture `certificates_empty.txt` | returns empty list | `SystemRunner` with fixture |

### 7.4 Unit Tests — `domain/`

| ID | File | Test | Scenario | Expected result | Mock |
|---|---|---|---|---|---|
| TC-044 | `test_certbot_service.py` | `test_generate_calls_dns_check` | `service.generate(config)` | `dns_validator.check(config.domain)` called | all deps |
| TC-045 | `test_certbot_service.py` | `test_generate_skip_dns_when_flag` | `config.skip_dns_check=True` | `dns_validator.check` not called | all deps |
| TC-046 | `test_certbot_service.py` | `test_generate_sequence` | `service.generate(config)` happy path | sequence: DNS → install → configure → verify → certbot | all deps |
| TC-047 | `test_certbot_service.py` | `test_generate_aborts_on_dns_error` | `dns_validator.check` raises `DNSValidationError` | `generate` propagates exception, does not continue | all deps |
| TC-048 | `test_certbot_service.py` | `test_generate_aborts_on_root` | `os.geteuid() == 0` | raises `SudoError` before any action | `os.geteuid` mock |
| TC-049 | `test_certbot_service.py` | `test_list_delegates_to_certbot_manager` | `service.list()` | returns what `certbot_manager.list_certificates()` returns | `CertbotManager` mock |
| TC-050 | `test_certbot_service.py` | `test_renew_delegates_to_certbot_manager` | `service.renew()` | `certbot_manager.renew()` called | `CertbotManager` mock |
| TC-051 | `test_certbot_service.py` | `test_remove_sequence` | `service.remove("app.example.com")` | revoke → remove config → registry.remove | all deps |

### 7.5 Unit Tests — CLI, interactive/ and i18n/

| ID | File | Test | Scenario | Expected result | Mock |
|---|---|---|---|---|---|
| TC-052 | `test_cli.py` | `test_generate_exits_0_with_all_flags` | `generate --server nginx --domain X --port 8080 --project Y --email Z` | exit code 0 | `CertbotService` mock via `CliRunner` |
| TC-053 | `test_cli.py` | `test_generate_exits_nonzero_missing_domain` | `generate --server nginx --no-interactive` (no `--domain`) | exit code != 0, error message | `CliRunner` |
| TC-054 | `test_cli.py` | `test_list_calls_service_list` | `gen-cerbot list` | `service.list()` called; exit code 0 | `CertbotService` mock |
| TC-055 | `test_cli.py` | `test_version_flag` | `gen-cerbot --version` | output contains package version | none |
| TC-056 | `test_cli.py` | `test_lang_flag_sets_locale` | `gen-cerbot --lang es generate ...` | `LocaleManager.set_lang("es")` called before Typer | `LocaleManager` mock |
| TC-057 | `interactive/test_wizard.py` | `test_wizard_happy_path` | predefined responses for 6 fields | returns `CertificateConfig` with correct values | `questionary.unsafe_ask` |
| TC-058 | `interactive/test_wizard.py` | `test_wizard_rejects_invalid_email` | email `"not-an-email"` | re-prompts (does not advance) | `questionary` mock |
| TC-059 | `interactive/test_wizard.py` | `test_wizard_rejects_invalid_port` | port `"99999"` | re-prompts (does not advance) | `questionary` mock |
| TC-060 | `interactive/test_menu.py` | `test_menu_generate_routes_to_wizard` | "Generate certificate" selection | calls `wizard.run()` | `questionary.select`, `GenerateWizard` mock |
| TC-061 | `interactive/test_menu.py` | `test_menu_exit_calls_sys_exit` | "Exit" selection | `sys.exit(0)` called | `questionary.select`, `sys.exit` mock |
| TC-062 | `interactive/test_output.py` | `test_renderer_shows_check_on_success` | `renderer.step("Installing", success=True)` | captured output contains `[✔]` | `rich.Console(file=StringIO())` |
| TC-063 | `interactive/test_output.py` | `test_renderer_shows_cross_on_failure` | `renderer.step("Installing", success=False)` | captured output contains `[✗]` | `rich.Console(file=StringIO())` |
| TC-064 | `i18n/test_locale_manager.py` | `test_t_returns_correct_en_string` | `manager.set_lang("en"); manager.t("menu.exit")` | `"Exit"` | JSON in `tmp_path` |
| TC-065 | `i18n/test_locale_manager.py` | `test_t_returns_correct_es_string` | `manager.set_lang("es"); manager.t("menu.exit")` | `"Salir"` | JSON in `tmp_path` |
| TC-066 | `i18n/test_locale_manager.py` | `test_t_falls_back_to_en_for_missing_key` | key exists in `en.json` but not in `es.json` | returns English value, no exception | partial JSON in `tmp_path` |
| TC-067 | `i18n/test_locale_manager.py` | `test_t_interpolates_variables` | `manager.t("output.done", domain="app.example.com")` | string with interpolated domain | JSON in `tmp_path` |
| TC-068 | `i18n/test_language_selector.py` | `test_resolve_reads_saved_preference` | `config.toml` contains `lang = "es"` | `LocaleManager.set_lang("es")` called; no prompt | `config.toml` in `tmp_path`, `questionary` mock |
| TC-069 | `i18n/test_language_selector.py` | `test_resolve_shows_prompt_on_first_run` | `config.toml` does not exist | `questionary.select` prompt shown; response persisted | `questionary.select` mock |
| TC-070 | `i18n/test_language_selector.py` | `test_resolve_lang_flag_skips_prompt` | `--lang es` passed | `set_lang("es")` without prompt or `config.toml` read | `questionary` not called |

### 7.6 Integration Tests

| ID | File | Test | What is tested | Real deps | Mocked deps |
|---|---|---|---|---|---|
| TI-001 | `test_nginx_config_gen.py` | `test_nginx_configure_creates_valid_file` | Nginx config file generated in `tmp_path` contains domain, port, and correct headers | `NginxProvider`, `TemplateRenderer`, `CertificateConfig` | `SystemRunner` |
| TI-002 | `test_apache_config_gen.py` | `test_apache_debian_template_selected` | `ApacheProvider` with `DistroFamily.DEBIAN` generates VirtualHost with `apache2` syntax | `ApacheProvider`, `TemplateRenderer` | `SystemRunner`, `PackageManager` |
| TI-003 | `test_apache_config_gen.py` | `test_apache_redhat_template_selected` | `ApacheProvider` with `DistroFamily.REDHAT` generates VirtualHost with `httpd` syntax | `ApacheProvider`, `TemplateRenderer` | `SystemRunner`, `PackageManager` |
| TI-004 | `test_apache_config_gen.py` | `test_apache_suse_template_selected` | `ApacheProvider` with `DistroFamily.SUSE` generates correct VirtualHost | `ApacheProvider`, `TemplateRenderer` | `SystemRunner`, `PackageManager` |
| TI-005 | `test_traefik_config_gen.py` | `test_traefik_generates_compose_and_yml` | `TraefikProvider` generates `docker-compose.yml` and `traefik.yml` in `tmp_path`; YAML parseable | `TraefikProvider`, `TemplateRenderer` | `SystemRunner` |
| TI-006 | `test_traefik_config_gen.py` | `test_traefik_acme_json_chmod_600` | `runner.run(["chmod", "600", ...])` called with `sudo=True` | `TraefikProvider` | `SystemRunner` mock that records calls |
| TI-007 | `test_certbot_output.py` | `test_parse_certificates_ok_fixture` | `CertbotManager.list_certificates()` parses fixture → 2 records with domain and expiration | `CertbotManager` | `SystemRunner` with stdout = fixture |
| TI-008 | `test_certbot_output.py` | `test_parse_certificates_empty_fixture` | `CertbotManager.list_certificates()` returns `[]` with empty fixture | `CertbotManager` | `SystemRunner` with stdout = fixture |
| TI-009 | `test_cert_registry_io.py` | `test_registry_persists_and_reads_back` | `add` + `list` + `remove` on real JSON in `tmp_path` | `CertRegistry` | none |
| TI-010 | `test_full_flow.py` | `test_generate_full_flow_nginx_debian` | Complete `CertbotService.generate()` flow with Nginx on Debian; verifies mock sequence | `CertbotService`, `NginxProvider`, `CertbotManager`, `CertRegistry` | `SystemRunner`, `socket.getaddrinfo`, `tmp_path` |
| TI-011 | `test_certbot_installer_flow.py` | `test_certbot_install_debian_full_sequence` | `CertbotInstaller` on Debian: snapd check → snap install → symlink; verifies all 3 commands called in order | `CertbotInstaller` | `SystemRunner` mock recording call order |
| TI-012 | `test_certbot_installer_flow.py` | `test_certbot_verify_service_nginx` | `CertbotManager.verify_service(NGINX)` calls systemctl correctly and returns on success | `CertbotManager` | `SystemRunner` mock returning returncode=0 |

---

## Change History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-03-31 | Ernesto Crespo | Initial version: 6 phases, Nginx/Apache/Traefik, Certbot, CLI Typer |
| 1.1 | 2026-03-31 | Ernesto Crespo | Multi-distro support: F1-07 SystemRunner sudo, F1-08 DistroDetector, F1-09 PackageManager (apt/dnf/zypper); new Fedora VM in prerequisites; 2 new distro risks |
| 1.2 | 2026-03-31 | Ernesto Crespo | Interactive mode: Phase 7 complete (15 tasks F7-01..F7-15); dependency map updated; summary corrected to 7 phases/7 weeks; 2 new terminal/TUI risks |
| 1.3 | 2026-03-31 | Ernesto Crespo | i18n support: Phase 8 complete (13 tasks F8-01..F8-13); summary 8 phases/8 weeks/2026-05-26; dependency map Phase 7→Phase 8; new incomplete translations risk; DoD updated with i18n criteria |
| 1.4 | 2026-03-31 | Ernesto Crespo | Native packaging: Phase 6 expanded to 2 weeks with 25 tasks (F6-10..F6-34) for PyPI wheel, .deb (debian/), and .rpm (rpm/spec); build prerequisites; summary 9 weeks/2026-06-02; packaging/ structure; global DoD with native installation criteria |
| 1.5 | 2026-03-31 | Ernesto Crespo | Test catalog: new Section 7 with 80 test cases (TC-001..TC-070 unit + TI-001..TI-010 integration) organized by module with inputs, expected results, and mock strategy; covers utils, providers, certbot, domain/services, CLI, interactive, i18n |
| 1.6 | 2026-03-31 | Ernesto Crespo | Certbot installation detail: F4-03 expanded into F4-03/F4-03a/F4-03b/F4-03c/F4-03d (snapd pre-check, snap install, symlink, dnf branch, zypper branch, traefik skip); F4-04 enhanced with --non-interactive --agree-tos; F4-04a added for verify_service(); TC-034..TC-039 expanded with snapd/symlink/server-specific tests; TI-011..TI-012 added |
