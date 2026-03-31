# gen_cerbot

> Interactive Python CLI for generating and managing TLS/SSL certificates for web servers (Nginx, Apache, Traefik) using Let's Encrypt / Certbot. Supports guided menu mode and direct command mode.

---

## What is gen_cerbot?

`gen_cerbot` is a command-line tool that automates the complete TLS/SSL configuration process for the most widely used web servers. Instead of running manual commands and editing configuration files by hand, the user declares their parameters in the CLI and `gen_cerbot` takes care of the rest: dependency installation, server configuration, certificate request, and automatic renewal.

## Key Features

- **Interactive mode (menu)**: Guides the user step by step with selection menus and input fields; displays execution output in real time
- **Multi-language (i18n)**: Interactive interface available in English and Spanish; language selector on first use, preference saved automatically; `--lang` flag to force the language
- **Direct command mode**: All subcommands also available as CLI flags for use in scripts and CI/CD
- **Multi-server**: Support for Nginx, Apache, and Traefik with reverse proxy configuration and certificates
- **Multi-distro**: Manual selection or automatic detection of the package family (`deb` for Debian/Ubuntu, `rpm` for Fedora/openSUSE)
- **Internal sudo**: Invokes `sudo` transparently when elevated privileges are needed; no need to run the CLI as root
- **Let's Encrypt integration**: Certificate request and renewal via Certbot (ACME protocol)
- **Automatic reverse proxy**: Generates the complete reverse proxy configuration in Nginx, Apache, or Traefik
- **DNS validation**: Pre-flight check that the domain points correctly before requesting the certificate
- **Automatic renewal**: Cron/systemd timer configuration for automatic renewal
- **Dry-run mode**: Configuration testing without applying real changes
- **Idempotent**: Re-running the command on an already-configured system does not break anything

## Installation

`gen_cerbot` is available in three formats: Python package (PyPI), native Debian/Ubuntu package (`.deb`), and native Fedora/openSUSE package (`.rpm`).

### Option 1 — pip / pipx (all distributions)

```bash
# Recommended: pipx installs in an isolated environment and exposes gen-cerbot in the PATH
pipx install gen-cerbot

# Alternative with pip
pip install gen-cerbot
```

### Option 2 — Native .deb package (Debian / Ubuntu)

