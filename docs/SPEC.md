# gen_cerbot — TLS/SSL Certificate Generation CLI

## Product Requirements Document (PRD)

| Field | Value |
|---|---|
| **Author** | Ernesto Crespo |
| **Status** | `DRAFT` |
| **Version** | 1.6 |
| **Date** | 2026-03-31 |
| **Reviewers** | To be defined |
| **Last updated** | 2026-03-31 |

---

## 1. Executive Summary

`gen_cerbot` is a Python CLI tool that automates TLS/SSL certificate configuration for web servers Nginx, Apache, and Traefik using Let's Encrypt (Certbot). The goal is to eliminate the manual and error-prone process of installing dependencies, editing configuration files, and requesting certificates: the user simply declares their parameters in the CLI and the tool handles the complete process.

The tool offers two modes of use: an **interactive mode** with a guided menu where the user selects options step by step and sees execution output in real time, and a **direct command mode** where all parameters are passed as flags for use in scripts and CI/CD. In interactive mode the user specifies: the subdomain, the port of the dockerized service, the system package family (`deb` or `rpm`), and the web server (`nginx`, `apache`, or `traefik`); the tool configures the reverse proxy and generates the certificate automatically.

Internally, it uses the appropriate package manager (`apt` on Debian/Ubuntu, `dnf` on Fedora, `zypper` on openSUSE) to install on the fly everything necessary: the web server, Certbot, and its plugins. It invokes `sudo` when elevated privileges are required, so the user runs the CLI as a normal user.

The project originates from an existing bash script (`nginx-setup.sh`) that solved the problem ad-hoc for Nginx on Ubuntu/Debian. `gen_cerbot` evolves it toward a robust, multi-server, multi-distro, tested, and packagable Python tool solution.

The target audience are infrastructure engineers, DevOps and developers who manage Linux servers and need to configure HTTPS quickly and repeatably for multiple projects or domains, regardless of the server distribution.

---

## 2. Context and Problem

### 2.1 Current Situation

Today, configuring TLS/SSL on a new server involves a manual sequence of commands: updating the system, installing Nginx/Apache, creating virtual host configuration files, enabling the site, installing Certbot (with different methods depending on the distro), requesting the certificate and verifying that everything works. The bash script `nginx-setup.sh` solves part of this problem for Nginx on Ubuntu/Debian, but does not cover Apache or Traefik, does not support Fedora or openSUSE, is not tested or packaged, and does not offer maintenance operations (renewal, listing, deletion).

### 2.2 Problem

The SSL configuration process is repetitive, manual, and error-prone. Every time a new server or project is launched, you have to remember the correct steps, the order of commands, and the configuration details (timeouts, proxy headers, etc.). Errors in this process leave services without HTTPS or with insecure configurations.

### 2.3 Opportunity

Packaging this operational knowledge into a reusable, tested, multi-server Python CLI reduces configuration time from ~20 minutes manual to a single command. Additionally, the tool can be integrated into CI/CD pipelines and infrastructure provisioning scripts.

---

## 3. Target Users

### Persona 1: DevOps / SRE

- **Description:** Operations engineering that manages multiple servers and projects
- **Primary need:** Configure HTTPS on new servers quickly, repeatably, and securely
- **Usage frequency:** Weekly / per provisioning event
- **Technical level:** High

### Persona 2: Backend Developer

- **Description:** Developer who launches their own servers on VPS or EC2 for personal or team projects
- **Primary need:** Not having to remember the sequence of commands to configure Nginx+SSL each time
- **Usage frequency:** Occasional (per new project)
- **Technical level:** Medium-High

### Persona 3: Infrastructure Engineer

- **Description:** Systems administrator managing server fleets for clients
- **Primary need:** Standardized and auditable tool to configure SSL on multiple clients
- **Usage frequency:** Frequent
- **Technical level:** High

---

## 4. Goals and Success Metrics

### 4.1 Project Goals

| Goal | Metric | Target | Timeline |
|---|---|---|---|
| Reduce SSL configuration time | Minutes per configuration | < 3 min (vs ~20 min manual) | v1.0 |
| Multi-server support | Servers supported | Nginx, Apache, Traefik | v1.0 |
| Process reliability | Success rate on first execution | > 95% | v1.0 |
| Code maintainability | Test coverage | > 80% | v1.0 |

### 4.2 User Goals

| User Goal | Indicator |
|---|---|
| Configure HTTPS without manually editing files | The `generate` command completes the flow without intervention |
| Know what certificates you have managed | The `list` command shows status, domain, and expiration date |
| Renew certificates easily | The `renew` command requires no additional parameters |
| Test before applying | The `--dry-run` flag executes without actual effects |

---

## 5. Scope

### 5.1 In Scope

