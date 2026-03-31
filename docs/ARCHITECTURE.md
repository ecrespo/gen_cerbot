# gen_cerbot — Technical Design Document

## Metadata

| Field | Value |
|---|---|
| **Author** | Ernesto Crespo |
| **Status** | `DRAFT` |
| **Version** | 1.6 |
| **Date** | 2026-03-31 |
| **Related SPEC** | [SPEC.md](./SPEC.md) |
| **Reviewers** | To be defined |

---

## 1. Context

`gen_cerbot` is a CLI tool that automates TLS/SSL configuration for multiple web servers. Technically, the problem decomposes into two independent responsibilities: (a) configuring the web server (Nginx, Apache, Traefik) with reverse proxy and the correct directives, and (b) managing the lifecycle of Let's Encrypt certificates through Certbot.

The original bash script (`nginx-setup.sh`) combines both responsibilities into a single sequential flow, making it fragile, difficult to test, and not extensible to other servers. The proposed architecture separates these responsibilities into independent modules under a Provider pattern that allows adding new servers without modifying core code.

The tool runs on the server's operating system (Ubuntu/Debian, Fedora, openSUSE), detects the distribution at runtime, and invokes the appropriate package manager (`apt-get`, `dnf`, `zypper`) to install dependencies on the fly. All commands that require elevated privileges are executed by internally prepending `sudo` — the user runs the CLI as a normal user and the tool escalates privileges granularly only where necessary. The tool also reads and writes server configuration files and communicates with Let's Encrypt ACME services through Certbot.

---

## 2. Technical Goals

- **Correctness:** Generated configuration files must be valid and production-safe; the process must be idempotent
- **Extensibility:** Adding support for a new web server must require only creating a new Provider without modifying core code
- **Testability:** Code must be testable with filesystem and system command mocks
- **Maintainability:** Test coverage > 80%, type hints on all public functions, code formatted with ruff
- **Usability:** Interactive mode with guided menu as default; command mode as alternative for automation; real-time output with visual indicators

---

## 3. Proposed Architecture

### 3.1 High-Level Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                      Entry point                                 │
│              gen-cerbot  (no args → interactive mode)             │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                 LanguageSelector / LocaleManager (i18n)          │
│  --lang flag → config.toml → selector questionary → fallback en  │
└──────────────┬───────────────────────────┬───────────────────────┘
               │                           │
               ▼                           ▼
┌──────────────────────────┐   ┌───────────────────────────────────┐
│   Interactive Mode        │   │   Command Mode (Typer)            │
│   InteractiveMenu         │   │   generate | list | renew | remove│
│   GenerateWizard          │   └──────────────┬────────────────────┘
│   LiveOutputRenderer      │                  │
└──────────────┬────────────┘                  │
               └───────────────┬───────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  CertbotService (domain)                    │
│   DNS check → DistroDetect → Server config → Certbot        │
└──────┬───────────────────────┬──────────────────────────────┘
       │                       │
       ▼                       ▼
┌──────────────────┐   ┌───────────────────────────────────────┐
│  ServerProvider  │   │         CertbotManager                │
│  (Abstract Base) │   │   install() / request() / renew()     │
│                  │   │   revoke() / list()                   │
│ NginxProvider    │   └───────────────────────────────────────┘
│ ApacheProvider   │
│ TraefikProvider  │   ┌───────────────────────────────────────┐
└────────┬─────────┘   │           DNSValidator                │
         │             │   check_domain_resolves_to_ip()        │
         ▼             └───────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────┐
│               PackageManager (abstraction)                   │
│   install(pkg) / update() / is_installed(pkg)                │
│                                                              │
│  AptPackageManager  DnfPackageManager  ZypperPackageManager  │
│  (Debian/Ubuntu)        (Fedora)          (openSUSE)         │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                  SystemRunner                                │
│   run(cmd, sudo=True/False) → subprocess with internal sudo  │
└──────────────────────────────────────────────────────────────┘
                         ▲
                         │
┌──────────────────────────────────────────────────────────────┐
│                  DistroDetector                              │
│   detect() → reads /etc/os-release → DistroFamily enum       │
│   (DEBIAN | REDHAT | SUSE | UNKNOWN)                        │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Components

| Component | Python Module | Responsibility |
|---|---|---|
| Entry point | `cli.py` | No args → launches InteractiveMenu; with args → Typer |
| InteractiveMenu | `interactive/menu.py` | Main navigable menu (questionary); routing to wizard or subcommands |
| GenerateWizard | `interactive/wizard.py` | Step-by-step assistant: domain → port → pkg-family → server → email → confirmation |
| LiveOutputRenderer | `interactive/output.py` | Prints execution output in real-time with `[✔]`/`[→]`/`[✗]` via rich |
| LocaleManager | `i18n/locale_manager.py` | Loads active language JSON file and resolves text keys; fallback to `en` |
| LanguageSelector | `i18n/selector.py` | Shows language `questionary` selector if no saved preference; persists in config.toml |
| CLI (Typer) | `cli.py` | Direct subcommands: generate, list, renew, remove; flags `--no-interactive`, `--lang` |
| CertbotService | `domain/services.py` | Orchestration of complete generate/renew/remove flow |
| ServerProvider (ABC) | `providers/base.py` | Abstract interface: `install()`, `configure()`, `verify()`, `remove()` |
| NginxProvider | `providers/nginx.py` | Multi-distro Nginx configuration using PackageManager |
| ApacheProvider | `providers/apache.py` | Multi-distro Apache configuration using PackageManager |
| TraefikProvider | `providers/traefik.py` | docker-compose.yml + traefik.yml generation |
| CertbotManager | `certbot/manager.py` | Wraps certbot CLI: install, certonly, renew, revoke, certificates |
| CertbotInstaller | `certbot/installer.py` | Installs Certbot per distro: (1) Debian/Ubuntu → snapd check + `snap install --classic certbot` + symlink `/usr/local/bin/certbot`; (2) Fedora → `dnf install -y certbot python3-certbot-nginx python3-certbot-apache`; (3) openSUSE → `zypper install -y certbot python3-certbot-nginx python3-certbot-apache`; (4) Traefik → no Certbot |
| DistroDetector | `utils/distro.py` | Reads `/etc/os-release` and returns `DistroFamily` (DEBIAN, REDHAT, SUSE) |
| PackageManager (ABC) | `utils/package_manager.py` | Abstract interface: `install()`, `update()`, `is_installed()` |
| AptPackageManager | `utils/package_manager.py` | `apt-get` implementation for Debian/Ubuntu |
| DnfPackageManager | `utils/package_manager.py` | `dnf` implementation for Fedora/RHEL |
| ZypperPackageManager | `utils/package_manager.py` | `zypper` implementation for openSUSE |
| DNSValidator | `utils/dns.py` | Resolves domain and compares against server's local IPs |
| CertRegistry | `utils/registry.py` | Reads and writes local JSON registry of managed certificates |
| SystemRunner | `utils/system.py` | subprocess abstraction with `sudo=True/False` support per command |
| TemplateRenderer | `utils/templates.py` | Renders Jinja2 templates for configuration files |
| Config | `core/config.py` | Global configuration: paths, defaults, environment variables |
| Exceptions | `core/exceptions.py` | Domain exception hierarchy |

