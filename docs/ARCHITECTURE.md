# gen_cerbot — Technical Design Document

## Metadata

| Campo | Valor |
|---|---|
| **Autor** | Ernesto Crespo |
| **Estado** | `DRAFT` |
| **Versión** | 1.5 |
| **Fecha** | 2026-03-31 |
| **SPEC Relacionado** | [SPEC.md](./SPEC.md) |
| **Reviewers** | Por definir |

---

## 1. Contexto

`gen_cerbot` es una herramienta CLI que automatiza la configuración TLS/SSL para múltiples servidores web. Técnicamente, el problema se descompone en dos responsabilidades independientes: (a) configurar el servidor web (Nginx, Apache, Traefik) con reverse proxy y las directivas correctas, y (b) gestionar el ciclo de vida de los certificados Let's Encrypt a través de Certbot.

El script bash original (`nginx-setup.sh`) combina ambas responsabilidades en un único flujo secuencial, lo que lo hace frágil, difícil de testear y no extensible a otros servidores. La arquitectura propuesta separa estas responsabilidades en módulos independientes bajo un patrón Provider que permite agregar nuevos servidores sin modificar el código central.

La herramienta corre en el sistema operativo del servidor (Ubuntu/Debian, Fedora, openSUSE), detecta la distribución en tiempo de ejecución e invoca el gestor de paquetes apropiado (`apt-get`, `dnf`, `zypper`) para instalar dependencias al vuelo. Todos los comandos que requieren privilegios elevados se ejecutan anteponiendo `sudo` de forma interna — el usuario corre el CLI como usuario normal y la herramienta escala privilegios de forma granular solo donde es necesario. La herramienta también lee y escribe archivos de configuración del servidor y se comunica con los servicios ACME de Let's Encrypt a través de Certbot.

---

## 2. Objetivos Técnicos

- **Correctitud:** Los archivos de configuración generados deben ser válidos y seguros para producción; el proceso debe ser idempotente
- **Extensibilidad:** Agregar soporte para un nuevo servidor web debe requerir solo crear un nuevo Provider sin modificar el core
- **Testabilidad:** El código debe ser testeable con mocks del sistema de archivos y de los comandos del sistema
- **Mantenibilidad:** Cobertura de tests > 80%, type hints en todas las funciones públicas, código formateado con ruff
- **Usabilidad:** Modo interactivo con menú guiado como modo por defecto; modo comando como alternativa para automatización; salida en tiempo real con indicadores visuales

---

## 3. Arquitectura Propuesta

### 3.1 Diagrama de Alto Nivel