- [x] `generate` subcommand: complete server configuration + SSL for Nginx, Apache, and Traefik
- [x] `renew` subcommand: renewal of existing certificates
- [x] `list` subcommand: listing of managed certificates with status and expiration date
- [x] `remove` subcommand: deletion of configuration and certificate for a domain
- [x] Pre-flight DNS validation (verify that the domain resolves to the server IP)
- [x] Support for `--dry-run` (simulates without applying changes)
- [x] Nginx configuration generation with reverse proxy and secure headers
- [x] Apache configuration generation with VirtualHost and proxy
- [x] Traefik configuration generation (docker-compose + traefik.yml)
- [x] **Interactive mode with menu**: navigable main menu + step-by-step wizard for `generate` with real-time execution output
- [x] Interactive selection of: subdomain, port of dockerized service, package family (`deb`/`rpm`), and web server
- [x] Summary screen and confirmation before executing in interactive mode
- [x] Automatic Certbot installation if not present
- [x] Automatic detection of Linux distribution; in interactive mode the user can also select it manually (`deb`/`rpm`)
- [x] On-the-fly installation of necessary packages (web server, Certbot, plugins) using the detected manager
- [x] Internal invocation of `sudo` for operations requiring elevated privileges
- [x] Automatic renewal configuration via cron/systemd timer
- [x] Support for multiple domains / SAN in the same certificate
- [x] Output with colors and clear progress and error messages
- [x] Logging to file for auditing

### 5.2 Out of Scope