### 3.3 Project File Structure

```
src/gen_cerbot/
├── __init__.py
├── cli.py                      # Entry point: no args → InteractiveMenu; with args → Typer subcommands
├── core/
│   ├── config.py               # Paths, defaults, env vars (pydantic-settings)
│   └── exceptions.py           # DomainError, DNSError, CertbotError, ServerConfigError, UnsupportedDistroError
├── domain/
│   ├── models.py               # CertificateConfig, ServerType (Enum), CertificateStatus, DistroFamily
│   └── services.py             # CertbotService: main orchestration
├── providers/
│   ├── base.py                 # ServerProvider (ABC) — receives PackageManager in constructor
│   ├── nginx.py                # NginxProvider (multi-distro)
│   ├── apache.py               # ApacheProvider (multi-distro)
│   ├── traefik.py              # TraefikProvider
│   └── factory.py              # ProviderFactory.get(server_type, pkg_manager)
├── interactive/
│   ├── menu.py                 # InteractiveMenu: main menu with questionary
│   ├── wizard.py               # GenerateWizard: collects subdomain, port, pkg-family, server
│   └── output.py               # LiveOutputRenderer: real-time printing with rich
├── i18n/
│   ├── locale_manager.py       # LocaleManager: loads active locale JSON; t("key") → text
│   ├── selector.py             # LanguageSelector: questionary prompt + config.toml persistence
│   └── locales/
│       ├── en.json             # All interface strings in English (default language)
│       └── es.json             # Spanish translation
├── certbot/
│   ├── installer.py            # Detects/installs Certbot: snap (Debian), dnf (Fedora), zypper (SUSE)
│   └── manager.py              # Wraps certbot CLI with internal sudo
├── utils/
│   ├── distro.py               # DistroDetector: reads /etc/os-release → DistroFamily
│   ├── package_manager.py      # PackageManager (ABC) + Apt/Dnf/ZypperPackageManager
│   ├── dns.py                  # DNS resolution and IP comparison
│   ├── system.py               # SystemRunner: subprocess with sudo=True/False parameter
│   ├── registry.py             # JSON registry of managed certs
│   └── templates.py            # Jinja2 renderer
└── templates/
    ├── nginx/
    │   └── site.conf.j2        # Nginx VirtualHost template (valid for all distros)
    ├── apache/
    │   ├── vhost-debian.conf.j2    # Apache template for Debian/Ubuntu
    │   ├── vhost-redhat.conf.j2    # Apache template for Fedora/RHEL
    │   └── vhost-suse.conf.j2      # Apache template for openSUSE
    └── traefik/
        ├── docker-compose.yml.j2
        └── traefik.yml.j2
```

### 3.4 Entry Flow: Interactive Mode vs. Command Mode

```
gen-cerbot  (no args)
  └──▶ LanguageSelector.resolve()
         ├── If --lang <code> was passed → LocaleManager.set(code)
         ├── If config.toml has preference → LocaleManager.set(saved_lang)
         └── If none → shows questionary selector → saves to config.toml
                  Select your language / Selecciona tu idioma:
                   ❯  English
                      Español
  └──▶ InteractiveMenu.run()   ← all text via LocaleManager.t("key")
         ├── Option "Generate certificate" → GenerateWizard.run()
         │     1. Asks for subdomain (domain regex validation)
         │     2. Asks for dockerized port (default 8000, range 1-65535)
         │     3. Package family selection: deb | rpm
         │     4. Server selection: nginx | apache | traefik
         │     5. Asks for Let's Encrypt email
         │     6. Asks for project name
         │     7. Shows summary + confirmation (t("wizard.confirm"))
         │     8. If confirms → CertbotService.generate(config)
         │                       with LiveOutputRenderer.attach()
         ├── Option "List certificates" → CertbotService.list()
         ├── Option "Renew certificates" → CertbotService.renew()
         ├── Option "Remove certificate" → asks for domain → CertbotService.remove()
         └── Option "Exit" → sys.exit(0)

gen-cerbot --lang es generate --server nginx --domain X --port Y --pkg-family deb ...
  └──▶ LocaleManager.set("es") → Typer parses flags → creates CertificateConfig → CertbotService.generate(config)
```

**Package family selection in interactive mode:**

The assistant always explicitly asks for the family (`deb`/`rpm`) rather than auto-detecting, so the user consciously confirms the manager that will be used. If the user wants auto-detection they can select a third option `"Auto-detect"`.

```
  System package family:
    ❯  deb  — Debian / Ubuntu  (uses apt-get)
       rpm  — Fedora           (uses dnf)
       rpm  — openSUSE         (uses zypper)
       Auto-detect
```

### 3.5 Main Flow: `generate` (CertbotService)