```
┌──────────────────────────────────────────────────────────────────┐
│                      Punto de entrada                            │
│              gen-cerbot  (sin args → modo interactivo)           │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                 LanguageSelector / LocaleManager (i18n)          │
│  --lang flag → config.toml → selector questionary → fallback en  │
└──────────────┬───────────────────────────┬───────────────────────┘
               │                           │
               ▼                           ▼
┌──────────────────────────┐   ┌───────────────────────────────────┐
│   Modo Interactivo        │   │   Modo Comando (Typer)            │
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
│               PackageManager (abstracción)                   │
│   install(pkg) / update() / is_installed(pkg)                │
│                                                              │
│  AptPackageManager  DnfPackageManager  ZypperPackageManager  │
│  (Debian/Ubuntu)        (Fedora)          (openSUSE)         │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                  SystemRunner                                │
│   run(cmd, sudo=True/False) → subprocess con sudo interno    │
└──────────────────────────────────────────────────────────────┘
                         ▲
                         │
┌──────────────────────────────────────────────────────────────┐
│                  DistroDetector                              │
│   detect() → lee /etc/os-release → DistroFamily enum        │
│   (DEBIAN | REDHAT | SUSE | UNKNOWN)                        │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Componentes

| Componente | Módulo Python | Responsabilidad |
|---|---|---|
| Entry point | `cli.py` | Sin args → lanza InteractiveMenu; con args → Typer |
| InteractiveMenu | `interactive/menu.py` | Menú principal navegable (questionary); routing a wizard o subcomandos |
| GenerateWizard | `interactive/wizard.py` | Asistente paso a paso: dominio → puerto → pkg-family → servidor → email → confirmación |
| LiveOutputRenderer | `interactive/output.py` | Imprime salida de ejecución en tiempo real con `[✔]`/`[→]`/`[✗]` via rich |
| LocaleManager | `i18n/locale_manager.py` | Carga el archivo JSON del idioma activo y resuelve claves de texto; fallback a `en` |
| LanguageSelector | `i18n/selector.py` | Muestra selector `questionary` de idioma si no hay preferencia guardada; persiste en config.toml |
| CLI (Typer) | `cli.py` | Subcomandos directos: generate, list, renew, remove; flags `--no-interactive`, `--lang` |
| CertbotService | `domain/services.py` | Orquestación del flujo completo generate/renew/remove |
| ServerProvider (ABC) | `providers/base.py` | Interfaz abstracta: `install()`, `configure()`, `verify()`, `remove()` |
| NginxProvider | `providers/nginx.py` | Configuración Nginx multi-distro usando PackageManager |
| ApacheProvider | `providers/apache.py` | Configuración Apache multi-distro usando PackageManager |
| TraefikProvider | `providers/traefik.py` | Generación de docker-compose.yml + traefik.yml |
| CertbotManager | `certbot/manager.py` | Wraps certbot CLI: install, certonly, renew, revoke, certificates |
| CertbotInstaller | `certbot/installer.py` | Detecta e instala Certbot según la distro (snap / dnf / zypper) |
| DistroDetector | `utils/distro.py` | Lee `/etc/os-release` y retorna `DistroFamily` (DEBIAN, REDHAT, SUSE) |
| PackageManager (ABC) | `utils/package_manager.py` | Interfaz abstracta: `install()`, `update()`, `is_installed()` |
| AptPackageManager | `utils/package_manager.py` | Implementación `apt-get` para Debian/Ubuntu |
| DnfPackageManager | `utils/package_manager.py` | Implementación `dnf` para Fedora/RHEL |
| ZypperPackageManager | `utils/package_manager.py` | Implementación `zypper` para openSUSE |
| DNSValidator | `utils/dns.py` | Resuelve el dominio y compara contra IPs locales del servidor |
| CertRegistry | `utils/registry.py` | Lee y escribe el registro JSON local de certificados gestionados |
| SystemRunner | `utils/system.py` | Abstracción subprocess con soporte `sudo=True/False` por comando |
| TemplateRenderer | `utils/templates.py` | Renderiza plantillas Jinja2 para archivos de configuración |
| Config | `core/config.py` | Configuración global: rutas, defaults, variables de entorno |
| Exceptions | `core/exceptions.py` | Jerarquía de excepciones del dominio |

### 3.3 Estructura de Archivos del Proyecto

```
src/gen_cerbot/
├── __init__.py
├── cli.py                      # Entry point: sin args → InteractiveMenu; con args → Typer subcomandos
├── core/
│   ├── config.py               # Paths, defaults, env vars (pydantic-settings)
│   └── exceptions.py           # DomainError, DNSError, CertbotError, ServerConfigError, UnsupportedDistroError
├── domain/
│   ├── models.py               # CertificateConfig, ServerType (Enum), CertificateStatus, DistroFamily
│   └── services.py             # CertbotService: orquestación principal
├── providers/
│   ├── base.py                 # ServerProvider (ABC) — recibe PackageManager en constructor
│   ├── nginx.py                # NginxProvider (multi-distro)
│   ├── apache.py               # ApacheProvider (multi-distro)
│   ├── traefik.py              # TraefikProvider
│   └── factory.py              # ProviderFactory.get(server_type, pkg_manager)
├── interactive/
│   ├── menu.py                 # InteractiveMenu: menú principal con questionary
│   ├── wizard.py               # GenerateWizard: recoge subdominio, puerto, pkg-family, servidor
│   └── output.py               # LiveOutputRenderer: impresión en tiempo real con rich
├── i18n/
│   ├── locale_manager.py       # LocaleManager: carga locale JSON activo; t("key") → texto
│   ├── selector.py             # LanguageSelector: prompt questionary + persistencia config.toml
│   └── locales/
│       ├── en.json             # Todas las cadenas de la interfaz en inglés (idioma por defecto)
│       └── es.json             # Traducción al español
├── certbot/
│   ├── installer.py            # Detecta/instala Certbot: snap (Debian), dnf (Fedora), zypper (SUSE)
│   └── manager.py              # Wraps certbot CLI con sudo interno
├── utils/
│   ├── distro.py               # DistroDetector: lee /etc/os-release → DistroFamily
│   ├── package_manager.py      # PackageManager (ABC) + Apt/Dnf/ZypperPackageManager
│   ├── dns.py                  # Resolución DNS y comparación de IPs
│   ├── system.py               # SystemRunner: subprocess con parámetro sudo=True/False
│   ├── registry.py             # JSON registry de certs gestionados
│   └── templates.py            # Jinja2 renderer
└── templates/
    ├── nginx/
    │   └── site.conf.j2        # Template VirtualHost Nginx (válido para todas las distros)
    ├── apache/
    │   ├── vhost-debian.conf.j2    # Template Apache para Debian/Ubuntu
    │   ├── vhost-redhat.conf.j2    # Template Apache para Fedora/RHEL
    │   └── vhost-suse.conf.j2      # Template Apache para openSUSE
    └── traefik/
        ├── docker-compose.yml.j2
        └── traefik.yml.j2
```

### 3.4 Flujo de entrada: modo interactivo vs. modo comando

```
gen-cerbot  (sin args)
  └──▶ LanguageSelector.resolve()
         ├── Si --lang <code> fue pasado → LocaleManager.set(code)
         ├── Si config.toml tiene preferencia → LocaleManager.set(saved_lang)
         └── Si ninguna → muestra selector questionary → guarda en config.toml
                  Select your language / Selecciona tu idioma:
                   ❯  English
                      Español
  └──▶ InteractiveMenu.run()   ← todos los textos vía LocaleManager.t("key")
         ├── Opción "Generate certificate" → GenerateWizard.run()
         │     1. Solicita subdominio (validación regex dominio)
         │     2. Solicita puerto dockerizado (default 8000, rango 1-65535)
         │     3. Selección pkg-family: deb | rpm
         │     4. Selección servidor: nginx | apache | traefik
         │     5. Solicita email para Let's Encrypt
         │     6. Solicita nombre del proyecto
         │     7. Muestra resumen + confirmación (t("wizard.confirm"))
         │     8. Si confirma → CertbotService.generate(config)
         │                       con LiveOutputRenderer.attach()
         ├── Opción "List certificates" → CertbotService.list()
         ├── Opción "Renew certificates" → CertbotService.renew()
         ├── Opción "Remove certificate" → solicita dominio → CertbotService.remove()
         └── Opción "Exit" → sys.exit(0)

gen-cerbot --lang es generate --server nginx --domain X --port Y --pkg-family deb ...
  └──▶ LocaleManager.set("es") → Typer parsea flags → crea CertificateConfig → CertbotService.generate(config)
```

**Selección de familia de paquetes en modo interactivo:**

El asistente siempre pregunta explícitamente por la familia (`deb`/`rpm`) en lugar de auto-detectar, para que el usuario confirme conscientemente el gestor que se usará. Si el usuario quiere auto-detección puede seleccionar una tercera opción `"Detectar automáticamente"`.

```
  Familia de paquetes del sistema:
    ❯  deb  — Debian / Ubuntu  (usa apt-get)
       rpm  — Fedora           (usa dnf)
       rpm  — openSUSE         (usa zypper)
       Detectar automáticamente