Download the `.deb` from [GitHub Releases](https://github.com/user/gen_cerbot/releases) and install:

```bash
sudo dpkg -i gen-cerbot_<version>_all.deb

# If there are missing dependencies, resolve them with:
sudo apt-get install -f
```

After installation, `gen-cerbot` is available at `/usr/bin/gen-cerbot`.

### Option 3 — Native .rpm package (Fedora / openSUSE)

Download the `.rpm` from [GitHub Releases](https://github.com/user/gen_cerbot/releases) and install:

```bash
# Fedora
sudo dnf install ./gen-cerbot-<version>-1.noarch.rpm

# openSUSE
sudo zypper install ./gen-cerbot-<version>-1.noarch.rpm
```

After installation, `gen-cerbot` is available at `/usr/bin/gen-cerbot`.

### From the repository (development)

```bash
git clone https://github.com/user/gen_cerbot.git
cd gen_cerbot
pip install -e .
```

## Language Selector

On the **first run**, before showing the main menu, `gen_cerbot` displays a language selector:

```
  Select your language / Selecciona tu idioma:
   ❯  English
      Español
```

The selection is saved in `~/.config/gen_cerbot/config.toml`. Subsequent runs open the menu directly in the saved language, without asking again.

To force a specific language at any time (without changing the saved preference):

```bash
gen-cerbot --lang en   # English
gen-cerbot --lang es   # Spanish
```

---

## Interactive Mode (recommended)

Running without arguments launches the language selector (if applicable) and then the guided menu:

```bash
gen-cerbot
```

With a saved preference or with `--lang`:

```
╔══════════════════════════════════════════════════╗
║         gen_cerbot v1.0.0  —  TLS/SSL CLI        ║
╚══════════════════════════════════════════════════╝

 What would you like to do?
  ❯  1. Generate new SSL certificate
     2. List managed certificates
     3. Renew certificates
     4. Remove certificate for a domain
     5. Exit
```

Or in Spanish if that language was selected:

```
╔══════════════════════════════════════════════════╗
║         gen_cerbot v1.0.0  —  TLS/SSL CLI        ║
╚══════════════════════════════════════════════════╝

 ¿Qué deseas hacer?
  ❯  1. Generar nuevo certificado SSL
     2. Listar certificados gestionados
     3. Renovar certificados
     4. Eliminar certificado de un dominio
     5. Salir
```

When selecting **Generate new SSL certificate**, the wizard guides the user:

```
  Subdomain or full domain: api.mycompany.com
  Dockerized service port: 8000
  System package family:
    ❯  deb  — Debian / Ubuntu  (apt)
       rpm  — Fedora / openSUSE (dnf / zypper)
  Web server:
    ❯  nginx
       apache
       traefik
  Let's Encrypt email: admin@mycompany.com
  Project name: myapi

  ──────────────────────────────────────────────────
  Summary:
    Domain  : api.mycompany.com → localhost:8000
    Server  : nginx  |  Distro: deb (apt)
    Email   : admin@mycompany.com
  ──────────────────────────────────────────────────
  Continue?  ❯ Yes    No
```

The execution output is then displayed in real time:

```
  [✔] Distro detected: Ubuntu 22.04 → apt
  [✔] DNS OK: api.mycompany.com → 203.0.113.5
  [→] Installing nginx...
      sudo apt-get install -y nginx
  [✔] nginx installed
  [→] Generating configuration...
      sudo tee /etc/nginx/sites-available/myapi
  [✔] Configuration created
  [→] Verifying syntax (nginx -t)...
  [✔] Configuration valid
  [→] Installing Certbot via snap...
  [✔] Certbot ready
  [→] Requesting Let's Encrypt certificate...
      sudo certbot --nginx -d api.mycompany.com
  [✔] Certificate obtained. Expires: 2026-06-29

  ══════════════════════════════════════════════════
  ✅  https://api.mycompany.com  is ready with SSL
  ══════════════════════════════════════════════════
```

## Direct Command Mode

For use in scripts, CI/CD, or automation:

```bash
# Configure Nginx with SSL (in English)
gen-cerbot --lang en generate --server nginx --domain sub.example.com --port 8000 --project myapp

# Configure Apache with SSL (in Spanish)
gen-cerbot --lang es generate --server apache --domain api.example.com --port 3000 --project myapi

# Configure Traefik (no prompts — CI/CD mode)
gen-cerbot generate --server traefik --domain app.example.com --email admin@example.com --no-interactive

# Renew all certificates
gen-cerbot renew

# List managed certificates
gen-cerbot list

# Remove configuration for a domain
gen-cerbot remove --domain sub.example.com
```

## System Requirements

- Python 3.11+ (not required if installing via `.deb` or `.rpm` — the package manages it)
- Linux — supported distributions:
  - **Debian/Ubuntu** (20.04, 22.04, 24.04 / Debian 11, 12) — uses `apt`
  - **Fedora** (38+) — uses `dnf`
  - **openSUSE Leap / Tumbleweed** — uses `zypper`
- `snapd` installed and running (Debian/Ubuntu only — required for Certbot installation)
- Docker (for Traefik mode)
- The domain must have DNS resolving to the server's IP **before** requesting the certificate
- The user must be able to run `sudo` — gen_cerbot invokes it internally when elevated privileges are needed; no need to run the CLI as root

## How Certbot is Installed

`gen_cerbot` automatically installs Certbot using the native method for each Linux distribution. No manual steps required.

### Debian / Ubuntu — via snap

```bash
# 1. Ensure snapd is installed
sudo apt install -y snapd

# 2. Install Certbot via snap (classic confinement)
sudo snap install --classic certbot

# 3. Create symlink so certbot is available in PATH
sudo ln -sf /snap/bin/certbot /usr/local/bin/certbot
```

### Fedora — via dnf

```bash
sudo dnf install -y certbot python3-certbot-nginx python3-certbot-apache
```

### openSUSE — via zypper

```bash
sudo zypper install -y certbot python3-certbot-nginx python3-certbot-apache
```

### Certificate request by web server

Once Certbot is installed, the certificate is requested with `--non-interactive` (no prompts, suitable for CI/CD):

| Web server | Command executed internally |
|---|---|
| Nginx | `sudo certbot --nginx -d <domain> --non-interactive --agree-tos --email <email>` |
| Apache | `sudo certbot --apache -d <domain> --non-interactive --agree-tos --email <email>` |
| Traefik | Not applicable — Traefik uses ACME natively via `traefik.yml` |

After obtaining the certificate, `gen_cerbot` verifies the service is running:

| Web server | Verification command |
|---|---|
| Nginx | `sudo systemctl status nginx --no-pager` |
| Apache (Debian/Ubuntu) | `sudo systemctl status apache2 --no-pager` |
| Apache (Fedora/openSUSE) | `sudo systemctl status httpd --no-pager` |
| Traefik | `docker compose ps` |

---

## Building Packages

This section describes how to compile the three distribution formats from source code.

### Common prerequisites

```bash
git clone https://github.com/user/gen_cerbot.git
cd gen_cerbot
```

### Wheel for PyPI

Required tools: `python-build`, `twine`

```bash
pip install build twine

# Generate wheel (.whl) and source distribution (.tar.gz)
python -m build

# Artifacts are placed in dist/
ls dist/
# gen_cerbot-1.0.0-py3-none-any.whl
# gen_cerbot-1.0.0.tar.gz

# Verify the package before publishing
twine check dist/*

# Publish to TestPyPI (test)
twine upload --repository testpypi dist/*

# Publish to PyPI (production)
twine upload dist/*
```

### Debian/Ubuntu Package (.deb)

Requires a **Debian 12 (Bookworm)** or **Ubuntu 22.04+** VM or container.

```bash
# Install packaging tools
sudo apt-get install -y fakeroot dpkg-dev debhelper dh-python python3-all

# Build the package (unsigned, for manual distribution)
dpkg-buildpackage -us -uc -b

# The .deb is placed in the parent directory
ls ../
# gen-cerbot_1.0.0-1_all.deb

# Validate the package
lintian --no-tag-display-limit ../gen-cerbot_1.0.0-1_all.deb

# Install and test
sudo dpkg -i ../gen-cerbot_1.0.0-1_all.deb
gen-cerbot --version
```

The packaging files are located in `packaging/debian/`:

```
packaging/debian/
├── changelog   # Version history (Debian format)
├── compat      # debhelper compatibility level (13)
├── control     # Metadata: name, arch, dependencies, description
├── copyright   # License in DEP-5 format
├── install     # List of files to install
└── rules       # Build script with dh helper
```

### RPM Package for Fedora/openSUSE (.rpm)

Requires a **Fedora 40+** VM or container.

```bash
# Install packaging tools
sudo dnf install -y rpm-build python3-devel python3-pip rpmdevtools rpmlint

# Set up the build tree
rpmdev-setuptree
# Creates ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Create the source tarball
python -m build --sdist
cp dist/gen_cerbot-1.0.0.tar.gz ~/rpmbuild/SOURCES/

# Copy the spec file
cp packaging/rpm/gen-cerbot.spec ~/rpmbuild/SPECS/

# Build the binary .rpm
rpmbuild -bb ~/rpmbuild/SPECS/gen-cerbot.spec

# The .rpm is placed in ~/rpmbuild/RPMS/noarch/
ls ~/rpmbuild/RPMS/noarch/
# gen-cerbot-1.0.0-1.noarch.rpm

# Validate the package
rpmlint ~/rpmbuild/RPMS/noarch/gen-cerbot-1.0.0-1.noarch.rpm

# Install and test (Fedora)
sudo dnf install ~/rpmbuild/RPMS/noarch/gen-cerbot-1.0.0-1.noarch.rpm
gen-cerbot --version

# Install and test (openSUSE)
sudo zypper install ~/rpmbuild/RPMS/noarch/gen-cerbot-1.0.0-1.noarch.rpm
gen-cerbot --version
```

The spec file is located at `packaging/rpm/gen-cerbot.spec`.

### Automated Release (GitHub Actions)

When pushing a `v*` tag (e.g. `git tag v1.0.0 && git push --tags`), the `.github/workflows/release.yml` workflow automatically:

1. Builds the wheel + source distribution → uploads to PyPI
2. Builds the `.deb` on Ubuntu runner → uploaded to GitHub Releases
3. Builds the `.rpm` on Fedora runner → uploaded to GitHub Releases

---

## Project Structure

```
gen_cerbot/
├── README.md               ← This file
├── CLAUDE.md               ← Instructions for the development agent
├── pyproject.toml
├── docs/                   ← SDD project documentation
│   ├── PRD.md              ← Product Requirements Document (executive summary)
│   ├── SPEC.md             ← Detailed technical specification (RF, NFR, user stories)
│   ├── ARCHITECTURE.md     ← Technical design, components, and architecture decisions
│   └── TASKS.md            ← Implementation plan by phases and test catalog
├── src/
│   └── gen_cerbot/
│       ├── __init__.py
│       ├── cli.py              ← CLI entry point (Typer)
│       ├── core/
│       │   ├── config.py       ← Global configuration
│       │   └── exceptions.py   ← Domain exceptions
│       ├── domain/
│       │   ├── models.py       ← Data models
│       │   └── services.py     ← Main business logic
│       ├── providers/
│       │   ├── base.py         ← Abstract server interface
│       │   ├── nginx.py        ← Nginx implementation
│       │   ├── apache.py       ← Apache implementation
│       │   └── traefik.py      ← Traefik implementation
│       ├── certbot/
│       │   ├── installer.py    ← Certbot installation
│       │   └── manager.py      ← Certificate lifecycle management
│       ├── interactive/
│       │   ├── menu.py             ← Main menu and navigation
│       │   ├── wizard.py           ← Step-by-step wizard (generate)
│       │   └── output.py           ← Real-time output with rich
│       ├── i18n/
│       │   ├── locale_manager.py   ← LocaleManager: t("key") with fallback to en
│       │   ├── selector.py         ← Language selector + config.toml persistence
│       │   └── locales/
│       │       ├── en.json         ← English strings (default)
│       │       └── es.json         ← Spanish strings
│       └── utils/
│           ├── dns.py              ← DNS validation
│           ├── system.py           ← System commands (internal sudo)
│           ├── distro.py           ← Linux distribution detection
│           ├── package_manager.py  ← apt / dnf / zypper abstraction
│           └── templates.py        ← Template rendering
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│       └── os-release/     ← /etc/os-release fixtures per distro
├── packaging/
│   ├── debian/             ← Files for building the .deb package
│   │   ├── changelog       ← Version history (Debian format)
│   │   ├── compat          ← debhelper level (13)
│   │   ├── control         ← Package metadata and dependencies
│   │   ├── copyright       ← License in DEP-5 format
│   │   ├── install         ← Files to install on the system
│   │   └── rules           ← Build script with dh helper
│   └── rpm/
│       └── gen-cerbot.spec ← Spec file for rpmbuild
├── .github/
│   └── workflows/
│       ├── ci.yml          ← CI: tests on Ubuntu/Fedora on each PR
│       └── release.yml     ← Release: build wheel+.deb+.rpm and upload
├── nginx-setup.sh          ← Original bash script (reference)
└── docs/                   ← (see tree above)
```

## SDD Documentation

This project follows the **Spec-Driven Design** methodology. The specification documents live in the `docs/` folder:

| Document | Description |
|---|---|
| [docs/PRD.md](./docs/PRD.md) | Product Requirements Document (executive summary) |
| [docs/SPEC.md](./docs/SPEC.md) | Detailed technical specification (RF, NFR, user stories) |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | Technical design, components, and architecture decisions |
| [docs/TASKS.md](./docs/TASKS.md) | Implementation plan by phases and test catalog |

## License

See [LICENSE](./LICENSE).