- Support for Windows or macOS as server operating system (Linux only)
- Graphical interface (GUI) or web application — CLI/TUI console only
- Management of private certificates / internal CA (Let's Encrypt / public ACME only)
- Integration with DNS providers for DNS-01 challenge (HTTP-01 only in v1.0)
- Firewall configuration (ufw, iptables) — outside the scope of the CLI
- Web interface or TUI — CLI only
- Support for Windows IIS servers

### 5.3 Future Considerations

- DNS-01 challenge for domains with firewall restrictions
- Support for Caddy as additional web server
- Integration with Ansible / Terraform for declarative provisioning
- Support for wildcard certificates
- Plugin for automatic renewal via GitHub Actions

---

## 6. Functional Requirements

### RF-001: Generate SSL configuration for Nginx

- **Description:** The system must install Nginx (if not installed), create the virtual host configuration with reverse proxy, and obtain the TLS/SSL certificate with Certbot.
- **Actor:** User (CLI)
- **Preconditions:** The server runs a supported Linux distribution (Debian/Ubuntu, Fedora, openSUSE), the domain has DNS configured pointing to the server IP, the user can execute `sudo`.
- **Main flow:**
  1. User runs `gen-cerbot generate --server nginx --domain sub.example.com --port 8000 --project myapp`
  2. The CLI validates input parameters
  3. The CLI detects the Linux distribution and selects the package manager (`apt`/`dnf`/`zypper`)
  4. The CLI verifies that the domain resolves to the server IP (DNS check)
  5. The CLI installs Nginx if not present using `sudo <pkg-manager> install nginx`
  6. The CLI generates the site configuration file in `/etc/nginx/sites-available/`
  7. The CLI activates the site (symlink on Debian/Ubuntu, include on Fedora/openSUSE)
  8. The CLI verifies the configuration with `sudo nginx -t`
  9. `CertbotInstaller.ensure_installed()` installs Certbot per distro: snapd check + `snap install --classic certbot` + symlink on Debian/Ubuntu; `dnf install certbot python3-certbot-nginx` on Fedora; `zypper install certbot python3-certbot-nginx` on openSUSE
  10. The CLI requests the certificate with `sudo certbot --nginx -d domain --non-interactive --agree-tos --email email`
  11. `CertbotManager.verify_service()` runs `sudo systemctl status nginx --no-pager` to confirm the service is running
  12. The CLI displays success message with the resulting HTTPS URL
- **Alternative flow:** If the DNS check fails, the CLI informs the user and offers to continue with `--skip-dns-check` or abort.
- **Postconditions:** The domain responds via HTTPS with a valid certificate. Automatic renewal is configured.
- **Priority:** `MUST`

### RF-002: Generate SSL configuration for Apache

- **Description:** The system must install Apache (if not installed), create the VirtualHost configuration with reverse proxy, and obtain the TLS/SSL certificate with Certbot.
- **Actor:** User (CLI)
- **Preconditions:** The server runs a supported Linux distribution, the domain has DNS configured, the user can execute `sudo`.
- **Main flow:**
  1. User runs `gen-cerbot generate --server apache --domain api.example.com --port 3000 --project myapi`
  2. Parameter validation and DNS check
  3. Distribution detection and package manager selection
  4. Installation of Apache and necessary modules using `sudo <pkg-manager>`:
     - Debian/Ubuntu: `apache2`, `libapache2-mod-proxy-html`
     - Fedora: `httpd`, `mod_ssl`
     - openSUSE: `apache2`, `apache2-mod_proxy`
  5. Module activation (`a2enmod proxy` on Debian/Ubuntu; `httpd_module` on Fedora/openSUSE)
  6. VirtualHost generation with ProxyPass via Jinja2 template
  7. `CertbotInstaller.ensure_installed()` installs Certbot + Apache plugin per distro: snap+symlink+apache-plugin on Debian/Ubuntu; `dnf install certbot python3-certbot-apache` on Fedora; `zypper install certbot python3-certbot-apache` on openSUSE
  8. Certificate request with `sudo certbot --apache -d domain --non-interactive --agree-tos --email email`
  9. `CertbotManager.verify_service()` runs `sudo systemctl status apache2 --no-pager` (Debian/Ubuntu) or `sudo systemctl status httpd --no-pager` (Fedora/openSUSE)
  10. Success message with HTTPS URL
- **Alternative flow:** If the port is in use, the CLI reports the conflict and suggests alternatives.
- **Postconditions:** The domain responds via HTTPS with a valid certificate.
- **Priority:** `MUST`

### RF-003: Generate SSL configuration for Traefik

- **Description:** The system must generate the configuration files for Traefik (docker-compose.yml and traefik.yml) with automatic HTTPS via Let's Encrypt.
- **Actor:** User (CLI)
- **Preconditions:** Docker and Docker Compose are installed, the domain has DNS configured.
- **Main flow:**
  1. User runs `gen-cerbot generate --server traefik --domain app.example.com --email admin@example.com`
  2. Parameter validation and DNS check
  3. Verification that Docker is installed
  4. Generation of `docker-compose.yml` with Traefik service and Docker network
  5. Generation of `traefik.yml` with ACME configuration (Let's Encrypt)
  6. Creation of `acme.json` with correct permissions (600)
  7. Final instructions to bring up with `docker compose up -d`
- **Alternative flow:** If Docker is not installed, the CLI informs and optionally installs Docker.
- **Postconditions:** The configuration files are generated and ready to use.
- **Priority:** `MUST`

### RF-004: List managed certificates

- **Description:** The system must display all certificates it has generated, with their status, expiration date, and associated server.
- **Actor:** User (CLI)
- **Preconditions:** At least one certificate generated by `gen_cerbot` exists.
- **Main flow:**
  1. User runs `gen-cerbot list`
  2. The CLI reads the local registry of managed certificates
  3. For each certificate, queries the real expiration date with Certbot
  4. Displays table with: domain, server, expiration date, status (OK / EXPIRING / EXPIRED)
- **Priority:** `MUST`

### RF-005: Renew certificates

- **Description:** The system must renew all certificates nearing expiration or a specific certificate.
- **Actor:** User (CLI) or cron/systemd timer
- **Main flow:**
  1. User runs `gen-cerbot renew` or `gen-cerbot renew --domain sub.example.com`
  2. The CLI runs `certbot renew` (or with `--cert-name` for specific domain)
  3. Displays renewal result
- **Priority:** `MUST`

### RF-006: Remove domain configuration

- **Description:** The system must revoke the certificate, delete the server configuration, and clean the local registry.
- **Actor:** User (CLI)
- **Main flow:**
  1. User runs `gen-cerbot remove --domain sub.example.com`
  2. CLI displays confirmation with the changes that will be applied
  3. User confirms
  4. CLI revokes and deletes the certificate with Certbot
  5. CLI deletes the server configuration (Nginx/Apache)
  6. CLI updates the local registry
- **Priority:** `SHOULD`

### RF-007: Dry-run mode

- **Description:** Any subcommand must be able to execute with `--dry-run` to show what it would do without applying actual changes.
- **Actor:** User (CLI)
- **Priority:** `SHOULD`

### RF-008: Pre-flight DNS validation

- **Description:** Before requesting a certificate, the CLI must verify that the domain resolves to one of the server's IPs.
- **Priority:** `MUST`

### RF-009: Automatic detection of package manager and use of sudo

- **Description:** The system must detect the Linux distribution at runtime and invoke the correct package manager with `sudo` to install all necessary dependencies without the user having to specify them manually.
- **Actor:** CertbotService (internal)
- **Preconditions:** The user can execute `sudo` on the server.
- **Main flow:**
  1. At the start of any installation operation, `DistroDetector` reads `/etc/os-release`
  2. Identifies the distribution family: Debian, RedHat/Fedora, SUSE
  3. `PackageManager` selects the manager: `apt-get` (Debian/Ubuntu), `dnf` (Fedora/RHEL), `zypper` (openSUSE)
  4. Each installation command runs with `sudo <pkg-manager> install -y <package>`
  5. For Certbot on Debian/Ubuntu: (a) ensure `snapd` is installed via `apt install -y snapd`; (b) `sudo snap install --classic certbot`; (c) `sudo ln -sf /snap/bin/certbot /usr/local/bin/certbot`
  5a. For Certbot on Fedora: `sudo dnf install -y certbot python3-certbot-nginx python3-certbot-apache`
  5b. For Certbot on openSUSE: `sudo zypper install -y certbot python3-certbot-nginx python3-certbot-apache`
  5c. For Traefik: Certbot is not installed; ACME is configured natively in `traefik.yml`
- **Alternative flow:** If the distribution is not recognized, the CLI shows a clear error message indicating the supported distributions and aborts.
- **Postconditions:** All necessary packages are installed regardless of distribution.
- **Priority:** `MUST`

### RF-010: Interactive mode with menu and guided wizard

- **Description:** The system must offer an interactive mode accessible by running `gen-cerbot` without arguments, which presents a navigable main menu, and when generating a certificate, guides the user with a step-by-step wizard collecting all necessary parameters and displaying execution output in real time.
- **Actor:** User (console)
- **Preconditions:** The tool is installed and the user has a terminal with color support (ANSI).
- **Main flow:**
  1. The user runs `gen-cerbot` without arguments
  2. The main menu is displayed with options: Generate certificate, List, Renew, Delete, Exit
  3. The user navigates with arrow keys and selects with Enter
  4. If they choose **Generate certificate**, the wizard requests in sequence:
     - **Subdomain**: free text field with domain format validation
     - **Port of dockerized service**: numeric field (1–65535) with default value 8000
     - **Package family**: selection between `deb` (Debian/Ubuntu) and `rpm` (Fedora/openSUSE)
     - **Web server**: selection between `nginx`, `apache`, `traefik`
     - **Email for Let's Encrypt**: text field with email format validation
     - **Project name**: free text field (to name the config file)
  5. A summary screen is displayed with all captured parameters and a confirmation `Continue? [Yes/No]`
  6. Upon confirmation, the process runs and the output of each step (installation, configuration, Certbot) prints in real time with visual indicators (`[✔]`, `[→]`, `[✗]`)
  7. Upon completion, the resulting HTTPS URL is displayed and the main menu reappears
- **Alternative flow A:** If the user selects `No` at confirmation, returns to main menu without executing anything.
- **Alternative flow B:** If an error occurs in a step, `[✗]` displays with the error message and the option to retry or return to menu.
- **Alternative flow C:** The user can exit with `Ctrl+C` at any time; the tool displays a clean exit message.
- **Postconditions:** The domain has HTTPS configured and the main menu reappears.
- **Priority:** `MUST`

### RF-011: Multi-language support (i18n) in interactive interface

- **Description:** The interactive interface must support multiple languages. The default language is **English**. Before displaying the main menu, the system must present a language selector (or respect the `--lang` flag) so the user can choose the session language. The preference is saved in `~/.config/gen_cerbot/config.toml` and automatically used in subsequent sessions.
- **Actor:** User (console)
- **Preconditions:** The system has at least the locale files `en.json` and `es.json` available.
- **Main flow:**
  1. The user runs `gen-cerbot` without arguments
  2. If no saved preference exists and `--lang` was not passed, the system displays a language selection prompt:
     ```
     Select your language / Selecciona tu idioma:
      ❯  English
         Español
     ```
  3. The user selects a language; the selection persists in `~/.config/gen_cerbot/config.toml`
  4. The main menu is presented completely in the selected language
- **Alternative flow A:** The user passes `--lang en` or `--lang es` — the selector is skipped and the indicated language is used.
- **Alternative flow B:** Subsequent sessions load the language from `config.toml` and skip the selector automatically.
- **Alternative flow C:** If the requested locale file does not exist, `en` is used as fallback without error.
- **Postconditions:** All interactive interface texts (menu, wizard, summary, indicators, errors) are displayed in the chosen language.
- **Priority:** `MUST`

### RF-012: Distribution as installable package (PyPI, .deb, .rpm)

- **Description:** The tool must be available in three distribution formats to facilitate adoption in different environments: Python package on PyPI (`pip install gen-cerbot`), native Debian/Ubuntu package (`.deb`), and native RPM package for Fedora and openSUSE (`.rpm`). Native packages must install the `gen-cerbot` command without exposing Python details to the user.
- **Actor:** System administrator / DevOps
- **pip/PyPI Flow:**
  1. `pip install gen-cerbot` installs the latest version from PyPI
  2. The `gen-cerbot` command becomes available in the active environment PATH
- **.deb Flow (Debian/Ubuntu):**
  1. `sudo apt install ./gen-cerbot_<version>_all.deb` or via repository
  2. The package declares dependencies (`python3 >= 3.11`, `python3-pip`) and postinst installs Python dependencies
  3. `gen-cerbot` becomes available in `/usr/bin/gen-cerbot`
- **.rpm Flow (Fedora/openSUSE):**
  1. `sudo dnf install ./gen-cerbot-<version>-1.noarch.rpm` (Fedora) or `sudo zypper install ./gen-cerbot-*.rpm`
  2. The `.spec` declares `Requires: python3 >= 3.11` and necessary dependencies as sub-packages
  3. `gen-cerbot` becomes available in `/usr/bin/gen-cerbot`
- **Postconditions:** The tool is installed and the `gen-cerbot --version` command works.
- **Priority:** `MUST`

### RF-013: Automated test suite (unit + integration)

- **Description:** The project must include an automated test suite covering business logic through unit tests and critical file generation flows through integration tests. Tests must run without network, without real `sudo`, and without installed web servers, using mocks and static fixtures.
- **Actor:** Developer / CI pipeline
- **Unit test requirements:**
  - Each module in `src/gen_cerbot/` must have a corresponding `tests/unit/test_<module>.py` file.
  - All unit tests must pass with `pytest -m unit` without network access or real `/etc/` access.
  - `SystemRunner` must be mocked in all unit tests — no unit test executes real subprocesses.
  - `DistroDetector` must be tested with at least 4 `/etc/os-release` fixtures: Ubuntu 22.04, Debian 12, Fedora 40, openSUSE Leap 15.5, and an unknown distribution.
  - The three `PackageManager` implementations (`Apt`, `Dnf`, `Zypper`) must be tested independently verifying correct command construction.
  - `ApacheProvider` must be tested with all three `DistroFamily` to verify the Apache package name and used template are correct.
  - `GenerateWizard` must be tested with predefined answers using `questionary.unsafe_ask()` for each field, including validation failure cases (invalid email, port out of range).
  - `LocaleManager.t("key")` must return text in the active language; for missing keys in the secondary language, must return English text without raising exception.
- **Integration test requirements:**
  - Integration tests must use `tmp_path` from pytest — never write to the real filesystem.
  - There must be a test verifying that `NginxProvider.configure()` generates a configuration file with the domain and backend port correctly interpolated.
  - There must be a test verifying that `ApacheProvider.configure()` generates different templates for `DistroFamily.DEBIAN`, `REDHAT`, and `SUSE`.
  - There must be a test verifying that `TraefikProvider.configure()` creates `acme.json` with permissions 600 and generates functional `docker-compose.yml`.
  - There must be a test verifying parsing of `certbot certificates` output against the `tests/fixtures/certbot-outputs/certificates_ok.txt` fixture.
  - There must be an end-to-end test of `CertbotService.generate()` flow with all real components except `SystemRunner` (mocked) and filesystem (`tmp_path`).
- **Postconditions:** `pytest -m "unit or integration"` passes with coverage > 80% in CI environment without network or privileges.
- **Priority:** `MUST`

### RF-014: Certbot installation and execution by distro and web server

- **Description:** The tool must install Certbot using the native method for each Linux distribution family, create the required post-install symlink on Debian/Ubuntu, execute the certificate request with `--non-interactive` mode (no interactive prompts), and verify the web server service is running correctly after the certificate is obtained.
- **Actor:** CertbotInstaller / CertbotManager (internal)
- **Preconditions:** The user can execute `sudo`; internet access is available; port 80 is free.

#### Certbot installation matrix by distro

| Distro family | Step 1 (prerequisite) | Step 2 (install) | Step 3 (post-install) |
|---|---|---|---|
| Debian / Ubuntu | `sudo apt install -y snapd` (if not installed) | `sudo snap install --classic certbot` | `sudo ln -sf /snap/bin/certbot /usr/local/bin/certbot` |
| Fedora (RHEL) | N/A | `sudo dnf install -y certbot python3-certbot-nginx python3-certbot-apache` | N/A |
| openSUSE | N/A | `sudo zypper install -y certbot python3-certbot-nginx python3-certbot-apache` | N/A |

> **Traefik exception:** Traefik does not use Certbot. ACME is handled natively via the `entryPoints.websecure.http.tls.certResolver` section in `traefik.yml`. The `acme.json` file (with permissions 600) stores certificates obtained directly by Traefik from Let's Encrypt.

#### Certificate request matrix by web server

| Web server | Command executed by CertbotManager |
|---|---|
| Nginx | `sudo certbot --nginx -d <domain> --non-interactive --agree-tos --email <email>` |
| Apache | `sudo certbot --apache -d <domain> --non-interactive --agree-tos --email <email>` |
| Traefik | Not applicable — ACME configured in `traefik.yml` |

#### Post-certificate service verification

After a successful certificate request, `CertbotManager` runs a service health check:

| Web server | Distro | Verification command |
|---|---|---|
| Nginx | All | `sudo systemctl status nginx --no-pager` |
| Apache | Debian/Ubuntu | `sudo systemctl status apache2 --no-pager` |
| Apache | Fedora/openSUSE | `sudo systemctl status httpd --no-pager` |
| Traefik | All | `docker compose ps` |

- **Main flow:**
  1. `CertbotInstaller.ensure_installed(distro_family, server_type)` is called by `CertbotService`
  2. If already installed (`certbot --version` succeeds), skip installation
  3. Otherwise execute the installation steps from the matrix above for the detected `DistroFamily`
  4. On Debian/Ubuntu only: verify symlink exists at `/usr/local/bin/certbot`; create it if missing
  5. `CertbotManager.request(domain, email, server_type, staging)` executes the certbot command from the matrix
  6. On failure, `CertbotError` is raised with the raw certbot output and the failed command
  7. On success, `CertbotManager.verify_service(server_type, distro_family)` executes the service status check
- **Alternative flow A:** `--staging` flag is active → append `--staging` to the certbot command (test certificate, no rate limits)
- **Alternative flow B:** `certbot` is already installed → `CertbotInstaller` skips all installation steps (idempotent)
- **Alternative flow C:** `snapd` not installed on Debian/Ubuntu → `CertbotInstaller` installs snapd first via `apt`
- **Postconditions:** Certbot is installed, a valid certificate exists for the domain, and the web service is confirmed running.
- **Priority:** `MUST`

---

## 7. Non-Functional Requirements

### System Compatibility

- **Debian Family:** Ubuntu 20.04 LTS, 22.04 LTS and 24.04 LTS / Debian 11 (Bullseye) and 12 (Bookworm)
- **RedHat Family:** Fedora 38, 39, 40
- **SUSE Family:** openSUSE Leap 15.5+ / openSUSE Tumbleweed
- Python 3.11 or higher

### Performance

- The `generate` command must complete in less than 5 minutes under normal conditions (excluding package download time on first installation)
- The `list` command must respond in less than 10 seconds

### Security

- The CLI must warn when run as root and abort; elevated privileges are obtained internally via `sudo` on a granular basis
- `sudo` is invoked only on commands that require it (package installation, `/etc/` writes, service restart) — the entire process is not elevated
- Traefik `acme.json` files must be generated with 600 permissions
- Generated private keys must never be printed to stdout or in logs
- The CLI must never log passwords or tokens

### Usability

- Error messages must be clear and actionable (indicate what went wrong and how to resolve it)
- The CLI must include detailed `--help` on each subcommand
- Standard output must use colors to distinguish INFO, WARNING, and ERROR

### Quality and Testing

- Test coverage > 80% globally; critical modules (`utils/system.py`, `utils/distro.py`) > 90%
- Code must follow PEP 8 and be formatted with `ruff`
- Type annotations (type hints) on all public functions

### Portability

- The tool must be installable via `pip` as a standard package published on PyPI
- The tool must be installable as a native `.deb` package on Debian/Ubuntu without requiring explicit Python from the user
- The tool must be installable as a native `.rpm` package on Fedora and openSUSE without requiring explicit Python from the user
- Generated configuration files must be template-based (Jinja2) versioned in the repository

---

## 8. Constraints and Dependencies

### Technical Constraints

- Requires internet access to contact Let's Encrypt ACME servers
- Port 80 must be available during the Let's Encrypt HTTP-01 validation process
- The user running the CLI must have `sudo` access (not required to run as root)
- Certbot is installed per distro:
  - Debian/Ubuntu: `snapd` required → `snap install --classic certbot` → symlink `/usr/local/bin/certbot`
  - Fedora: `dnf install -y certbot python3-certbot-nginx python3-certbot-apache`
  - openSUSE: `zypper install -y certbot python3-certbot-nginx python3-certbot-apache`
  - Traefik: no Certbot installation required (ACME native)
- Certbot is always invoked with `--non-interactive --agree-tos --email <email>` — no interactive prompts
- `/etc/os-release` must be available for distribution detection (present on all supported distros)

### Let's Encrypt Constraints

- Rate limits: 50 certificates per registered domain per week
- Certificates have a validity of 90 days
- The ACME challenge server must be able to receive HTTP requests on port 80

### External Dependencies

| Dependency | Type | Purpose | Status |
|---|---|---|---|
| Let's Encrypt / ACME | External service | Certificate issuance | Required |
| Certbot | System tool | ACME client | Automatically installed by gen_cerbot |
| Nginx / Apache | Web server | Server to configure | Automatically installed by gen_cerbot |
| apt / dnf / zypper | System package manager | Dependency installation | Native to distro |
| Docker | Runtime | For Traefik mode | Pre-installed by user |
| snapd | System service | Snap daemon required for Certbot on Debian/Ubuntu; installed via `apt install -y snapd` if missing | Required on Debian/Ubuntu |
| python3-build / twine | Build tool | Wheel construction and PyPI publishing | Development environment only |
| fakeroot / dpkg-dev / debhelper / dh-python | Build tools | `.deb` package construction | Debian build environment only |
| rpm-build / python3-devel | Build tools | `.rpm` package construction | Fedora/SUSE build environment only |

---

## 9. User Stories

### Epic 1: Certificate generation

**US-001:** As a DevOps engineer, I want to run a single command to configure HTTPS on Nginx, so I don't have to remember the manual command sequence.
- Acceptance criteria:
  - [ ] The command `gen-cerbot generate --server nginx --domain X --port Y --project Z` completes without errors
  - [ ] The domain responds via HTTPS with a valid Let's Encrypt certificate
  - [ ] The Nginx configuration includes security headers and correct proxy settings

**US-002:** As a developer, I want Apache support, so I can use the same tool regardless of my project's web server.
- Acceptance criteria:
  - [ ] The command works with `--server apache`
  - [ ] The generated VirtualHost has ProxyPass configured correctly
  - [ ] The certificate is obtained with the certbot-apache plugin

**US-003:** As a DevOps engineer using Docker, I want to generate Traefik configuration with automatic HTTPS, so I don't configure Certbot manually in containers.
- Acceptance criteria:
  - [ ] Functional `docker-compose.yml` and `traefik.yml` are generated
  - [ ] `acme.json` has 600 permissions
  - [ ] Post-generation instructions are clear

### Epic 2: Certificate management

**US-004:** As an administrator, I want to see the status of all my certificates, so I know which are nearing expiration.
- Acceptance criteria:
  - [ ] `gen-cerbot list` shows domain, server, expiration date, and status
  - [ ] Certificates with less than 30 days validity show with visual alert

**US-005:** As a DevOps engineer, I want to renew certificates with a single command, so I maintain HTTPS service without interruptions.
- Acceptance criteria:
  - [ ] `gen-cerbot renew` works without additional parameters
  - [ ] An individual domain can be specified with `--domain`
  - [ ] The command is idempotent (running it when no renewal is pending produces no error)

### Epic 3: Security and reliability

**US-006:** As a security engineer, I want the CLI to validate DNS before requesting the certificate, so I avoid Certbot errors from misconfigured DNS.
- Acceptance criteria:
  - [ ] If domain DNS does not resolve to the server IP, the CLI shows clear warning
  - [ ] Validation can be skipped with `--skip-dns-check`
  - [ ] Error message indicates the expected IP and what was found

### Epic 4: Interactive mode

**US-007:** As an administrator using the tool for the first time, I want an interactive menu, so I don't have to remember command syntax.
- Acceptance criteria:
  - [ ] Running `gen-cerbot` without arguments shows the main menu
  - [ ] Navigation works with arrow keys and Enter
  - [ ] The 4 main options are available: Generate, List, Renew, Delete

**US-008:** As an infrastructure engineer, I want a guided wizard to generate certificates, so I ensure I don't forget any parameter.
- Acceptance criteria:
  - [ ] The wizard requests: subdomain, service port, package family (`deb`/`rpm`), and web server
  - [ ] Fields have inline validation (domain format, port range)
  - [ ] A summary screen shows all values before execution
  - [ ] The `Continue?` confirmation prevents accidental execution

**US-009:** As a user, I want to see execution output in real time during certificate generation, so I know which step I'm on and detect errors quickly.
- Acceptance criteria:
  - [ ] Each step shows status: `[→]` in progress, `[✔]` complete, `[✗]` error
  - [ ] The `sudo` commands executed display on screen
  - [ ] If an error occurs, the system message shows and retry or exit options are offered
  - [ ] On successful completion, the HTTPS URL displays with success indicator

**US-010:** As a DevOps engineer automating with scripts, I want all interactive commands to also work as CLI flags, so I can use the tool in CI/CD without manual intervention.
- Acceptance criteria:
  - [ ] `gen-cerbot generate --server nginx --domain X --port Y --pkg-family deb --project Z` works without interactive mode
  - [ ] The `--no-interactive` flag disables any prompt and fails with error if required parameters are missing

**US-011:** As an international administrator, I want to select the interface language before starting, so I can operate the tool in my native language.
- Acceptance criteria:
  - [ ] On first run (without saved preference) a language selector displays before the menu
  - [ ] The selected language persists in `~/.config/gen_cerbot/config.toml` and is not asked again
  - [ ] The `--lang en|es` flag skips the selector and forces that language in the session
  - [ ] All interactive interface texts (menu, wizard, confirmations, errors) display in the chosen language
  - [ ] If no preference exists and `--lang` is not passed, the default language is English
  - [ ] `en` (English) and `es` (Spanish) are supported in v1.0

### Epic 5: Distribution and packaging

**US-012:** As a systems administrator on Debian/Ubuntu, I want to install `gen_cerbot` with `apt install` or `dpkg -i`, so I don't need Python or pip configured explicitly.
- Acceptance criteria:
  - [ ] A `.deb` file is downloadable from GitHub Releases for each version
  - [ ] `sudo dpkg -i gen-cerbot_<version>_all.deb` correctly installs the tool
  - [ ] `gen-cerbot --version` works after installation without additional configuration
  - [ ] The package passes `lintian` without critical errors (informational only allowed)
  - [ ] Uninstalling with `sudo apt remove gen-cerbot` cleans up correctly

**US-013:** As a systems administrator on Fedora or openSUSE, I want to install `gen_cerbot` with `dnf` or `zypper`, so I integrate it into my native package management workflow.
- Acceptance criteria:
  - [ ] A `.rpm` file is downloadable from GitHub Releases for each version
  - [ ] `sudo dnf install ./gen-cerbot-<version>-1.noarch.rpm` works on Fedora 40
  - [ ] `sudo zypper install ./gen-cerbot-<version>-1.noarch.rpm` works on openSUSE Leap 15.5
  - [ ] `gen-cerbot --version` works after installation
  - [ ] The package passes `rpmlint` without critical errors

**US-014:** As a Python developer, I want to install `gen_cerbot` with `pip install gen-cerbot` from PyPI, so I can integrate it in my virtual environments or provisioning tools.
- Acceptance criteria:
  - [ ] `pip install gen-cerbot` installs the latest stable version from PyPI
  - [ ] `pip install gen-cerbot==<version>` allows installing specific versions
  - [ ] The package includes a wheel (`.whl`) for fast installation without compilation
  - [ ] `gen-cerbot --version` displays the correct version after installation

---

## 10. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Let's Encrypt rate limit exceeded in development | High | Medium | Use `--staging` for tests with test certificates |
| Changes in Certbot / snap API | Low | High | Certbot provider abstraction with integration tests |
| Port 80 blocked by another process | Medium | High | Pre-flight port validation and clear error message |
| DNS propagation lag | Medium | Medium | Informational message + `--skip-dns-check` flag |
| Differences between Linux distros | Medium | Medium | Tests in distro matrix (Ubuntu 20/22/24, Debian 11/12) |
| Python dependencies unavailable as .deb/.rpm packages | Medium | Medium | Use `dh_python3` + `pip install --prefix` in postinst; list dependencies explicitly in .spec |
| Lintian / rpmlint report errors in packages | Medium | Low | Follow Debian Policy and Fedora Packaging Guidelines from the start |
| pip install breakage in environments with system-managed Python (PEP 668) | Medium | Medium | Document `pipx install gen-cerbot` as recommended installation method |

---

## 11. Estimated Timeline

| Phase | Estimated Duration | Deliverable |
|---|---|---|
| Phase 1: Foundation | 1 week | Project structure, CLI skeleton, tests |
| Phase 2: Nginx Provider | 1 week | Complete and tested Nginx provider |
| Phase 3: Apache + Traefik Providers ✅ | 1 week | Apache and Traefik providers (**Done**) |
| Phase 4: Certbot Manager | 1 week | Complete Certbot integration |
| Phase 5: Operations (list/renew/remove) | 1 week | All subcommands |
| Phase 6: Testing, Hardening & Packaging | 2 weeks | Coverage > 80%, docs; PyPI wheel + .deb + .rpm packages |
| Phase 7: Interactive Mode | 1 week | Main menu + generate wizard + real-time output |
| Phase 8: i18n Support | 1 week | Language selector, LocaleManager, en/es locales |

---

## Change History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-03-31 | Ernesto Crespo | Initial version: base PRD with RF-001..RF-008, Epics 1-3, 6 user stories, 6-phase timeline |
| 1.1 | 2026-03-31 | Ernesto Crespo | Multi-distro: RF-009 automatic package manager detection and internal sudo; constraints and dependencies update (dnf, zypper) |
| 1.2 | 2026-03-31 | Ernesto Crespo | Interactive mode: RF-010 interactive mode with menu and guided wizard; Epic 4 with US-007..US-010; timeline extended to Phase 7 |
| 1.3 | 2026-03-31 | Ernesto Crespo | i18n support: RF-011 language selector before menu, --lang flag, persisted preference; US-011; Phase 8 added to timeline |
| 1.4 | 2026-03-31 | Ernesto Crespo | Native packaging: RF-012 distribution PyPI/.deb/.rpm; Epic 5 with US-012..US-014; build dependencies in table; extended portability RNF; Phase 6 extended to 2 weeks; 3 new packaging risks |
| 1.5 | 2026-03-31 | Ernesto Crespo | Testing specifications: RF-013 unit and integration test suite with per-module requirements (DistroDetector fixtures, PackageManager 3 impls, ApacheProvider 3 DistroFamily, GenerateWizard unsafe_ask, LocaleManager fallback, 6 integration scenarios, complete CertbotService flow); updated Quality RNF with per-module coverage minimums |
| 1.6 | 2026-03-31 | Ernesto Crespo | RF-014: Certbot installation and execution by distro/server; snapd pre-check + symlink (Debian/Ubuntu); dnf/zypper on Fedora/openSUSE; --non-interactive --agree-tos execution; post-cert systemctl status verification; Traefik ACME-native exception documented; RF-001/RF-002/RF-009 enhanced with detailed certbot steps |

## Approvals

| Role | Name | Date | Status |
|---|---|---|---|
| Tech Lead | Ernesto Crespo | | ☐ Pending |