```
1. CLI / wizard creates CertificateConfig (includes selected pkg_family)
2. CertbotService.generate(config) starts the flow:
   a. SystemRunner checks if user is root → warning/error (aborts)
   b. distro = DistroDetector.detect() → reads /etc/os-release → DistroFamily
   c. pkg_manager = PackageManagerFactory.get(distro) → Apt/Dnf/ZypperPackageManager
   d. DNSValidator.check(domain) → error if DNS doesn't resolve (except --skip-dns-check)
   e. Provider = ProviderFactory.get(server_type, pkg_manager)
   f. Provider.install() → pkg_manager.install(packages) with internal sudo
   g. Provider.configure(config) → generates and activates server config (with sudo)
   h. Provider.verify() → sudo nginx -t / apache -t / docker compose config
   i. CertbotInstaller.ensure_installed(distro_family, server_type):
      - If server_type == TRAEFIK: skip (ACME native, no Certbot needed)
      - Debian/Ubuntu: apt install snapd → snap install --classic certbot → ln -sf /snap/bin/certbot /usr/local/bin/certbot
      - Fedora: dnf install -y certbot python3-certbot-nginx python3-certbot-apache
      - openSUSE: zypper install -y certbot python3-certbot-nginx python3-certbot-apache
      - If already installed (certbot --version returns 0): skip all steps (idempotent)
   j. CertbotManager.request(domain, email, server_type, staging):
      - Nginx: sudo certbot --nginx -d domain --non-interactive --agree-tos --email email
      - Apache: sudo certbot --apache -d domain --non-interactive --agree-tos --email email
      - Traefik: skip (certificate obtained by Traefik ACME engine on first request)
   j2. CertbotManager.verify_service(server_type, distro_family) → systemctl status post-cert check
   k. CertRegistry.register(config) → saves to local registry (~/.config/gen_cerbot/)
   l. CLI shows success message with HTTPS URL
```

**Error / compensation flow:**

```
- In interactive mode: each error is shown with `[✗]` + message + option "Retry / Back to menu"
- In command mode: each error raises exception with actionable message and exit code != 0
- If step 2a fails (user is root) → show warning + usage instruction; abort
- If step 2b fails (distro not recognized) → show supported distros; abort
- If step 2d fails (DNS) → show error + suggest --skip-dns-check; abort
- If step 2f fails (pkg installation) → show error + equivalent manual command; abort
- If step 2g fails (invalid config) → show error + revert created file; abort
- If step 2j fails (Certbot rate limit) → show error + suggest --staging; config stays intact
- If step 2j fails (port 80 occupied) → show which process occupies port; abort
```

### 3.5 Flow: `list`

```
1. CertRegistry.list_all() → reads local JSON registry
2. For each cert: CertbotManager.get_expiry(domain) → actual expiry date from Certbot
3. Calculate status: OK (>30d), WARNING (7-30d), EXPIRED (<7d or past)
4. CLI renders table with colors
```

### 3.6 Flow: `renew`

```
1. If --domain specified: CertbotManager.renew(domain)
   Else: CertbotManager.renew_all()
2. CLI shows Certbot result (renewed, skipped, failed)
```

### 3.7 Certbot Installation and Execution Matrix

#### Installation by distro family

| Distro family | Prerequisite check | Install command | Post-install step |
|---|---|---|---|
| Debian / Ubuntu | `dpkg -l snapd` → install snapd if missing | `sudo snap install --classic certbot` | `sudo ln -sf /snap/bin/certbot /usr/local/bin/certbot` |
| Fedora (RHEL) | N/A | `sudo dnf install -y certbot python3-certbot-nginx python3-certbot-apache` | N/A |
| openSUSE | N/A | `sudo zypper install -y certbot python3-certbot-nginx python3-certbot-apache` | N/A |
| (Traefik) | N/A — ACME native | Not installed | Not installed |

#### Certificate request by server type

| Web server | Command | Notes |
|---|---|---|
| Nginx | `sudo certbot --nginx -d <domain> --non-interactive --agree-tos --email <email>` | Plugin `python3-certbot-nginx` must be installed |
| Apache | `sudo certbot --apache -d <domain> --non-interactive --agree-tos --email <email>` | Plugin `python3-certbot-apache` must be installed |
| Traefik | Not applicable | Traefik contacts Let's Encrypt ACME directly using `certificatesResolvers.letsencrypt` in `traefik.yml` |

With `--staging` flag: `--staging` is appended to the certbot command; test certificates issued by Let's Encrypt Staging CA (no rate limits).

#### Post-certificate service verification

| Web server | Distro | Command | Checks |
|---|---|---|---|
| Nginx | All | `sudo systemctl status nginx --no-pager` | Service active, no config errors |
| Apache | Debian/Ubuntu | `sudo systemctl status apache2 --no-pager` | Service active |
| Apache | Fedora/openSUSE | `sudo systemctl status httpd --no-pager` | Service active |
| Traefik | All | `docker compose ps` | Container running |

`CertbotManager.verify_service()` raises `ServerConfigError` if the service is not active after the certificate request.

---

## 4. Design Decisions

### DD-001: Provider (Strategy) pattern for web servers

- **Decision:** Use an abstract base class `ServerProvider` with methods `install()`, `configure()`, `verify()`, `remove()` that each server implements.
- **Context:** There are 3 supported servers with similar flows but different implementations. The orchestration code is the same for all.
- **Evaluated alternatives:**

| Option | Pros | Cons |
|---|---|---|
| **Provider pattern / Strategy (chosen)** | Extensible without modifying core; testable separately; clean code | Requires upfront interface design |
| Conditionals if/elif per server | Simple to implement | Hard to maintain; adding server = modifying multiple places |
| Dynamic plugins | Very extensible | Over-engineering for 3 servers |

- **Justification:** The Provider/Strategy pattern offers the right balance between extensibility and simplicity for the predicted number of servers.
- **Consequences:** When adding a new server (e.g., Caddy) it is sufficient to create `providers/caddy.py` and register it in `ProviderFactory`.

### DD-002: SystemRunner with granular sudo per command

- **Decision:** `SystemRunner.run(cmd, sudo=False)` accepts a `sudo` parameter that prepends `["sudo"]` to the argument list when `True`. The user runs the CLI as a normal user; only specific commands that require it are elevated.
- **Context:** Package installation, writing to `/etc/`, and service restart require elevated privileges. Running the entire process as root is a security anti-pattern. Elevating the entire process with `sudo gen-cerbot` is unnecessary and undesirable.
- **Evaluated alternatives:**

| Option | Pros | Cons |
|---|---|---|
| **Granular sudo in SystemRunner (chosen)** | Principle of least privilege; normal user runs CLI; easy to audit which commands use sudo | Requires sudo to be configured for user |
| Run entire CLI with sudo | Simple | Runs all Python code as root (security risk); anti-pattern |
| polkit / dbus for elevation | Without requiring sudo in sudoers | Complex, inconsistent across distros |