```

### 3.5 Flujo Principal: `generate` (CertbotService)

```
1. CLI / wizard crea CertificateConfig (incluye pkg_family seleccionada)
2. CertbotService.generate(config) inicia el flujo:
   a. SystemRunner verifica si usuario es root → advertencia/error (aborta)
   b. distro = DistroDetector.detect() → lee /etc/os-release → DistroFamily
   c. pkg_manager = PackageManagerFactory.get(distro) → Apt/Dnf/ZypperPackageManager
   d. DNSValidator.check(domain) → error si DNS no resuelve (salvo --skip-dns-check)
   e. Provider = ProviderFactory.get(server_type, pkg_manager)
   f. Provider.install() → pkg_manager.install(paquetes) con sudo interno
   g. Provider.configure(config) → genera y activa config del servidor (con sudo)
   h. Provider.verify() → sudo nginx -t / apache -t / docker compose config
   i. CertbotInstaller.ensure_installed(pkg_manager) → instala Certbot según distro
   j. CertbotManager.request(domain, email, staging) → sudo certbot …
   k. CertRegistry.register(config) → guarda en registro local (~/.config/gen_cerbot/)
   l. CLI muestra mensaje de éxito con URL HTTPS
```

**Flujo de error / compensación:**

```
- En modo interactivo: cada error se muestra con `[✗]` + mensaje + opción "Reintentar / Volver al menú"
- En modo comando: cada error lanza excepción con mensaje accionable y exit code != 0
- Si paso 2a falla (usuario es root) → mostrar advertencia + instrucción de uso; abortar
- Si paso 2b falla (distro no reconocida) → mostrar distros soportadas; abortar
- Si paso 2d falla (DNS) → mostrar error + sugerir --skip-dns-check; abortar
- Si paso 2f falla (instalación pkg) → mostrar error + comando manual equivalente; abortar
- Si paso 2g falla (config inválida) → mostrar error + revertir archivo creado; abortar
- Si paso 2j falla (rate limit Certbot) → mostrar error + sugerir --staging; config queda intacta
- Si paso 2j falla (puerto 80 ocupado) → mostrar qué proceso ocupa el puerto; abortar
```

### 3.5 Flujo: `list`

```
1. CertRegistry.list_all() → lee registro local JSON
2. Para cada cert: CertbotManager.get_expiry(domain) → fecha real de Certbot
3. Calcular estado: OK (>30d), WARNING (7-30d), EXPIRED (<7d o pasada)
4. CLI renderiza tabla con colores
```

### 3.6 Flujo: `renew`

```
1. Si --domain especificado: CertbotManager.renew(domain)
   Sino: CertbotManager.renew_all()
2. CLI muestra resultado de Certbot (renovados, omitidos, fallidos)
```

---

## 4. Decisiones de Diseño

### DD-001: Patrón Provider (Strategy) para servidores web

- **Decisión:** Usar una clase base abstracta `ServerProvider` con métodos `install()`, `configure()`, `verify()`, `remove()` que cada servidor implementa.
- **Contexto:** Hay 3 servidores soportados con flujos similares pero implementaciones distintas. El código de orquestación es el mismo para todos.
- **Alternativas evaluadas:**

| Opción | Pros | Contras |
|---|---|---|
| **Provider pattern / Strategy (elegida)** | Extensible sin modificar core; testeable por separado; código limpio | Requiere diseño previo de la interfaz |
| Condicionales if/elif por servidor | Simple de implementar | Difícil de mantener; agregar servidor = modificar múltiples lugares |
| Plugins dinámicos | Muy extensible | Over-engineering para 3 servidores |

- **Justificación:** El patrón Provider/Strategy ofrece el balance correcto entre extensibilidad y simplicidad para el número de servidores previsto.
- **Consecuencias:** Al agregar un nuevo servidor (ej: Caddy) basta con crear `providers/caddy.py` y registrarlo en `ProviderFactory`.

### DD-002: SystemRunner con sudo granular por comando

- **Decisión:** `SystemRunner.run(cmd, sudo=False)` acepta un parámetro `sudo` que antepone `["sudo"]` a la lista de argumentos cuando es `True`. El usuario ejecuta el CLI como usuario normal; solo los comandos específicos que lo requieren se elevan.
- **Contexto:** Las operaciones de instalación de paquetes, escritura en `/etc/` y reinicio de servicios requieren privilegios. Ejecutar todo el proceso como root es un anti-patrón de seguridad. Elvar el proceso completo con `sudo gen-cerbot` no es necesario ni deseable.
- **Alternativas evaluadas:**

| Opción | Pros | Contras |
|---|---|---|
| **sudo granular en SystemRunner (elegida)** | Principio de mínimo privilegio; usuario normal ejecuta el CLI; fácil de auditar qué comandos usan sudo | Requiere que el usuario tenga sudo configurado |
| Ejecutar todo el CLI con sudo | Simple | Ejecuta como root todo el código Python (riesgo de seguridad); anti-patrón |
| polkit / dbus para elevación | Sin requerir sudo en sudoers | Complejo, inconsistente entre distros |

- **Justificación:** El parámetro `sudo=True` en `SystemRunner` es explícito, auditable en código y testeable con mocks sin necesitar permisos reales.
- **Consecuencias:** Los tests unitarios mockean `SystemRunner` completo. Los tests de integración requieren que el usuario de CI tenga `sudo NOPASSWD`.

### DD-003: Typer como framework CLI

- **Decisión:** Usar [Typer](https://typer.tiangolo.com/) para definir el CLI en lugar de argparse o Click directamente.
- **Alternativas evaluadas:**

| Opción | Pros | Contras |
|---|---|---|
| **Typer (elegida)** | Type hints nativos; autocompletado; rich output; basado en Click | Dependencia adicional |
| argparse | stdlib, sin deps | Verbose; sin type hints nativos |
| Click | Maduro, muy usado | Más boilerplate que Typer |

- **Justificación:** Typer reduce el boilerplate de CLI y permite aprovechar las anotaciones de tipo Python ya usadas en el resto del código.

### DD-004: Plantillas Jinja2 para archivos de configuración

- **Decisión:** Los archivos de configuración de servidores web se generan desde plantillas Jinja2 en `src/gen_cerbot/templates/`, no hardcodeados en Python.
- **Justificación:** Separa el contenido de la configuración del código Python; facilita la revisión, modificación y testing de las plantillas; permite que usuarios avanzados las customicen.

### DD-005: Registro local JSON para certificados gestionados

- **Decisión:** Mantener un archivo JSON local (en `~/.config/gen_cerbot/registry.json`) que registra los certificados creados por la herramienta.
- **Justificación:** Certbot no expone fácilmente metadatos sobre el servidor web asociado a cada certificado. El registro local permite al comando `list` mostrar información enriquecida (servidor, proyecto, puerto).
- **Consecuencias:** El registro puede desincronizarse si el usuario manipula Certbot directamente. El comando `list` consulta tanto el registro local como el estado real de Certbot para reconciliar.

### DD-006: Patrón Strategy para gestores de paquetes (PackageManager)

- **Decisión:** Usar una clase base abstracta `PackageManager` con métodos `install(packages)`, `update()`, `is_installed(package)`, e implementaciones concretas `AptPackageManager`, `DnfPackageManager` y `ZypperPackageManager`. Un `PackageManagerFactory` construye la instancia correcta a partir del `DistroFamily` detectado.
- **Contexto:** La instalación de paquetes es fundamentalmente diferente entre familias de distribuciones. Los comandos, flags, nombres de paquetes y comportamientos varían. El código de los Providers no debe conocer en qué distro está corriendo.
- **Alternativas evaluadas:**

| Opción | Pros | Contras |
|---|---|---|
| **PackageManager Strategy + DistroDetector (elegida)** | Providers agnósticos de distro; extensible; testeable por separado | Requiere mapeo de nombres de paquetes por distro |
| Condicionales en cada Provider | Simple | Duplicación masiva; agregar distro = modificar todos los Providers |
| Ansible como gestor | Declarativo, multi-distro nativo | Dependencia externa muy pesada; requiere Python en target |
| `distro` package de PyPI | Detección de distro robusta | No resuelve la abstracción del gestor; usar junto a la Strategy |

- **Justificación:** El mismo patrón Provider/Strategy ya probado para servidores web se aplica aquí de forma consistente, manteniendo la arquitectura coherente.
- **Consecuencias:** Los nombres de paquetes varían por distro (ej: `python3-certbot-nginx` en Debian vs `certbot` en Fedora). El mapeo de paquetes vive en cada implementación de `PackageManager`, no en los Providers.

### DD-007: questionary como librería para el modo interactivo

- **Decisión:** Usar [`questionary`](https://questionary.readthedocs.io/) para los prompts interactivos del menú y el asistente guiado, combinado con `rich` (ya incluido como dependencia transitiva de Typer) para la salida en tiempo real.
- **Contexto:** El modo interactivo requiere: selección con flechas de teclado, campos de texto con validación en línea, pantalla de confirmación y streaming de salida de ejecución. La librería debe ser liviana, compatible con la arquitectura Typer/rich existente y testeable con mocks.
- **Alternativas evaluadas:**

| Opción | Pros | Contras |
|---|---|---|
| **questionary (elegida)** | Liviana; API limpia; built on prompt_toolkit; testeable con `KeyboardInterrupt` mock; compatible con rich | Dependencia adicional |
| InquirerPy | Más features (checkbox, fuzzy search) | Más pesada; overkill para el caso de uso |
| prompt_toolkit directo | Máximo control | API muy verbose; requiere mucho boilerplate |
| curses (stdlib) | Sin dependencias | API arcaica; difícil de testear; no portátil |
| click.prompt (via Typer) | Ya incluido | Solo text prompts; no soporta menús de selección navegables |

- **Justificación:** `questionary` provee exactamente los tipos de prompt necesarios (`select`, `text`, `confirm`) con la API más limpia del ecosistema. Pesa menos de 50 KB y no duplica funcionalidad de `rich`. Su integración con `prompt_toolkit` permite un comportamiento consistente en todos los terminales soportados.
- **Consecuencias:** Se añade `questionary>=2.0` a `pyproject.toml`. Los tests del modo interactivo usan `questionary`'s `unsafe_ask()` con fixtures de respuestas predefinidas para evitar input interactivo real.

### DD-009: JSON locale files para el sistema i18n

- **Decisión:** Implementar i18n mediante archivos JSON planos por idioma (`en.json`, `es.json`) cargados por un `LocaleManager` ligero, en lugar de usar `gettext`/`babel` o librerías de terceros.
- **Contexto:** La interfaz interactiva tiene un conjunto acotado y estático de cadenas de texto (menú, asistente, confirmaciones, errores). Se necesita: cambio de idioma en tiempo de ejecución, fallback a inglés si una clave falta, y que sea fácil de extender con nuevos idiomas.
- **Alternativas evaluadas:**

| Opción | Pros | Contras |
|---|---|---|
| **JSON locales + LocaleManager (elegida)** | Sin dependencias extra; editable directamente; fácil de extender; carga en memoria O(1) | No soporta plurales complejos ni formatos de fecha/número |
| gettext / babel | Estándar de facto en Python; soporta plurales | Requiere compilar .po → .mo; setup complejo; overkill para el caso de uso |
| python-i18n (PyPI) | API fluida; soporta YAML/JSON | Dependencia extra; más de lo necesario |
| fluent (Mozilla) | Moderno; soporta plurales y géneros | API no-estándar; muy poca adopción en Python CLI |

- **Justificación:** El conjunto de cadenas es estático y pequeño (< 100 claves). JSON es legible y editable sin herramientas especiales. La lógica de `LocaleManager.t("key")` cabe en < 30 líneas. Si en el futuro se necesitan plurales o formatos, se puede migrar a `babel` sin cambiar la interfaz pública (`t("key")`).
- **Consecuencias:** Se añade el módulo `i18n/` con `locale_manager.py`, `selector.py` y `locales/{en,es}.json`. Se agrega el flag global `--lang <code>` al entry point. La preferencia de idioma se almacena en `~/.config/gen_cerbot/config.toml` (misma ruta que el registro de certs). Todos los textos hardcoded de `interactive/` se reemplazan por llamadas a `LocaleManager.t("clave")`.

### DD-008: `LiveOutputRenderer` con `rich.live` para salida en tiempo real

- **Decisión:** Usar `rich.live.Live` con un panel actualizable para mostrar el progreso de ejecución paso a paso, en lugar de imprimir línea a línea con `print()`.
- **Contexto:** Los pasos de instalación y configuración pueden tardar segundos. El usuario necesita feedback visual inmediato de qué está pasando, con indicadores de estado (`[✔]`, `[→]`, `[✗]`) y los comandos `sudo` ejecutados.
- **Alternativas evaluadas:**

| Opción | Pros | Contras |
|---|---|---|
| **rich.live + panel (elegida)** | Actualización in-place sin scroll; indicadores de spinner; ya es dependencia | Requiere contexto `with Live()` |
| print() línea a línea | Simple; testeable | Sin indicadores de progreso; output roto si hay caracteres ANSI |
| tqdm | Barras de progreso | No aplica bien a pasos cualitativos de duración variable |

- **Justificación:** `rich` ya es dependencia (via Typer[all]). `rich.live` permite mostrar un panel que se actualiza en el lugar sin hacer scroll, lo que da feedback visual limpio.
- **Consecuencias:** `LiveOutputRenderer` captura el `stdout` de `SystemRunner` paso a paso y lo feed a `rich.live`. Los tests de `LiveOutputRenderer` capturan el output con `rich.Console(file=io.StringIO())`.

---

## 5. Modelos de Datos

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
    backend_port: int = 8000              # Puerto del servicio dockerizado
    project_name: str                     # Nombre para archivos de config
    email: str                            # Email para Let's Encrypt
    pkg_family: PkgFamily | None = None   # deb | rpm | None → auto-detect
    staging: bool = False                 # Usar CA de staging de Let's Encrypt
    skip_dns_check: bool = False          # Omitir validación DNS
    dry_run: bool = False                 # No aplicar cambios reales
    extra_domains: list[str] = []         # Dominios adicionales (SAN)
    interactive: bool = True              # True = mostrar output via LiveOutputRenderer
    lang: str = "en"                      # Código de idioma activo (en | es | ...)
```