- **Justification:** The `sudo=True` parameter in `SystemRunner` is explicit, auditable in code, and testable with mocks without needing real permissions.
- **Consequences:** Unit tests mock entire `SystemRunner`. Integration tests require CI user to have `sudo NOPASSWD`.

### DD-003: Typer as CLI framework

- **Decision:** Use [Typer](https://typer.tiangolo.com/) to define the CLI instead of argparse or Click directly.
- **Evaluated alternatives:**

| Option | Pros | Cons |
|---|---|---|
| **Typer (chosen)** | Native type hints; autocompletion; rich output; built on Click | Additional dependency |
| argparse | stdlib, no deps | Verbose; no native type hints |
| Click | Mature, widely used | More boilerplate than Typer |

- **Justification:** Typer reduces CLI boilerplate and lets us leverage Python type annotations already used in the rest of the code.

### DD-004: Jinja2 templates for configuration files

- **Decision:** Web server configuration files are generated from Jinja2 templates in `src/gen_cerbot/templates/`, not hardcoded in Python.
- **Justification:** Separates configuration content from Python code; facilitates template review, modification, and testing; allows advanced users to customize them.

### DD-005: Local JSON registry for managed certificates

- **Decision:** Maintain a local JSON file (in `~/.config/gen_cerbot/registry.json`) that registers certificates created by the tool.
- **Justification:** Certbot does not easily expose metadata about the web server associated with each certificate. The local registry allows the `list` command to show enriched information (server, project, port).
- **Consequences:** The registry can fall out of sync if the user manipulates Certbot directly. The `list` command queries both the local registry and Certbot's actual state to reconcile.

### DD-006: Strategy pattern for package managers (PackageManager)

- **Decision:** Use an abstract base class `PackageManager` with methods `install(packages)`, `update()`, `is_installed(package)`, and concrete implementations `AptPackageManager`, `DnfPackageManager`, and `ZypperPackageManager`. A `PackageManagerFactory` constructs the correct instance from the detected `DistroFamily`.
- **Context:** Package installation is fundamentally different between distro families. Commands, flags, package names, and behaviors vary. Provider code must not know which distro it is running on.
- **Evaluated alternatives:**

| Option | Pros | Cons |
|---|---|---|
| **PackageManager Strategy + DistroDetector (chosen)** | Providers distro-agnostic; extensible; testable separately | Requires package name mapping per distro |
| Conditionals in each Provider | Simple | Massive duplication; adding distro = modifying all Providers |
| Ansible as manager | Declarative, multi-distro native | Very heavy external dependency; requires Python on target |
| `distro` package from PyPI | Robust distro detection | Does not solve manager abstraction; use alongside Strategy |

- **Justification:** The same Provider/Strategy pattern already proven for web servers is applied here consistently, keeping the architecture coherent.
- **Consequences:** Package names vary per distro (e.g., `python3-certbot-nginx` on Debian vs `certbot` on Fedora). Package name mapping lives in each `PackageManager` implementation, not in Providers.

### DD-007: questionary library for interactive mode

- **Decision:** Use [`questionary`](https://questionary.readthedocs.io/) for interactive prompts in the menu and guided assistant, combined with `rich` (already included as transitive dependency of Typer) for real-time output.
- **Context:** Interactive mode requires: keyboard arrow selection, text fields with inline validation, confirmation screen, and streaming execution output. The library must be lightweight, compatible with the existing Typer/rich architecture, and testable with mocks.
- **Evaluated alternatives:**

| Option | Pros | Cons |
|---|---|---|
| **questionary (chosen)** | Lightweight; clean API; built on prompt_toolkit; testable with `KeyboardInterrupt` mock; compatible with rich | Additional dependency |
| InquirerPy | More features (checkbox, fuzzy search) | Heavier; overkill for use case |
| prompt_toolkit directly | Maximum control | Very verbose API; requires lots of boilerplate |
| curses (stdlib) | No dependencies | Archaic API; difficult to test; not portable |
| click.prompt (via Typer) | Already included | Text prompts only; no navigable selection menus |

- **Justification:** `questionary` provides exactly the prompt types needed (`select`, `text`, `confirm`) with the cleanest API in the ecosystem. It weighs less than 50 KB and does not duplicate `rich` functionality. Its integration with `prompt_toolkit` enables consistent behavior across all supported terminals.
- **Consequences:** Add `questionary>=2.0` to `pyproject.toml`. Interactive mode tests use `questionary`'s `unsafe_ask()` with fixtures of predefined answers to avoid real interactive input.

### DD-009: JSON locale files for i18n system

- **Decision:** Implement i18n using plain JSON files per language (`en.json`, `es.json`) loaded by a lightweight `LocaleManager`, instead of `gettext`/`babel` or third-party libraries.
- **Context:** The interactive interface has a bounded and static set of text strings (menu, assistant, confirmations, errors). Needed: runtime language switching, fallback to English if key is missing, and ease of extension with new languages.
- **Evaluated alternatives:**

| Option | Pros | Cons |
|---|---|---|
| **JSON locales + LocaleManager (chosen)** | No extra dependencies; directly editable; easy to extend; O(1) memory load | No support for complex plurals or date/number formats |
| gettext / babel | De facto standard in Python; supports plurals | Requires compiling .po → .mo; complex setup; overkill for use case |
| python-i18n (PyPI) | Fluent API; supports YAML/JSON | Extra dependency; more than needed |
| fluent (Mozilla) | Modern; supports plurals and gender | Non-standard API; minimal Python adoption |

- **Justification:** The string set is static and small (< 100 keys). JSON is readable and editable without special tools. The `LocaleManager.t("key")` logic fits in < 30 lines. If plurals or formats are needed in the future, migration to `babel` is possible without changing the public interface (`t("key")`).
- **Consequences:** Add `i18n/` module with `locale_manager.py`, `selector.py`, and `locales/{en,es}.json`. Add global `--lang <code>` flag to entry point. Language preference stored in `~/.config/gen_cerbot/config.toml` (same path as cert registry). All hardcoded text in `interactive/` replaced with `LocaleManager.t("key")` calls.

### DD-008: `LiveOutputRenderer` with `rich.live` for real-time output

- **Decision:** Use `rich.live.Live` with an updatable panel to show execution progress step-by-step, instead of line-by-line printing with `print()`.
- **Context:** Installation and configuration steps can take seconds. Users need immediate visual feedback on what is happening, with status indicators (`[✔]`, `[→]`, `[✗]`) and executed `sudo` commands.
- **Evaluated alternatives:**

| Option | Pros | Cons |
|---|---|---|
| **rich.live + panel (chosen)** | In-place updates without scrolling; spinner indicators; already a dependency | Requires `with Live()` context |
| print() line by line | Simple; testable | No progress indicators; output broken if ANSI characters present |
| tqdm | Progress bars | Does not apply well to qualitative steps of variable duration |

- **Justification:** `rich` is already a dependency (via Typer[all]). `rich.live` allows showing a panel that updates in place without scrolling, giving clean visual feedback.
- **Consequences:** `LiveOutputRenderer` captures `SystemRunner` stdout step by step and feeds it to `rich.live`. Tests of `LiveOutputRenderer` capture output with `rich.Console(file=io.StringIO())`.

---

## 5. Data Models

### CertificateConfig

```python
from enum import Enum
from pydantic import BaseModel

class ServerType(str, Enum):
    NGINX = "nginx"
    APACHE = "apache"
    TRAEFIK = "traefik"

class CertificateConfig(BaseModel):
    domain: str                           # "sub.example.com"
    server_type: ServerType               # nginx | apache | traefik
    backend_port: int = 8000              # Port of dockerized service
    project_name: str                     # Name for config files
    email: str                            # Email for Let's Encrypt
    pkg_family: PkgFamily | None = None   # deb | rpm | None → auto-detect
    staging: bool = False                 # Use Let's Encrypt staging CA
    skip_dns_check: bool = False          # Skip DNS validation
    dry_run: bool = False                 # Do not apply real changes
    extra_domains: list[str] = []         # Additional domains (SAN)
    interactive: bool = True              # True = show output via LiveOutputRenderer
    lang: str = "en"                      # Active language code (en | es | ...)
```

### Language enum and LocaleManager

```python
class SupportedLang(str, Enum):
    EN = "en"   # English (default)
    ES = "es"   # Spanish

class LocaleManager:
    """Loads active language JSON and resolves keys with fallback to 'en'."""
    _instance: "LocaleManager | None" = None
    _translations: dict[str, str] = {}
    _fallback: dict[str, str] = {}       # always en.json

    def set_lang(self, lang: str) -> None: ...
    def t(self, key: str, **kwargs: str) -> str: ...   # kwargs for interpolation
```

Example structure of `locales/en.json`:

```json
{
  "menu.title": "gen_cerbot v{version}  —  TLS/SSL CLI",
  "menu.what_to_do": "What would you like to do?",
  "menu.generate": "Generate new SSL certificate",
  "menu.list": "List managed certificates",
  "menu.renew": "Renew certificates",
  "menu.remove": "Remove certificate for a domain",
  "menu.exit": "Exit",
  "wizard.subdomain": "Subdomain (e.g. app.example.com):",
  "wizard.port": "Dockerized service port (1-65535):",
  "wizard.pkg_family": "Package family:",
  "wizard.server": "Web server:",
  "wizard.email": "Let's Encrypt email:",
  "wizard.project": "Project name:",
  "wizard.confirm": "Continue with these settings?",
  "wizard.summary_title": "Summary",
  "output.step_install": "Installing packages",
  "output.step_configure": "Configuring web server",
  "output.step_certbot": "Obtaining certificate (Certbot)",
  "output.step_verify": "Verifying configuration",
  "output.done": "Done! Your site is now accessible at https://{domain}",
  "error.dns": "DNS error: {domain} does not resolve to this server ({ip})",
  "error.port_in_use": "Port 80 is already in use. Stop the process and retry.",
  "lang.select": "Select your language / Selecciona tu idioma:"
}
```

### CertificateRecord (local registry)

```python
class CertificateRecord(BaseModel):
    domain: str
    server_type: ServerType
    project_name: str
    backend_port: int | None
    email: str
    created_at: str                 # ISO-8601
    config_path: str                # Path to generated config file
    cert_name: str                  # Certificate name in Certbot
```

### DistroFamily and PackageManager

```python
class PkgFamily(str, Enum):
    """Explicit user selection (interactive) or derived from DistroFamily (auto-detect)."""
    DEB = "deb"   # Debian / Ubuntu → AptPackageManager
    RPM = "rpm"   # Fedora → DnfPackageManager; openSUSE → ZypperPackageManager

class DistroFamily(str, Enum):
    DEBIAN = "debian"    # Ubuntu, Debian → uses apt-get
    REDHAT = "redhat"    # Fedora, RHEL, CentOS → uses dnf
    SUSE   = "suse"      # openSUSE Leap, Tumbleweed → uses zypper
    UNKNOWN = "unknown"  # → raises UnsupportedDistroError

class PackageManager(ABC):
    def __init__(self, runner: SystemRunner): ...
    @abstractmethod
    def install(self, packages: list[str]) -> None: ...   # sudo <mgr> install -y pkgs
    @abstractmethod
    def update(self) -> None: ...                          # sudo <mgr> update/upgrade
    @abstractmethod
    def is_installed(self, package: str) -> bool: ...      # no sudo

class AptPackageManager(PackageManager):
    """sudo apt-get install -y {packages}"""

class DnfPackageManager(PackageManager):
    """sudo dnf install -y {packages}"""

class ZypperPackageManager(PackageManager):
    """sudo zypper install -y {packages}"""
```

### Package name mapping by distro

| Logical package | Debian/Ubuntu | Fedora | openSUSE |
|---|---|---|---|
| Nginx Server | `nginx` | `nginx` | `nginx` |
| Apache Server | `apache2` | `httpd` | `apache2` |
| Apache proxy plugin | `libapache2-mod-proxy-html` | `mod_proxy` (included) | `apache2-mod_proxy` |
| Certbot base | (snap) | `certbot` | `certbot` |
| Certbot Nginx plugin | `python3-certbot-nginx` | `python3-certbot-nginx` | `python3-certbot-nginx` |
| Certbot Apache plugin | `python3-certbot-apache` | `python3-certbot-apache` | `python3-certbot-apache` |

### Exception Hierarchy

```python
class GenCerbotError(Exception): ...              # Base
class DNSValidationError(GenCerbotError): ...     # Domain doesn't resolve → actionable message
class CertbotError(GenCerbotError): ...           # Certbot error → includes raw output
class ServerConfigError(GenCerbotError): ...      # Server config error
class SystemCommandError(GenCerbotError): ...     # subprocess failure → includes exit code and cmd
class DependencyError(GenCerbotError): ...        # Missing dependency (Docker, snapd)
class UnsupportedDistroError(GenCerbotError): ... # Distro not recognized in /etc/os-release
class SudoError(GenCerbotError): ...              # sudo unavailable or command denied
```

---

## 6. Security

| Vector | Mitigation |
|---|---|
| Execution as root | CLI detects `EUID == 0` and aborts with explanatory message |
| Privilege escalation | `sudo` prepended only to specific, predefined commands in `SystemRunner`; never to strings built from user input |
| System command injection | User arguments (domain, project_name) passed as string list to `subprocess.run`, never with `shell=True` |
| Permissions on `acme.json` (Traefik) | Generated with `os.chmod(path, 0o600)` explicitly |
| Private keys in logs | `SystemRunner` filters lines containing key patterns before logging |
| Template injection | Jinja2 with `autoescape=False` only for config files, never for HTML |
| Email in logs | User email never logged at DEBUG level or higher |

---

## 7. Observability

### Logging

The tool uses Python's standard `logging` module. Logs are written to `~/.local/share/gen_cerbot/gen_cerbot.log` with 7-day rotation.

```
[2026-03-31T14:30:00Z] [INFO]  Starting generate for domain=sub.example.com server=nginx
[2026-03-31T14:30:00Z] [INFO]  Distro detected: Ubuntu 22.04 (family=DEBIAN) → package_manager=apt
[2026-03-31T14:30:01Z] [INFO]  DNS check passed: sub.example.com → 203.0.113.5
[2026-03-31T14:30:02Z] [INFO]  Running: sudo apt-get install -y nginx
[2026-03-31T14:30:05Z] [INFO]  Nginx installed successfully
[2026-03-31T14:30:06Z] [INFO]  Running: sudo tee /etc/nginx/sites-available/myapp
[2026-03-31T14:30:06Z] [INFO]  Config written to /etc/nginx/sites-available/myapp
[2026-03-31T14:30:07Z] [INFO]  Running: sudo nginx -t
[2026-03-31T14:30:07Z] [INFO]  Nginx configuration test: OK
[2026-03-31T14:30:08Z] [INFO]  Installing Certbot via snap (Debian family)
[2026-03-31T14:30:40Z] [INFO]  Running: sudo certbot --nginx -d sub.example.com
[2026-03-31T14:30:45Z] [INFO]  Certificate obtained for sub.example.com
[2026-03-31T14:30:45Z] [INFO]  Registry updated: sub.example.com registered
```

### Console output (stdout)

- `[INFO]` in green
- `[WARN]` in yellow
- `[ERROR]` in red
- Progress with spinners (via `rich` or `typer` progress)

---

## 8. Testing Strategy

### 8.1 Test Pyramid

```
         ▲
        /E2E\          Manual / VM  — happy paths on Ubuntu, Fedora, openSUSE
       /──────\         (Phase 6, Let's Encrypt --staging)
      /  Integ \        pytest + tmp_path — critical flows without network or real sudo
     /──────────\
    /    Unit    \      pytest + unittest.mock — isolated business logic
   ──────────────
```

| Level | Coverage target | Environment | Main tools |
|---|---|---|---|
| **Unit** | > 85% per module | CI / local | `pytest`, `unittest.mock`, `pytest-mock` |
| **Integration** | Critical flows (10 minimum scenarios) | CI / local | `pytest`, `tmp_path`, static fixtures |
| **E2E / Manual** | Happy paths on 3 distros | Clean VM | Real environment + Let's Encrypt `--staging` |

### 8.2 Test Directory Structure

```
tests/
├── conftest.py                     # Global fixtures: runner_mock, pkg_manager_mock, tmp_config
├── unit/
│   ├── test_system_runner.py       # SystemRunner: sudo, no sudo, subprocess error
│   ├── test_distro_detector.py     # DistroDetector: 3 distros + unknown
│   ├── test_package_manager.py     # Apt/Dnf/Zypper: install, is_installed, update
│   ├── test_dns_validator.py       # DNSValidator: ok, fail, skip_dns_check
│   ├── test_cert_registry.py       # CertRegistry: add, list, remove, idempotence
│   ├── test_template_renderer.py   # TemplateRenderer: nginx, apache per distro, traefik
│   ├── test_nginx_provider.py      # NginxProvider: install, configure, verify, remove
│   ├── test_apache_provider.py     # ApacheProvider: 3 DistroFamily
│   ├── test_traefik_provider.py    # TraefikProvider: compose + acme.json generation
│   ├── test_certbot_installer.py   # CertbotInstaller: snap, dnf, zypper
│   ├── test_certbot_manager.py     # CertbotManager: certonly, renew, revoke, list
│   ├── test_certbot_service.py     # CertbotService: generate, list, renew, remove flow
│   ├── test_cli.py                 # CLI Typer: CliRunner per subcommand
│   ├── interactive/
│   │   ├── test_wizard.py          # GenerateWizard: fields, validation, summary
│   │   ├── test_menu.py            # InteractiveMenu: option routing
│   │   └── test_output.py          # LiveOutputRenderer: [✔]/[→]/[✗] indicators
│   └── i18n/
│       ├── test_locale_manager.py  # LocaleManager: t(), fallback, interpolation
│       └── test_language_selector.py # LanguageSelector: prompt, persistence, --lang
├── integration/
│   ├── test_nginx_config_gen.py    # Generates nginx file in tmp_path and validates content
│   ├── test_apache_config_gen.py   # Generates Apache VirtualHost per distro in tmp_path
│   ├── test_traefik_config_gen.py  # Generates docker-compose.yml + traefik.yml in tmp_path
│   ├── test_certbot_output.py      # Parsing real `certbot certificates` output
│   ├── test_cert_registry_io.py    # Reading/writing registry JSON on real disk
│   └── test_full_flow.py           # CertbotService end-to-end with all deps mocked
└── fixtures/
    ├── os-release/
    │   ├── ubuntu-22.04            # /etc/os-release content for Ubuntu 22.04
    │   ├── debian-12               # /etc/os-release content for Debian 12
    │   ├── fedora-40               # /etc/os-release content for Fedora 40
    │   ├── opensuse-leap-15.5      # /etc/os-release content for openSUSE Leap
    │   └── unknown-distro          # Distro with unknown ID (for UnsupportedDistroError)
    ├── certbot-outputs/
    │   ├── certificates_ok.txt     # Output of `certbot certificates` with 2 certs
    │   ├── certificates_empty.txt  # Output with "No certificates found"
    │   └── certonly_success.txt    # Output of `certbot certonly --nginx` success
    └── templates-rendered/
        ├── nginx-site-expected.conf        # Expected Nginx config for comparison
        ├── apache-debian-expected.conf     # Expected Apache VirtualHost for Debian
        ├── apache-redhat-expected.conf     # Expected Apache VirtualHost for Fedora
        └── traefik-compose-expected.yml    # Expected docker-compose.yml for Traefik
```

### 8.3 Global Fixtures (`conftest.py`)

```python
@pytest.fixture
def mock_runner(mocker):
    """SystemRunner with subprocess.run mocked — does not execute real commands."""
    runner = MagicMock(spec=SystemRunner)
    runner.run.return_value = CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    return runner

@pytest.fixture
def mock_apt(mock_runner):
    """AptPackageManager injected with mocked runner."""
    return AptPackageManager(runner=mock_runner)

@pytest.fixture
def mock_dnf(mock_runner):
    """DnfPackageManager injected with mocked runner."""
    return DnfPackageManager(runner=mock_runner)

@pytest.fixture
def tmp_config(tmp_path):
    """Temporary configuration directory for CertRegistry and LocaleManager."""
    config_dir = tmp_path / ".config" / "gen_cerbot"
    config_dir.mkdir(parents=True)
    return config_dir

@pytest.fixture
def ubuntu_os_release(tmp_path):
    """/etc/os-release file for Ubuntu 22.04 in temporary directory."""
    content = Path("tests/fixtures/os-release/ubuntu-22.04").read_text()
    f = tmp_path / "os-release"
    f.write_text(content)
    return f
```

### 8.4 Mocking Strategy per Module

| Module | Mocked dependency | Mock method | What is verified |
|---|---|---|---|
| `SystemRunner` | `subprocess.run` | `unittest.mock.patch` | cmd constructed, sudo prepended, returncode != 0 → `SystemCommandError` |
| `DistroDetector` | `/etc/os-release` | `tmp_path` + fixture file | Correct DistroFamily for Ubuntu/Fedora/openSUSE/unknown |
| `AptPackageManager` | `SystemRunner` | `MagicMock(spec=SystemRunner)` | cmd includes `apt-get install -y` + package list |
| `DnfPackageManager` | `SystemRunner` | `MagicMock(spec=SystemRunner)` | cmd includes `dnf install -y` + package list |
| `ZypperPackageManager` | `SystemRunner` | `MagicMock(spec=SystemRunner)` | cmd includes `zypper install -y` + package list |
| `NginxProvider` | `PackageManager`, `SystemRunner` | `MagicMock` | `install()` calls `pkg_manager.install(["nginx", ...])`; `verify()` uses `sudo=True` |
| `ApacheProvider` | `PackageManager`, `SystemRunner`, `DistroFamily` | `MagicMock` | package name varies by `DistroFamily` (apache2 / httpd); correct template |
| `TraefikProvider` | `SystemRunner`, `tmp_path` | `MagicMock` + `tmp_path` | generated files exist; `acme.json` with perms 600 |
| `DNSValidator` | `socket.getaddrinfo` | `unittest.mock.patch("socket.getaddrinfo")` | IP matches → OK; no match → `DNSValidationError` with message |
| `CertbotManager` | `SystemRunner` | `MagicMock` | `certonly` cmd includes `--nginx`/`--apache`; `certificates` parses fixture |
| `CertbotInstaller` | `SystemRunner`, `DistroFamily`, `ServerType` | `MagicMock` | snap+symlink for Debian, dnf for Fedora, zypper for SUSE; TRAEFIK skips install; idempotent if already installed |
| `CertbotService` | all of the above | multiple `MagicMock` + `patch` | correct call sequence; exception propagation |
| `GenerateWizard` | `questionary` | `mocker.patch("questionary.text.ask")` + `unsafe_ask` | fields with predefined values; validation rejects invalid emails |
| `LiveOutputRenderer` | `rich.Console` | `rich.Console(file=io.StringIO())` | output contains `[✔]` on completion; `[✗]` on failure |
| `LocaleManager` | `locales/*.json` files | `tmp_path` with custom JSON | `t("key")` returns correct text; missing key → fallback English |
| `LanguageSelector` | `questionary`, `config.toml` | `mocker.patch` + `tmp_config` fixture | persists lang in TOML; second call does not show prompt |
| CLI (Typer) | `CertbotService` | Typer CliRunner + `MagicMock` | exit code 0 on happy path; exit code != 0 with missing flag + `--no-interactive` |

### 8.5 Integration Test Patterns

Integration tests verify collaboration between two or more real modules, without network or sudo. Use `tmp_path` for disk I/O.

**Pattern: configuration file generation**

```python
def test_nginx_config_gen_creates_valid_file(tmp_path, mock_runner):
    config = CertificateConfig(
        domain="app.example.com", server_type=ServerType.NGINX,
        backend_port=8000, project_name="myapp", email="a@b.com"
    )
    provider = NginxProvider(runner=mock_runner, config_dir=tmp_path)
    provider.configure(config)

    site_file = tmp_path / "sites-available" / "myapp"
    assert site_file.exists()
    content = site_file.read_text()
    assert "app.example.com" in content
    assert "proxy_pass http://localhost:8000" in content
```

**Pattern: Certbot output parsing**

```python
def test_certbot_manager_parses_certificates_output(mock_runner):
    fixture = Path("tests/fixtures/certbot-outputs/certificates_ok.txt").read_text()
    mock_runner.run.return_value = CompletedProcess(args=[], returncode=0, stdout=fixture)
    manager = CertbotManager(runner=mock_runner)

    certs = manager.list_certificates()
    assert len(certs) == 2
    assert certs[0].domain == "api.example.com"
    assert certs[0].days_until_expiry > 0
```

**Pattern: complete `generate` flow with all deps mocked**

```python
def test_certbot_service_generate_full_flow(mock_runner, tmp_path, mocker):
    mocker.patch("socket.getaddrinfo", return_value=[("", "", "", "", ("203.0.113.1", 0))])
    mocker.patch("gen_cerbot.utils.system.get_local_ips", return_value=["203.0.113.1"])
    config = CertificateConfig(domain="app.example.com", ...)

    service = CertbotService(runner=mock_runner, config_dir=tmp_path)
    service.generate(config)

    # Verify call sequence
    calls = [str(c) for c in mock_runner.run.call_args_list]
    assert any("nginx -t" in c for c in calls)
    assert any("certbot" in c for c in calls)
```

### 8.6 Minimum Coverage per Module

| Module | Minimum coverage | Justification |
|---|---|---|
| `utils/system.py` | 95% | Security core — granular sudo |
| `utils/distro.py` | 100% | Critical detection logic, small module |
| `utils/package_manager.py` | 90% | All 3 implementations must cover install, update, is_installed |
| `utils/dns.py` | 90% | ok flow + error + skip must be covered |
| `providers/nginx.py` | 85% | install, configure, verify, remove |
| `providers/apache.py` | 85% | All 3 `DistroFamily` in configure |
| `providers/traefik.py` | 80% | File generation + chmod |
| `certbot/manager.py` | 85% | certonly, renew, revoke, list, parsing |
| `certbot/installer.py` | 90% | snap+snapd+symlink, dnf, zypper branches; traefik skip; already-installed idempotency |
| `domain/services.py` | 80% | Main flow + exception handling |
| `interactive/wizard.py` | 80% | Happy path + field validation |
| `interactive/output.py` | 75% | States [✔] [→] [✗] |
| `i18n/locale_manager.py` | 95% | Fallback, interpolation — critical for UX |
| `i18n/selector.py` | 85% | prompt, persistence, --lang override |
| `cli.py` | 75% | Main subcommands via CliRunner |

### 8.7 pytest and Coverage Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--strict-markers -v"
markers = [
    "unit: unit tests without real I/O",
    "integration: tests with disk I/O (tmp_path)",
    "e2e: tests requiring real Linux environment with sudo",
]

[tool.coverage.run]
source = ["src/gen_cerbot"]
omit = ["*/tests/*", "*/__init__.py"]

[tool.coverage.report]
fail_under = 80
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

**Usage commands:**

```bash
# Run only unit tests (without real I/O)
pytest -m unit

# Run unit + integration tests
pytest -m "unit or integration"

# View coverage per module
pytest --cov=src/gen_cerbot --cov-report=term-missing -m "unit or integration"

# Generate HTML coverage report
pytest --cov=src/gen_cerbot --cov-report=html

# E2E tests (require Linux environment with sudo)
pytest -m e2e --sudo
```

### 8.8 Testing Dependencies

```toml
# pyproject.toml — [project.optional-dependencies] group
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-mock>=3.12",      # mocker fixture (alternative to unittest.mock.patch)
    "pytest-cov>=5.0",        # integrated coverage
    "pytest-asyncio>=0.23",   # in case coroutines are used in future
    "rich",                   # already a production dependency
    "typer[all]",             # already a production dependency
]
```

---

## 9. Packaging and Distribution

```toml
# pyproject.toml
[project]
name = "gen-cerbot"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "typer[all]>=0.12",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "jinja2>=3.1",
    "dnspython>=2.4",
    "rich>=13.0",
]

[project.scripts]
gen-cerbot = "gen_cerbot.cli:app"

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "UP"]
```

---

## 10. Open Questions

- [ ] Is Debian support required for v1.0 or only Ubuntu? — Owner: Ernesto, Deadline: before Phase 1
- [ ] Should automatic renewal configuration be generated as cron or as systemd timer? — Owner: Ernesto, Deadline: before Phase 4
- [ ] Should Traefik mode generate a new `docker-compose.yml` or only Traefik configuration files, assuming the user already has one? — Owner: Ernesto, Deadline: before Phase 3

---

## Change History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-03-31 | Ernesto Crespo | Initial version: base architecture Nginx/Apache/Traefik, Provider pattern, Certbot, Typer |
| 1.1 | 2026-03-31 | Ernesto Crespo | Multi-distro: DistroDetector, PackageManager ABC (Apt/Dnf/Zypper), PkgFamily enum, SystemRunner with granular sudo, package name mapping table per distro, DD-005 PackageManager Strategy, DD-006 granular sudo |
| 1.2 | 2026-03-31 | Ernesto Crespo | Interactive mode: interactive/ module (menu.py, wizard.py, output.py), InteractiveMenu/GenerateWizard/LiveOutputRenderer components, updated dual-mode diagram, DD-007 questionary, DD-008 rich.live, CertificateConfig with interactive field |
| 1.3 | 2026-03-31 | Ernesto Crespo | i18n support: i18n/ module (locale_manager.py, selector.py, locales/en.json, es.json), LanguageSelector, LocaleManager, DD-009 JSON locales, global --lang flag, lang field in CertificateConfig, locale JSON structure example, entry diagram updated with i18n layer |
| 1.4 | 2026-03-31 | Ernesto Crespo | Native packaging: complete pyproject.toml, packaging/debian/, packaging/rpm/gen-cerbot.spec; Section 9 updated with .deb and .rpm |
| 1.5 | 2026-03-31 | Ernesto Crespo | Testing specifications: Section 8 rewritten with test pyramid, tests/ structure, fixture catalog (os-release, certbot-outputs, templates-rendered), conftest.py with global fixtures, mocking table per module, integration patterns, minimum coverage per module, pyproject.toml with pytest/coverage config and dev dependencies |
| 1.6 | 2026-03-31 | Ernesto Crespo | Certbot detail: Section 3.7 (installation matrix, certificate request matrix, post-cert service verification table); CertbotInstaller updated with snapd pre-check and symlink; main flow step i/j refined with per-distro commands and verify_service step; mock strategy and coverage table updated |