### Language enum y LocaleManager

```python
class SupportedLang(str, Enum):
    EN = "en"   # English (default)
    ES = "es"   # Español

class LocaleManager:
    """Carga el JSON del idioma activo y resuelve claves con fallback a 'en'."""
    _instance: "LocaleManager | None" = None
    _translations: dict[str, str] = {}
    _fallback: dict[str, str] = {}       # siempre en.json

    def set_lang(self, lang: str) -> None: ...
    def t(self, key: str, **kwargs: str) -> str: ...   # kwargs para interpolación
```

Ejemplo de estructura de `locales/en.json`:

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

### CertificateRecord (registro local)

```python
class CertificateRecord(BaseModel):
    domain: str
    server_type: ServerType
    project_name: str
    backend_port: int | None
    email: str
    created_at: str                 # ISO-8601
    config_path: str                # Ruta al archivo de config generado
    cert_name: str                  # Nombre del cert en Certbot
```

### DistroFamily y PackageManager

```python
class PkgFamily(str, Enum):
    """Selección explícita del usuario (interactivo) o derivada de DistroFamily (auto-detect)."""
    DEB = "deb"   # Debian / Ubuntu → AptPackageManager
    RPM = "rpm"   # Fedora → DnfPackageManager; openSUSE → ZypperPackageManager

class DistroFamily(str, Enum):
    DEBIAN = "debian"    # Ubuntu, Debian → usa apt-get
    REDHAT = "redhat"    # Fedora, RHEL, CentOS → usa dnf
    SUSE   = "suse"      # openSUSE Leap, Tumbleweed → usa zypper
    UNKNOWN = "unknown"  # → lanza UnsupportedDistroError

class PackageManager(ABC):
    def __init__(self, runner: SystemRunner): ...
    @abstractmethod
    def install(self, packages: list[str]) -> None: ...   # sudo <mgr> install -y pkgs
    @abstractmethod
    def update(self) -> None: ...                          # sudo <mgr> update/upgrade
    @abstractmethod
    def is_installed(self, package: str) -> bool: ...      # sin sudo

class AptPackageManager(PackageManager):
    """sudo apt-get install -y {packages}"""

class DnfPackageManager(PackageManager):
    """sudo dnf install -y {packages}"""

class ZypperPackageManager(PackageManager):
    """sudo zypper install -y {packages}"""
```

### Mapeo de nombres de paquetes por distro

| Paquete lógico | Debian/Ubuntu | Fedora | openSUSE |
|---|---|---|---|
| Servidor Nginx | `nginx` | `nginx` | `nginx` |
| Servidor Apache | `apache2` | `httpd` | `apache2` |
| Plugin proxy Apache | `libapache2-mod-proxy-html` | `mod_proxy` (incluido) | `apache2-mod_proxy` |
| Certbot base | (snap) | `certbot` | `certbot` |
| Plugin Certbot Nginx | `python3-certbot-nginx` | `python3-certbot-nginx` | `python3-certbot-nginx` |
| Plugin Certbot Apache | `python3-certbot-apache` | `python3-certbot-apache` | `python3-certbot-apache` |

### Jerarquía de Excepciones

```python
class GenCerbotError(Exception): ...              # Base
class DNSValidationError(GenCerbotError): ...     # Dominio no resuelve → mensaje accionable
class CertbotError(GenCerbotError): ...           # Error de Certbot → incluye output raw
class ServerConfigError(GenCerbotError): ...      # Error en config del servidor
class SystemCommandError(GenCerbotError): ...     # Fallo de subprocess → incluye exit code y cmd
class DependencyError(GenCerbotError): ...        # Dependencia faltante (Docker, snapd)
class UnsupportedDistroError(GenCerbotError): ... # Distro no reconocida en /etc/os-release
class SudoError(GenCerbotError): ...              # sudo no disponible o comando denegado
```

---

## 6. Seguridad

| Vector | Mitigación |
|---|---|
| Ejecución como root | CLI detecta `EUID == 0` y aborta con mensaje explicativo |
| Escalación de privilegios | `sudo` se antepone solo a comandos específicos y predefinidos en `SystemRunner`; nunca a strings construidos desde input del usuario |
| Inyección en comandos del sistema | Los argumentos del usuario (domain, project_name) se pasan como lista de strings a `subprocess.run`, nunca como `shell=True` |
| Permisos de `acme.json` (Traefik) | Se genera con `os.chmod(path, 0o600)` explícitamente |
| Claves privadas en logs | `SystemRunner` filtra líneas que contienen patrones de claves antes de loguear |
| Inyección en templates | Jinja2 con `autoescape=False` solo para archivos de config, nunca para HTML |
| Email en logs | El email del usuario nunca se loguea a nivel DEBUG ni superior |

---

## 7. Observabilidad

### Logging

La herramienta usa el módulo `logging` estándar de Python. Los logs se escriben a `~/.local/share/gen_cerbot/gen_cerbot.log` con rotación de 7 días.

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

### Salida de consola (stdout)

- `[INFO]` en verde
- `[WARN]` en amarillo
- `[ERROR]` en rojo
- Progreso con spinners (via `rich` o `typer` progress)

---

## 8. Estrategia de Testing

### 8.1 Pirámide de Tests

```
         ▲
        /E2E\          Manual / VM  — happy paths en Ubuntu, Fedora, openSUSE
       /──────\         (Fase 6, Let's Encrypt --staging)
      /  Integ \        pytest + tmp_path — flujos críticos sin red ni sudo real
     /──────────\
    /    Unit    \      pytest + unittest.mock — lógica de negocio aislada
   ──────────────────
```

| Nivel | Target cobertura | Entorno | Herramientas principales |
|---|---|---|---|
| **Unit** | > 85% por módulo | CI / local | `pytest`, `unittest.mock`, `pytest-mock` |
| **Integración** | Flujos críticos (10 escenarios mínimo) | CI / local | `pytest`, `tmp_path`, fixtures estáticas |
| **E2E / Manual** | Happy paths en 3 distros | VM limpia | Entorno real + `--staging` de Let's Encrypt |

### 8.2 Estructura de Directorios de Tests

```
tests/
├── conftest.py                     # Fixtures globales: runner_mock, pkg_manager_mock, tmp_config
├── unit/
│   ├── test_system_runner.py       # SystemRunner: sudo, sin sudo, error de subprocess
│   ├── test_distro_detector.py     # DistroDetector: 3 distros + desconocida
│   ├── test_package_manager.py     # Apt/Dnf/Zypper: install, is_installed, update
│   ├── test_dns_validator.py       # DNSValidator: ok, fallo, skip_dns_check
│   ├── test_cert_registry.py       # CertRegistry: add, list, remove, idempotencia
│   ├── test_template_renderer.py   # TemplateRenderer: nginx, apache por distro, traefik
│   ├── test_nginx_provider.py      # NginxProvider: install, configure, verify, remove
│   ├── test_apache_provider.py     # ApacheProvider: 3 DistroFamily
│   ├── test_traefik_provider.py    # TraefikProvider: generación de compose + acme.json
│   ├── test_certbot_installer.py   # CertbotInstaller: snap, dnf, zypper
│   ├── test_certbot_manager.py     # CertbotManager: certonly, renew, revoke, list
│   ├── test_certbot_service.py     # CertbotService: flujo generate, list, renew, remove
│   ├── test_cli.py                 # CLI Typer: CliRunner por subcomando
│   ├── interactive/
│   │   ├── test_wizard.py          # GenerateWizard: campos, validación, resumen
│   │   ├── test_menu.py            # InteractiveMenu: routing de opciones
│   │   └── test_output.py          # LiveOutputRenderer: indicadores [✔]/[→]/[✗]
│   └── i18n/
│       ├── test_locale_manager.py  # LocaleManager: t(), fallback, interpolación
│       └── test_language_selector.py # LanguageSelector: prompt, persistencia, --lang
├── integration/
│   ├── test_nginx_config_gen.py    # Genera archivo nginx en tmp_path y valida contenido
│   ├── test_apache_config_gen.py   # Genera VirtualHost Apache por distro en tmp_path
│   ├── test_traefik_config_gen.py  # Genera docker-compose.yml + traefik.yml en tmp_path
│   ├── test_certbot_output.py      # Parseo de salida real de `certbot certificates`
│   ├── test_cert_registry_io.py    # Lectura/escritura del JSON registry en disco real
│   └── test_full_flow.py           # CertbotService end-to-end con todos los deps mockeados
└── fixtures/
    ├── os-release/
    │   ├── ubuntu-22.04            # Contenido de /etc/os-release en Ubuntu 22.04
    │   ├── debian-12               # Contenido de /etc/os-release en Debian 12
    │   ├── fedora-40               # Contenido de /etc/os-release en Fedora 40
    │   ├── opensuse-leap-15.5      # Contenido de /etc/os-release en openSUSE Leap
    │   └── unknown-distro          # Distro sin ID conocido (para UnsupportedDistroError)
    ├── certbot-outputs/
    │   ├── certificates_ok.txt     # Salida de `certbot certificates` con 2 certs
    │   ├── certificates_empty.txt  # Salida con "No certificates found"
    │   └── certonly_success.txt    # Salida de `certbot certonly --nginx` exitoso
    └── templates-rendered/
        ├── nginx-site-expected.conf        # Config Nginx esperada para comparar
        ├── apache-debian-expected.conf     # VirtualHost Apache Debian esperado
        ├── apache-redhat-expected.conf     # VirtualHost Apache Fedora esperado
        └── traefik-compose-expected.yml    # docker-compose.yml Traefik esperado
```

### 8.3 Fixtures Globales (`conftest.py`)

```python
@pytest.fixture
def mock_runner(mocker):
    """SystemRunner con subprocess.run mockeado — no ejecuta comandos reales."""
    runner = MagicMock(spec=SystemRunner)
    runner.run.return_value = CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    return runner

@pytest.fixture
def mock_apt(mock_runner):
    """AptPackageManager inyectado con runner mockeado."""
    return AptPackageManager(runner=mock_runner)

@pytest.fixture
def mock_dnf(mock_runner):
    """DnfPackageManager inyectado con runner mockeado."""
    return DnfPackageManager(runner=mock_runner)

@pytest.fixture
def tmp_config(tmp_path):
    """Directorio de configuración temporal para CertRegistry y LocaleManager."""
    config_dir = tmp_path / ".config" / "gen_cerbot"
    config_dir.mkdir(parents=True)
    return config_dir

@pytest.fixture
def ubuntu_os_release(tmp_path):
    """Archivo /etc/os-release para Ubuntu 22.04 en directorio temporal."""
    content = Path("tests/fixtures/os-release/ubuntu-22.04").read_text()
    f = tmp_path / "os-release"
    f.write_text(content)
    return f
```

### 8.4 Estrategia de Mocking por Módulo

| Módulo | Dependencia que se mockea | Método de mock | Qué se verifica |
|---|---|---|---|
| `SystemRunner` | `subprocess.run` | `unittest.mock.patch` | cmd construida, sudo prepended, returncode != 0 → `SystemCommandError` |
| `DistroDetector` | `/etc/os-release` | `tmp_path` + fixture file | DistroFamily correcto para Ubuntu/Fedora/openSUSE/unknown |
| `AptPackageManager` | `SystemRunner` | `MagicMock(spec=SystemRunner)` | cmd incluye `apt-get install -y` + lista de paquetes |
| `DnfPackageManager` | `SystemRunner` | `MagicMock(spec=SystemRunner)` | cmd incluye `dnf install -y` + lista de paquetes |
| `ZypperPackageManager` | `SystemRunner` | `MagicMock(spec=SystemRunner)` | cmd incluye `zypper install -y` + lista de paquetes |
| `NginxProvider` | `PackageManager`, `SystemRunner` | `MagicMock` | `install()` llama `pkg_manager.install(["nginx", ...])`; `verify()` usa `sudo=True` |
| `ApacheProvider` | `PackageManager`, `SystemRunner`, `DistroFamily` | `MagicMock` | nombre de paquete varía por `DistroFamily` (apache2 / httpd); template correcto |
| `TraefikProvider` | `SystemRunner`, `tmp_path` | `MagicMock` + `tmp_path` | archivos generados existen; `acme.json` con permisos 600 |
| `DNSValidator` | `socket.getaddrinfo` | `unittest.mock.patch("socket.getaddrinfo")` | IP coincide → OK; no coincide → `DNSValidationError` con mensaje |
| `CertbotManager` | `SystemRunner` | `MagicMock` | cmd de `certonly` incluye `--nginx`/`--apache`; `certificates` parsea fixture |
| `CertbotInstaller` | `SystemRunner`, `DistroFamily` | `MagicMock` | instala via snap para Debian, dnf para Fedora, zypper para SUSE |
| `CertbotService` | todos los anteriores | múltiples `MagicMock` + `patch` | secuencia de llamadas correcta; propagación de excepciones |
| `GenerateWizard` | `questionary` | `mocker.patch("questionary.text.ask")` + `unsafe_ask` | campos con valores predefinidos; validación rechaza emails inválidos |
| `LiveOutputRenderer` | `rich.Console` | `rich.Console(file=io.StringIO())` | output contiene `[✔]` al completar; `[✗]` al fallar |
| `LocaleManager` | archivos `locales/*.json` | `tmp_path` con JSON custom | `t("clave")` retorna texto correcto; clave inexistente → fallback inglés |
| `LanguageSelector` | `questionary`, `config.toml` | `mocker.patch` + `tmp_config` fixture | persiste lang en TOML; segunda llamada no muestra prompt |
| CLI (Typer) | `CertbotService` | `Typer CliRunner` + `MagicMock` | exit code 0 en happy path; exit code != 0 con flag faltante + `--no-interactive` |

### 8.5 Patrones de Tests de Integración

Los tests de integración verifican la colaboración entre dos o más módulos reales, sin red ni sudo. Usan `tmp_path` para I/O de disco.

**Patrón: generación de archivo de configuración**

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

**Patrón: parseo de salida de Certbot**

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

**Patrón: flujo completo de `generate` con todos los deps mockeados**

```python
def test_certbot_service_generate_full_flow(mock_runner, tmp_path, mocker):
    mocker.patch("socket.getaddrinfo", return_value=[("", "", "", "", ("203.0.113.1", 0))])
    mocker.patch("gen_cerbot.utils.system.get_local_ips", return_value=["203.0.113.1"])
    config = CertificateConfig(domain="app.example.com", ...)

    service = CertbotService(runner=mock_runner, config_dir=tmp_path)
    service.generate(config)

    # Verificar secuencia de llamadas
    calls = [str(c) for c in mock_runner.run.call_args_list]
    assert any("nginx -t" in c for c in calls)
    assert any("certbot" in c for c in calls)
```

### 8.6 Cobertura Mínima por Módulo

| Módulo | Cobertura mínima | Justificación |
|---|---|---|
| `utils/system.py` | 95% | Núcleo de seguridad — sudo granular |
| `utils/distro.py` | 100% | Lógica de detección crítica, pequeño |
| `utils/package_manager.py` | 90% | Las 3 implementaciones deben cubrir install, update, is_installed |
| `utils/dns.py` | 90% | Flujo ok + error + skip deben estar cubiertos |
| `providers/nginx.py` | 85% | install, configure, verify, remove |
| `providers/apache.py` | 85% | Los 3 `DistroFamily` en configure |
| `providers/traefik.py` | 80% | Generación de archivos + chmod |
| `certbot/manager.py` | 85% | certonly, renew, revoke, list, parsing |
| `certbot/installer.py` | 90% | snap, dnf, zypper branches |
| `domain/services.py` | 80% | Flujo principal + manejo de excepciones |
| `interactive/wizard.py` | 80% | Happy path + validación de campos |
| `interactive/output.py` | 75% | Estados [✔] [→] [✗] |
| `i18n/locale_manager.py` | 95% | Fallback, interpolación — crítico para UX |
| `i18n/selector.py` | 85% | prompt, persistencia, --lang override |
| `cli.py` | 75% | Subcomandos principales via CliRunner |

### 8.7 Configuración de pytest y Cobertura

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--strict-markers -v"
markers = [
    "unit: tests unitarios sin I/O real",
    "integration: tests con I/O de disco (tmp_path)",
    "e2e: tests que requieren entorno Linux real con sudo",
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

**Comandos de uso:**

```bash
# Ejecutar solo tests unitarios (sin I/O real)
pytest -m unit

# Ejecutar tests unitarios + integración
pytest -m "unit or integration"

# Ver cobertura por módulo
pytest --cov=src/gen_cerbot --cov-report=term-missing -m "unit or integration"

# Generar reporte HTML de cobertura
pytest --cov=src/gen_cerbot --cov-report=html

# Tests E2E (requieren entorno Linux con sudo)
pytest -m e2e --sudo
```

### 8.8 Dependencias de Testing

```toml
# pyproject.toml — grupo [project.optional-dependencies]
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-mock>=3.12",      # mocker fixture (alternativa a unittest.mock.patch)
    "pytest-cov>=5.0",        # cobertura integrada
    "pytest-asyncio>=0.23",   # por si se usan corutinas en el futuro
    "rich",                   # ya es dependencia de producción
    "typer[all]",             # ya es dependencia de producción
]
```

---

## 9. Empaquetado y Distribución

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

## 10. Preguntas Abiertas

- [ ] ¿Se requiere soporte para Debian en la v1.0 o solo Ubuntu? — Owner: Ernesto, Deadline: antes de Fase 1
- [ ] ¿Se debe generar configuración de renovación automática como cron o como systemd timer? — Owner: Ernesto, Deadline: antes de Fase 4
- [ ] ¿El modo Traefik debe generar un `docker-compose.yml` nuevo o solo los archivos de configuración de Traefik, asumiendo que el usuario ya tiene uno? — Owner: Ernesto, Deadline: antes de Fase 3

---

## Historial de Cambios

| Versión | Fecha | Autor | Cambios |
|---|---|---|---|
| 1.0 | 2026-03-31 | Ernesto Crespo | Versión inicial: arquitectura base Nginx/Apache/Traefik, Provider pattern, Certbot, Typer |
| 1.1 | 2026-03-31 | Ernesto Crespo | Multi-distro: DistroDetector, PackageManager ABC (Apt/Dnf/Zypper), PkgFamily enum, SystemRunner con sudo granular, tabla de mapeo de paquetes por distro, DD-005 PackageManager Strategy, DD-006 sudo granular |
| 1.2 | 2026-03-31 | Ernesto Crespo | Modo interactivo: módulo interactive/ (menu.py, wizard.py, output.py), componentes InteractiveMenu/GenerateWizard/LiveOutputRenderer, diagrama dual-mode actualizado, DD-007 questionary, DD-008 rich.live, CertificateConfig con campo interactive |
| 1.3 | 2026-03-31 | Ernesto Crespo | Soporte i18n: módulo i18n/ (locale_manager.py, selector.py, locales/en.json, es.json), LanguageSelector, LocaleManager, DD-009 JSON locales, flag --lang global, campo lang en CertificateConfig, ejemplo de estructura locale JSON, diagrama de entrada actualizado con capa i18n |
| 1.4 | 2026-03-31 | Ernesto Crespo | Empaquetado nativo: pyproject.toml completo, packaging/debian/, packaging/rpm/gen-cerbot.spec; Sección 9 actualizada con .deb y .rpm |
| 1.5 | 2026-03-31 | Ernesto Crespo | Especificaciones de testing: Sección 8 reescrita con pirámide de tests, estructura tests/, catálogo de fixtures (os-release, certbot-outputs, templates-rendered), conftest.py con fixtures globales, tabla de mock por módulo, patrones de integración, cobertura mínima por módulo, pyproject.toml con pytest/coverage config y dependencias de dev |
