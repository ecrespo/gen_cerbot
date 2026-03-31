# gen_cerbot — Implementation Plan

## Metadata

| Campo | Valor |
|---|---|
| **Autor** | Ernesto Crespo |
| **Estado** | `DRAFT` |
| **Versión** | 1.5 |
| **Fecha** | 2026-03-31 |
| **SPEC** | [SPEC.md](./SPEC.md) |
| **Architecture** | [ARCHITECTURE.md](./ARCHITECTURE.md) |

---

## 1. Resumen de Implementación

La implementación de `gen_cerbot` se divide en **8 fases** (Fase 6 tiene duración de 2 semanas; el resto 1 semana cada una), con un total estimado de 9 semanas. El enfoque es bottom-up: primero se establece la base del proyecto, luego se implementan los providers de servidor web, la integración con Certbot, las operaciones de gestión de certificados, el hardening y los tres formatos de empaquetado (PyPI + .deb + .rpm), el modo interactivo con menú navegable, y finalmente el soporte multi-idioma.

**Duración total estimada:** 9 semanas
**Equipo requerido:** 1 desarrollador Python
**Fecha objetivo de primera release:** 2026-06-02

---

## 2. Pre-requisitos

| Pre-requisito | Owner | Estado | Fecha Límite |
|---|---|---|---|
| SPEC.md aprobado | Ernesto | ☐ Pendiente | 2026-04-07 |
| ARCHITECTURE.md aprobado | Ernesto | ☐ Pendiente | 2026-04-07 |
| Entorno de desarrollo Python 3.11+ | Ernesto | ☐ Pendiente | Fase 1 |
| VM Ubuntu 22.04 para tests E2E | Ernesto | ☐ Pendiente | Fase 4 |
| Cuenta en PyPI (para distribución) | Ernesto | ☐ Pendiente | Fase 6 |
| VM Debian 12 (Bookworm) para build del paquete .deb | Ernesto | ☐ Pendiente | Fase 6 |
| VM Fedora 40 para build del paquete .rpm | Ernesto | ☐ Pendiente | Fase 6 |
| `fakeroot`, `dpkg-dev`, `debhelper>=13`, `dh-python` instalados en VM Debian | Ernesto | ☐ Pendiente | Fase 6 |
| `rpm-build`, `python3-devel`, `rpmlint` instalados en VM Fedora | Ernesto | ☐ Pendiente | Fase 6 |
| Token de API de PyPI para upload con Twine | Ernesto | ☐ Pendiente | Fase 6 |

---

## 3. Fases de Implementación

---

### Fase 1: Foundation & Project Setup

**Duración:** 1 semana
**Objetivo:** Establecer la estructura del proyecto, el CLI esqueleto, los modelos de datos y el sistema de testing.

#### Tareas

| ID | Tarea | Estimación | Dependencia | Estado |
|---|---|---|---|---|
| F1-01 | Crear estructura de directorios del proyecto | 2h | — | ☐ |
| F1-02 | Configurar `pyproject.toml` con dependencias y entry point | 1h | F1-01 | ☐ |
| F1-03 | Configurar ruff, mypy y pre-commit hooks | 1h | F1-02 | ☐ |
| F1-04 | Implementar `core/exceptions.py` con jerarquía completa (incl. `UnsupportedDistroError`, `SudoError`) | 1h | F1-01 | ☐ |
| F1-05 | Implementar `core/config.py` con pydantic-settings | 2h | F1-01 | ☐ |
| F1-06 | Implementar `domain/models.py` (CertificateConfig, ServerType, DistroFamily, CertificateRecord) | 2h | F1-04 | ☐ |
| F1-07 | Implementar `utils/system.py` (SystemRunner con `run(cmd, sudo=False)` — antepone `["sudo"]` cuando `sudo=True`) | 3h | F1-04 | ☐ |
| F1-08 | Implementar `utils/distro.py` (DistroDetector: lee `/etc/os-release` → `DistroFamily`) | 2h | F1-06 | ☐ |
| F1-09 | Implementar `utils/package_manager.py` (PackageManager ABC + AptPackageManager + DnfPackageManager + ZypperPackageManager + Factory) | 4h | F1-07, F1-08 | ☐ |
| F1-10 | Implementar `utils/registry.py` (CertRegistry JSON) | 2h | F1-06 | ☐ |
| F1-11 | Implementar `utils/templates.py` (Jinja2 renderer) | 2h | F1-01 | ☐ |
| F1-12 | Crear CLI esqueleto con Typer: subcomandos `generate`, `list`, `renew`, `remove` (stubs) | 3h | F1-06 | ☐ |
| F1-13 | Configurar pytest con fixtures base y estructura de tests | 2h | F1-07 | ☐ |
| F1-14 | Unit tests: SystemRunner (verificar anteponer sudo), DistroDetector (mock /etc/os-release), PackageManager (3 implementaciones) | 4h | F1-07, F1-08, F1-09 | ☐ |
| F1-15 | Unit tests: CertRegistry, TemplateRenderer | 2h | F1-10, F1-11 | ☐ |

#### Criterios de "Done"

- [ ] `gen-cerbot --help` funciona y muestra todos los subcomandos
- [ ] `gen-cerbot generate --help` muestra todos los flags documentados
- [ ] `DistroDetector` detecta correctamente Ubuntu, Fedora y openSUSE con fixtures de `/etc/os-release`
- [ ] `PackageManager` genera el comando correcto con `sudo` para cada distro
- [ ] `SystemRunner.run(cmd, sudo=True)` antepone `["sudo"]` verificado en tests
- [ ] Tests unitarios de utils pasan con `pytest`
- [ ] `ruff check .` y `mypy .` sin errores
- [ ] `pyproject.toml` instalable con `pip install -e .`

---

### Fase 2: Nginx Provider

**Duración:** 1 semana
**Objetivo:** Implementar el Provider de Nginx con generación de configuración, instalación y validación.

#### Tareas

| ID | Tarea | Estimación | Dependencia | Estado |
|---|---|---|---|---|
| F2-01 | Implementar `providers/base.py` (ServerProvider ABC — recibe `PackageManager` en constructor) | 2h | F1-06 | ☐ |
| F2-02 | Crear plantilla Jinja2 `templates/nginx/site.conf.j2` | 2h | F1-11 | ☐ |
| F2-03 | Implementar `providers/nginx.py`: método `install()` usando `pkg_manager.install(["nginx"])` con sudo | 2h | F2-01, F1-09 | ☐ |
| F2-04 | Implementar `providers/nginx.py`: método `configure()` — genera config y activa sitio (symlink en Debian, include en Fedora/SUSE) | 3h | F2-02, F2-03 | ☐ |
| F2-05 | Implementar `providers/nginx.py`: método `verify()` — `runner.run(["nginx", "-t"], sudo=True)` | 1h | F2-04 | ☐ |
| F2-06 | Implementar `providers/nginx.py`: método `remove()` | 2h | F2-04 | ☐ |
| F2-07 | Implementar `providers/factory.py` (ProviderFactory.get(server_type, pkg_manager)) | 1h | F2-01 | ☐ |
| F2-08 | Unit tests: NginxProvider con PackageManager y SystemRunner mockeados (verificar llamadas sudo) | 4h | F2-06 | ☐ |
| F2-09 | Integration test: generación de archivo de configuración con tmp_path | 2h | F2-04 | ☐ |
| F2-10 | Validar que la plantilla Nginx generada es sintácticamente válida | 1h | F2-02 | ☐ |

#### Criterios de "Done"

- [ ] `NginxProvider` implementa todos los métodos de `ServerProvider`
- [ ] `NginxProvider` recibe `PackageManager` por inyección (no lo instancia directamente)
- [ ] La plantilla Nginx genera configuración válida (con reverse proxy, headers y timeouts del script original)
- [ ] Tests de `NginxProvider` pasan con PackageManager y SystemRunner mockeados
- [ ] Tests verifican que `install()` llama `pkg_manager.install()` y que `verify()` usa `sudo=True`
- [ ] Cobertura de tests en `providers/nginx.py` > 80%

---

### Fase 3: Apache y Traefik Providers

**Duración:** 1 semana
**Objetivo:** Implementar los Providers de Apache y Traefik.

#### Tareas

| ID | Tarea | Estimación | Dependencia | Estado |
|---|---|---|---|---|
| F3-01 | Crear plantillas Jinja2 Apache: `vhost-debian.conf.j2`, `vhost-redhat.conf.j2`, `vhost-suse.conf.j2` | 3h | F1-11 | ☐ |
| F3-02 | Implementar `providers/apache.py`: método `install()` — paquetes por distro via `pkg_manager`, `sudo a2enmod` en Debian o módulos via conf en Fedora/SUSE | 3h | F2-01, F1-09 | ☐ |
| F3-03 | Implementar `providers/apache.py`: método `configure()` — selecciona template según distro + `verify()` (`sudo apachectl -t`) | 3h | F3-01, F3-02 | ☐ |
| F3-04 | Implementar `providers/apache.py`: método `remove()` (`sudo a2dissite` en Debian; `rm` config en Fedora/SUSE) | 2h | F3-03 | ☐ |
| F3-05 | Unit tests: ApacheProvider con PackageManager y SystemRunner mockeados — verificar comportamiento correcto para cada `DistroFamily` | 4h | F3-04 | ☐ |
| F3-06 | Crear plantillas Jinja2 para Traefik: `docker-compose.yml.j2` y `traefik.yml.j2` | 3h | F1-11 | ☐ |
| F3-07 | Implementar `providers/traefik.py`: método `install()` (verifica Docker — distro-agnostic) | 1h | F2-01, F1-07 | ☐ |
| F3-08 | Implementar `providers/traefik.py`: método `configure()` (genera archivos + `acme.json` con `chmod 600`) | 3h | F3-06, F3-07 | ☐ |
| F3-09 | Implementar `providers/traefik.py`: método `verify()` (`docker compose config` sin sudo) | 1h | F3-08 | ☐ |
| F3-10 | Implementar `providers/traefik.py`: método `remove()` | 1h | F3-08 | ☐ |
| F3-11 | Unit tests: TraefikProvider con SystemRunner mockeado | 3h | F3-10 | ☐ |
| F3-12 | Registrar Apache y Traefik en ProviderFactory (con pkg_manager) | 1h | F3-04, F3-10, F2-07 | ☐ |

#### Criterios de "Done"

- [ ] Los tres providers están registrados en `ProviderFactory`
- [ ] `ApacheProvider` selecciona el template correcto según `DistroFamily`
- [ ] Tests de `ApacheProvider` cubren los 3 `DistroFamily` con PackageManager mockeado
- [ ] Tests de `TraefikProvider` pasan con SystemRunner mockeado
- [ ] La plantilla Traefik generada es un YAML válido
- [ ] Las 3 plantillas Apache generan configuración válida para su distro
- [ ] `acme.json` se crea con permisos 600 en `TraefikProvider`

---

### Fase 4: Certbot Manager e Integración DNS

**Duración:** 1 semana
**Objetivo:** Implementar la integración completa con Certbot y la validación DNS.

#### Tareas

| ID | Tarea | Estimación | Dependencia | Estado |
|---|---|---|---|---|
| F4-01 | Implementar `utils/dns.py`: resolución DNS y comparación contra IPs locales | 3h | F1-07 | ☐ |
| F4-02 | Unit tests: DNSValidator con socket.getaddrinfo mockeado | 2h | F4-01 | ☐ |
| F4-03 | Implementar `certbot/installer.py`: instalar Certbot según distro — snap (DEBIAN), `dnf install certbot` (REDHAT), `zypper install certbot` (SUSE) — usando `pkg_manager` + `sudo` | 4h | F1-09, F1-07 | ☐ |
| F4-04 | Implementar `certbot/manager.py`: método `request()` — `runner.run(["certbot", ...], sudo=True)` | 3h | F4-03, F1-07 | ☐ |
| F4-05 | Implementar `certbot/manager.py`: método `renew()` y `renew_all()` | 2h | F4-04 | ☐ |
| F4-06 | Implementar `certbot/manager.py`: método `revoke()` y `delete()` | 2h | F4-04 | ☐ |
| F4-07 | Implementar `certbot/manager.py`: método `get_certificates()` (parseo de certbot certificates) | 3h | F4-04 | ☐ |
| F4-08 | Unit tests: CertbotManager con fixtures de output de Certbot (staging/prod) | 4h | F4-07 | ☐ |
| F4-09 | Implementar `domain/services.py`: `CertbotService.generate()` — incluye paso de detección de distro + construcción de PackageManager antes de crear el Provider | 5h | F4-04, F4-01, F2-07 | ☐ |
| F4-10 | Implementar soporte `--dry-run` en CertbotService y en todos los Providers | 2h | F4-09 | ☐ |
| F4-11 | Implementar soporte `--staging` en CertbotManager | 1h | F4-04 | ☐ |

#### Criterios de "Done"

- [ ] DNSValidator detecta correctamente cuando el dominio no resuelve
- [ ] CertbotManager.request() funciona con `--staging` (verificado en VM)
- [ ] El flujo completo `CertbotService.generate()` pasa tests unitarios con todos los componentes mockeados
- [ ] `--dry-run` no ejecuta ningún comando del sistema real

---

### Fase 5: Subcomandos CLI Completos

**Duración:** 1 semana
**Objetivo:** Implementar los subcomandos `generate`, `list`, `renew` y `remove` completamente funcionales.

#### Tareas

| ID | Tarea | Estimación | Dependencia | Estado |
|---|---|---|---|---|
| F5-01 | Implementar subcomando `generate` en `cli.py` con todos los flags | 3h | F4-09 | ☐ |
| F5-02 | Implementar subcomando `list` en `cli.py` con tabla rich | 3h | F4-07, F1-08 | ☐ |
| F5-03 | Implementar `CertbotService.renew()` | 2h | F4-05 | ☐ |
| F5-04 | Implementar subcomando `renew` en `cli.py` | 1h | F5-03 | ☐ |
| F5-05 | Implementar `CertbotService.remove()` | 3h | F4-06 | ☐ |
| F5-06 | Implementar subcomando `remove` en `cli.py` con confirmación interactiva | 2h | F5-05 | ☐ |
| F5-07 | Implementar output con colores y spinners de progreso (rich) | 2h | F5-01 | ☐ |
| F5-08 | Implementar logging a archivo `~/.local/share/gen_cerbot/gen_cerbot.log` | 2h | F5-01 | ☐ |
| F5-09 | Unit tests: subcomandos CLI con Typer CliRunner | 4h | F5-06 | ☐ |
| F5-10 | Revisar y completar `--help` de todos los subcomandos y flags | 1h | F5-06 | ☐ |

#### Criterios de "Done"

- [ ] Los 4 subcomandos están implementados y funcionales
- [ ] `gen-cerbot list` muestra estado con colores (verde/amarillo/rojo)
- [ ] `gen-cerbot remove` pide confirmación antes de ejecutar
- [ ] Logging a archivo funciona correctamente
- [ ] Tests de CLI pasan con CliRunner
- [ ] `gen-cerbot --help` y cada subcomando tienen documentación completa

---

### Fase 6: Testing, Hardening y Empaquetado

**Duración:** 2 semanas
**Objetivo:** Alcanzar cobertura de tests > 80%, probar en entorno real (staging Let's Encrypt), y distribuir la herramienta en tres formatos: wheel en PyPI, paquete nativo `.deb` para Debian/Ubuntu, y paquete nativo `.rpm` para Fedora/openSUSE.

#### Tareas — Semana 1: Testing y Hardening

| ID | Tarea | Estimación | Dependencia | Estado |
|---|---|---|---|---|
| F6-01 | Revisar cobertura con `pytest --cov` y completar tests faltantes hasta > 80% | 4h | F5-09 | ☐ |
| F6-02 | Test E2E en VM Ubuntu 22.04: flujo Nginx + Apache + Traefik con `--staging` | 3h | F5-01 | ☐ |
| F6-03 | Test E2E en VM Fedora 40: flujo Nginx + Apache con `--staging` (verificar `dnf` y `sudo`) | 3h | F5-01 | ☐ |
| F6-04 | Test E2E en VM openSUSE Leap 15.5: flujo Nginx con `--staging` (verificar `zypper` y `sudo`) | 3h | F5-01 | ☐ |
| F6-05 | Revisar y fortalecer manejo de errores: mensajes claros para distro no soportada, sudo denegado y puerto 80 ocupado | 3h | F5-09 | ☐ |
| F6-06 | Verificar que el CLI rechaza ejecución como root (EUID check) en las 3 distros | 1h | F5-01 | ☐ |
| F6-07 | Verificar que claves privadas no aparecen en logs ni stdout | 1h | F5-08 | ☐ |
| F6-08 | Agregar fixtures de `/etc/os-release` para Ubuntu, Fedora y openSUSE en `tests/fixtures/` | 1h | F6-01 | ☐ |
| F6-09 | Configurar GitHub Actions CI: tests unitarios + matriz Ubuntu 22.04/24.04 + Fedora 40 (push/PR) | 3h | F6-01 | ☐ |

#### Tareas — Semana 2: Empaquetado PyPI + .deb + .rpm

**PyPI (wheel)**

| ID | Tarea | Estimación | Dependencia | Estado |
|---|---|---|---|---|
| F6-10 | Completar `pyproject.toml`: classifiers, `project.urls`, `project.scripts`, dependencias con rangos de versión | 2h | F6-01 | ☐ |
| F6-11 | Instalar `python-build` y `twine`; ejecutar `python -m build` → verificar `.whl` + `.tar.gz` en `dist/` | 1h | F6-10 | ☐ |
| F6-12 | Publicar en TestPyPI (`twine upload --repository testpypi dist/*`) y verificar instalación con `pip install --index-url https://test.pypi.org/simple/ gen-cerbot` | 1h | F6-11 | ☐ |
| F6-13 | Publicar release v1.0.0 en PyPI (`twine upload dist/*`) y verificar con `pip install gen-cerbot` desde cero | 1h | F6-12 | ☐ |
| F6-14 | Configurar GitHub Actions `release.yml`: en `push tag v*` → `python -m build` + `twine upload` automático | 2h | F6-13 | ☐ |

**Paquete Debian/Ubuntu (.deb)**

| ID | Tarea | Estimación | Dependencia | Estado |
|---|---|---|---|---|
| F6-15 | Crear directorio `packaging/debian/` con los archivos base: `control`, `rules`, `changelog`, `compat`, `copyright`, `install` | 2h | F6-10 | ☐ |
| F6-16 | Escribir `packaging/debian/control`: `Package: gen-cerbot`, `Architecture: all`, `Depends: python3 (>= 3.11), python3-pip`, `Description` multi-línea | 1h | F6-15 | ☐ |
| F6-17 | Escribir `packaging/debian/rules` con `dh $@` y target `override_dh_auto_install` que instala con `pip install --prefix=/usr --no-deps .` | 2h | F6-15 | ☐ |
| F6-18 | Escribir `packaging/debian/changelog` en formato Debian (`dch --create`) con versión inicial `1.0.0-1` | 1h | F6-15 | ☐ |
| F6-19 | Escribir `packaging/debian/copyright` en formato DEP-5 con licencia del proyecto | 1h | F6-15 | ☐ |
| F6-20 | Build del `.deb` en VM Debian 12: `dpkg-buildpackage -us -uc -b` → verificar generación de `gen-cerbot_1.0.0-1_all.deb` | 2h | F6-17, F6-18 | ☐ |
| F6-21 | Validar el paquete con `lintian --no-tag-display-limit gen-cerbot_*.deb` — resolver errores graves | 2h | F6-20 | ☐ |
| F6-22 | Test de instalación en VM Ubuntu 22.04 limpia: `sudo dpkg -i gen-cerbot_*.deb && gen-cerbot --version` | 1h | F6-21 | ☐ |
| F6-23 | Test de desinstalación limpia: `sudo apt remove gen-cerbot` no deja archivos residuales | 1h | F6-22 | ☐ |
| F6-24 | Agregar step en `release.yml` para build del `.deb` y upload a GitHub Releases como artefacto | 2h | F6-14, F6-21 | ☐ |

**Paquete RPM para Fedora/openSUSE (.rpm)**

| ID | Tarea | Estimación | Dependencia | Estado |
|---|---|---|---|---|
| F6-25 | Crear `packaging/rpm/gen-cerbot.spec` con cabecera completa: `Name`, `Version`, `Release`, `Summary`, `License`, `BuildArch: noarch`, `URL`, `Source0` | 2h | F6-10 | ☐ |
| F6-26 | Definir sección `%description` y `Requires: python3 >= 3.11` en el `.spec`; agregar `BuildRequires: python3-pip python3-build` | 1h | F6-25 | ☐ |
| F6-27 | Implementar secciones `%prep` (descomprimir tarball), `%build` (vacío para paquete puro Python), `%install` (`pip install --prefix=%{buildroot}/usr --no-deps .`) en el `.spec` | 2h | F6-26 | ☐ |
| F6-28 | Implementar sección `%files` en el `.spec`: `/usr/bin/gen-cerbot`, `/usr/lib/python3*/site-packages/gen_cerbot*`; agregar `%license LICENSE`, `%doc README.md` | 2h | F6-27 | ☐ |
| F6-29 | Build del `.rpm` en VM Fedora 40: configurar `~/rpmbuild/` con `rpmdev-setuptree`, copiar tarball a `SOURCES/`, ejecutar `rpmbuild -bb packaging/rpm/gen-cerbot.spec` | 2h | F6-28 | ☐ |
| F6-30 | Validar el paquete con `rpmlint gen-cerbot-*.noarch.rpm` — resolver errores graves | 2h | F6-29 | ☐ |
| F6-31 | Test de instalación en VM Fedora 40 limpia: `sudo dnf install ./gen-cerbot-*.rpm && gen-cerbot --version` | 1h | F6-30 | ☐ |
| F6-32 | Test de instalación en VM openSUSE Leap 15.5: `sudo zypper install ./gen-cerbot-*.rpm && gen-cerbot --version` | 1h | F6-30 | ☐ |
| F6-33 | Test de desinstalación: `sudo dnf remove gen-cerbot` y `sudo zypper remove gen-cerbot` en sus respectivas VMs | 1h | F6-31, F6-32 | ☐ |
| F6-34 | Agregar step en `release.yml` para build del `.rpm` y upload a GitHub Releases como artefacto | 2h | F6-24, F6-30 | ☐ |

#### Estructura de archivos de packaging generada

```
packaging/
├── debian/
│   ├── changelog       # Historia de versiones en formato Debian
│   ├── compat          # Nivel de compatibilidad debhelper (13)
│   ├── control         # Metadatos del paquete y dependencias
│   ├── copyright       # Licencia en formato DEP-5
│   ├── install         # Lista de archivos a incluir en el paquete
│   └── rules           # Script de build (Makefile con dh helper)
└── rpm/
    └── gen-cerbot.spec # Spec file completo para rpmbuild
```

#### Criterios de "Done"

- [ ] `pytest --cov` reporta cobertura > 80%
- [ ] Tests E2E pasan en Ubuntu 22.04 (staging), Fedora 40 y openSUSE Leap 15.5
- [ ] `pip install gen-cerbot` funciona desde PyPI — `gen-cerbot --version` OK
- [ ] `pip install gen-cerbot` funciona desde TestPyPI antes de la publicación final
- [ ] `python -m build` genera `.whl` + `.tar.gz` sin errores
- [ ] `sudo dpkg -i gen-cerbot_*.deb && gen-cerbot --version` funciona en Ubuntu 22.04 limpia
- [ ] `lintian gen-cerbot_*.deb` sin errores graves (nivel E)
- [ ] `sudo dnf install ./gen-cerbot-*.rpm && gen-cerbot --version` funciona en Fedora 40 limpia
- [ ] `sudo zypper install ./gen-cerbot-*.rpm && gen-cerbot --version` funciona en openSUSE Leap 15.5
- [ ] `rpmlint gen-cerbot-*.rpm` sin errores graves
- [ ] GitHub Releases v1.0.0 contiene `.whl`, `.tar.gz`, `.deb` y `.rpm` como artefactos
- [ ] `release.yml` automatiza build y upload de los 4 artefactos en cada tag `v*`
- [ ] CI verde en GitHub Actions para Ubuntu 22.04, 24.04 y Fedora 40

---

### Fase 7: Modo Interactivo

**Duración:** 1 semana
**Objetivo:** Implementar el modo interactivo con menú principal, asistente guiado para generar certificados y salida de ejecución en tiempo real.

#### Tareas

| ID | Tarea | Estimación | Dependencia | Estado |
|---|---|---|---|---|
| F7-01 | Agregar `questionary>=2.0` a `pyproject.toml` y verificar compatibilidad con Typer/rich | 1h | F5-01 | ☐ |
| F7-02 | Implementar `interactive/output.py` (LiveOutputRenderer): captura stdout de SystemRunner y lo renderiza con `rich.live` mostrando `[✔]`/`[→]`/`[✗]` por paso | 4h | F5-08 | ☐ |
| F7-03 | Implementar `interactive/wizard.py` (GenerateWizard): solicita en secuencia subdominio, puerto, pkg-family (`deb`/`rpm`), servidor web, email y nombre de proyecto; valida cada campo en línea | 4h | F7-01 | ☐ |
| F7-04 | Agregar pantalla de resumen y confirmación `¿Continuar?` al final del GenerateWizard | 1h | F7-03 | ☐ |
| F7-05 | Implementar `interactive/menu.py` (InteractiveMenu): menú principal con las 5 opciones (Generar, Listar, Renovar, Eliminar, Salir); navegación con flechas y Enter | 3h | F7-03 | ☐ |
| F7-06 | Modificar `cli.py`: detectar invocación sin argumentos → lanzar `InteractiveMenu.run()`; con argumentos → comportamiento Typer existente | 2h | F7-05 | ☐ |
| F7-07 | Agregar flag `--no-interactive` a `generate` para deshabilitar prompts en CI/CD (falla si falta parámetro requerido) | 1h | F7-06 | ☐ |
| F7-08 | Agregar flag `--pkg-family deb\|rpm` a `generate` para especificar la familia desde línea de comandos | 1h | F7-06 | ☐ |
| F7-09 | Conectar LiveOutputRenderer con CertbotService: cada paso del flujo emite eventos que el renderer recoge y muestra | 3h | F7-02, F5-01 | ☐ |
| F7-10 | Manejo de errores en modo interactivo: `[✗]` con mensaje + opción "Reintentar / Volver al menú" | 2h | F7-05, F7-09 | ☐ |
| F7-11 | Manejo de `Ctrl+C` en modo interactivo: salida limpia con mensaje | 1h | F7-05 | ☐ |
| F7-12 | Unit tests: GenerateWizard con respuestas mockeadas via `questionary`'s `unsafe_ask` | 3h | F7-04 | ☐ |
| F7-13 | Unit tests: InteractiveMenu con navegación simulada | 2h | F7-05 | ☐ |
| F7-14 | Unit tests: LiveOutputRenderer con `rich.Console(file=io.StringIO())` | 2h | F7-02 | ☐ |
| F7-15 | Test manual E2E del flujo completo modo interactivo en terminal real (Ubuntu + Fedora) | 2h | F7-10 | ☐ |

#### Criterios de "Done"

- [ ] `gen-cerbot` sin argumentos muestra el menú principal navegable
- [ ] El asistente solicita los 6 campos (subdominio, puerto, pkg-family, servidor, email, proyecto) con validación
- [ ] La selección `deb`/`rpm` determina el PackageManager usado internamente
- [ ] La pantalla de resumen muestra todos los valores antes de ejecutar
- [ ] La salida en tiempo real muestra cada paso con `[✔]`/`[→]`/`[✗]`
- [ ] Los comandos `sudo` ejecutados son visibles en pantalla
- [ ] `Ctrl+C` termina limpiamente sin stack trace
- [ ] `gen-cerbot generate --no-interactive ...` funciona para CI/CD
- [ ] Tests del módulo `interactive/` pasan sin terminal real (mocks de questionary)
- [ ] El modo interactivo funciona correctamente en Ubuntu 22.04 y Fedora 40

---

### Fase 8: Soporte Multi-idioma (i18n)

**Duración:** 1 semana
**Objetivo:** Implementar el sistema de internacionalización con `LocaleManager`, archivos de locale JSON, selector de idioma previo al menú, flag `--lang` y persistencia de la preferencia del usuario.

#### Tareas

| ID | Tarea | Estimación | Dependencia | Estado |
|---|---|---|---|---|
| F8-01 | Crear módulo `i18n/` con `__init__.py`; agregar dependencias (ninguna extra — solo stdlib `json` + `tomllib`/`tomli`) | 1h | F7-01 | ☐ |
| F8-02 | Implementar `i18n/locale_manager.py` (singleton `LocaleManager`): `set_lang(code)`, `t(key, **kwargs)` con interpolación `str.format_map`, fallback a `en` si clave no existe | 3h | F8-01 | ☐ |
| F8-03 | Crear `i18n/locales/en.json` con todas las cadenas de la interfaz interactiva en inglés (~40 claves: menu, wizard, output, errors) | 2h | F8-02 | ☐ |
| F8-04 | Crear `i18n/locales/es.json` con la traducción al español de todas las claves definidas en `en.json` | 2h | F8-03 | ☐ |
| F8-05 | Implementar `i18n/selector.py` (LanguageSelector): leer lang de `config.toml`; si no existe → prompt `questionary.select` con opciones "English / Español"; guardar selección en `config.toml` | 3h | F8-02 | ☐ |
| F8-06 | Modificar `cli.py`: agregar flag global `--lang <code>` (Typer callback); si presente → `LocaleManager.set_lang(code)` y omitir selector; integrar `LanguageSelector.resolve()` antes de `InteractiveMenu.run()` | 2h | F8-05 | ☐ |
| F8-07 | Reemplazar todos los strings hardcoded en `interactive/menu.py`, `interactive/wizard.py` e `interactive/output.py` por llamadas a `LocaleManager.t("clave")` | 3h | F8-06 | ☐ |
| F8-08 | Agregar `SupportedLang` enum a `domain/models.py`; añadir campo `lang: str = "en"` a `CertificateConfig` | 1h | F8-02 | ☐ |
| F8-09 | Leer/escribir preferencia de idioma en `~/.config/gen_cerbot/config.toml` via `core/config.py` | 2h | F8-05 | ☐ |
| F8-10 | Unit tests: `LocaleManager` — fallback a `en` para clave inexistente, interpolación `{variable}`, cambio de idioma en runtime | 3h | F8-04 | ☐ |
| F8-11 | Unit tests: `LanguageSelector` — mock `config.toml` existente, mock `questionary`, verificar persistencia | 2h | F8-05 | ☐ |
| F8-12 | Test manual E2E: `gen-cerbot` sin args muestra selector de idioma → seleccionar `es` → menú en español; segunda ejecución no muestra selector | 1h | F8-07 | ☐ |
| F8-13 | Test manual: `gen-cerbot --lang en` y `gen-cerbot --lang es` omiten selector y muestran el menú en el idioma correspondiente | 1h | F8-06 | ☐ |

#### Criterios de "Done"

- [ ] `gen-cerbot` sin args (primera ejecución) muestra selector de idioma antes del menú
- [ ] Al seleccionar un idioma, todas las cadenas del menú y asistente se muestran en ese idioma
- [ ] La preferencia queda guardada en `config.toml`; sesiones posteriores no muestran el selector
- [ ] `gen-cerbot --lang es` fuerza el idioma sin selector
- [ ] Clave inexistente en `es.json` → fallback transparente al texto en inglés
- [ ] Interpolación de variables funciona: `t("output.done", domain="app.example.com")`
- [ ] Tests del módulo `i18n/` pasan con cobertura > 90%

---

## 4. Mapa de Dependencias

```
Fase 1: Foundation & Setup
  │
  ├──▶ Fase 2: Nginx Provider
  │       │
  │       └──▶ Fase 3: Apache + Traefik Providers
  │                 │
  ├──▶ Fase 4: Certbot Manager + DNS ◀───────────┘
  │       │
  │       └──▶ Fase 5: CLI Subcomandos Completos
  │                 │
  │                 ├──▶ Fase 6: Testing, Hardening & PyPI
  │                 │
  └─────────────────└──▶ Fase 7: Modo Interactivo
                               │
                               └──▶ Fase 8: Soporte i18n
```

---

## 5. Riesgos de Implementación

| Riesgo | Probabilidad | Impacto | Mitigación | Owner |
|---|---|---|---|---|
| Rate limit de Let's Encrypt en pruebas | Alta | Medio | Siempre usar `--staging` en desarrollo; tests unitarios con mocks | Ernesto |
| Diferencias de comportamiento Certbot entre distros (snap vs dnf vs zypper) | Alta | Alto | Tests E2E en 3 VMs; CertbotInstaller abstrae la instalación por distro | Ernesto |
| Nombre de paquetes diferente entre distros | Media | Medio | Mapeo explícito en cada implementación de PackageManager; tests con paquetes reales en VMs | Ernesto |
| sudo con password interactivo en CI | Media | Alto | Configurar `NOPASSWD` en sudoers del runner de CI; documentar requisito | Ernesto |
| Cambios en output de `certbot certificates` (parsing) | Baja | Medio | Tests con fixtures de output real; versión mínima de Certbot fijada | Ernesto |
| Puerto 80 ocupado en entorno de test E2E | Media | Medio | Documentar pre-requisitos del entorno de test; usar VMs limpias | Ernesto |
| Complejidad de casos edge en configuración Traefik | Media | Medio | Iterar con casos reales; dejar preguntas abiertas de ARCHITECTURE.md resueltas antes de Fase 3 | Ernesto |
| Terminal sin soporte ANSI (SSH headless) | Media | Medio | questionary y rich degradan gracefully; agregar flag `--no-interactive` para estos casos | Ernesto |
| Tests de modo interactivo sin terminal real | Media | Medio | Usar `questionary`'s `unsafe_ask` con fixtures; `rich.Console(file=StringIO())` para capturar output | Ernesto |
| Traducciones incompletas en `es.json` generan UX rota | Baja | Medio | Fallback automático a clave `en` en `LocaleManager.t()`; CI verifica que `es.json` tenga todas las claves de `en.json` | Ernesto |

---

## 6. Definición de Done (Global)

- [ ] Código implementado, testeado y mergeado a `main`
- [ ] Tests unitarios e integración pasan (`pytest`)
- [ ] `ruff check .` sin errores
- [ ] `mypy .` sin errores (strict mode)
- [ ] Cobertura de tests > 80% (`pytest --cov`)
- [ ] Documentación actualizada (README.md, --help de cada subcomando, mockup del menú en README)
- [ ] Modo interactivo funcional: menú, asistente y salida en tiempo real verificados manualmente
- [ ] `gen-cerbot` sin args abre menú; con args funciona como comando directo
- [ ] Selector de idioma aparece en primera ejecución; preferencia persistida en `config.toml`
- [ ] `gen-cerbot --lang es` y `gen-cerbot --lang en` funcionan correctamente
- [ ] Todos los textos interactivos usan `LocaleManager.t("clave")` — cero strings hardcoded
- [ ] `pip install gen-cerbot` funciona desde PyPI
- [ ] `sudo dpkg -i gen-cerbot_*.deb && gen-cerbot --version` OK en Ubuntu 22.04
- [ ] `sudo dnf install ./gen-cerbot-*.rpm && gen-cerbot --version` OK en Fedora 40
- [ ] `sudo zypper install ./gen-cerbot-*.rpm && gen-cerbot --version` OK en openSUSE Leap 15.5
- [ ] GitHub Releases v1.0.0 contiene `.whl`, `.tar.gz`, `.deb` y `.rpm`
- [ ] Tests E2E manuales pasando en VM Ubuntu 22.04
- [ ] SPEC.md y ARCHITECTURE.md actualizados si hubo cambios durante la implementación
- [ ] Sin `TODO` ni `FIXME` sin ticket correspondiente en el código

---

## 7. Catálogo de Casos de Prueba

Catálogo de referencia de todos los tests requeridos. Sirve como contrato entre el diseño (ARCHITECTURE.md §8) y la implementación. Cada caso de prueba corresponde a un test function en el archivo indicado.

### 7.1 Tests Unitarios — `utils/`

| ID | Archivo | Test | Entrada / Escenario | Resultado esperado | Mock |
|---|---|---|---|---|---|
| TC-001 | `test_system_runner.py` | `test_run_prepends_sudo` | `run(["nginx", "-t"], sudo=True)` | `subprocess.run` llamado con `["sudo", "nginx", "-t"]` | `subprocess.run` |
| TC-002 | `test_system_runner.py` | `test_run_without_sudo` | `run(["ls"], sudo=False)` | `subprocess.run` llamado con `["ls"]` (sin sudo) | `subprocess.run` |
| TC-003 | `test_system_runner.py` | `test_run_nonzero_raises` | `subprocess.run` retorna `returncode=1` | Lanza `SystemCommandError` con exit code y cmd | `subprocess.run` |
| TC-004 | `test_system_runner.py` | `test_run_captures_stdout` | `subprocess.run` retorna `stdout="output"` | `result.stdout == "output"` | `subprocess.run` |
| TC-005 | `test_distro_detector.py` | `test_detect_ubuntu_2204` | fixture `ubuntu-22.04` en `tmp_path` | `DistroFamily.DEBIAN` | `/etc/os-release` via `tmp_path` |
| TC-006 | `test_distro_detector.py` | `test_detect_debian_12` | fixture `debian-12` en `tmp_path` | `DistroFamily.DEBIAN` | `/etc/os-release` via `tmp_path` |
| TC-007 | `test_distro_detector.py` | `test_detect_fedora_40` | fixture `fedora-40` en `tmp_path` | `DistroFamily.REDHAT` | `/etc/os-release` via `tmp_path` |
| TC-008 | `test_distro_detector.py` | `test_detect_opensuse_leap` | fixture `opensuse-leap-15.5` en `tmp_path` | `DistroFamily.SUSE` | `/etc/os-release` via `tmp_path` |
| TC-009 | `test_distro_detector.py` | `test_detect_unknown_raises` | fixture `unknown-distro` en `tmp_path` | Lanza `UnsupportedDistroError` | `/etc/os-release` via `tmp_path` |
| TC-010 | `test_package_manager.py` | `test_apt_install_cmd` | `apt.install(["nginx", "certbot"])` | cmd contiene `apt-get install -y nginx certbot` con sudo | `SystemRunner` mock |
| TC-011 | `test_package_manager.py` | `test_dnf_install_cmd` | `dnf.install(["httpd"])` | cmd contiene `dnf install -y httpd` con sudo | `SystemRunner` mock |
| TC-012 | `test_package_manager.py` | `test_zypper_install_cmd` | `zypper.install(["nginx"])` | cmd contiene `zypper install -y nginx` con sudo | `SystemRunner` mock |
| TC-013 | `test_package_manager.py` | `test_is_installed_no_sudo` | `apt.is_installed("nginx")` | cmd no contiene sudo | `SystemRunner` mock |
| TC-014 | `test_dns_validator.py` | `test_dns_ok` | `socket.getaddrinfo` retorna IP del servidor | No lanza excepción | `socket.getaddrinfo` |
| TC-015 | `test_dns_validator.py` | `test_dns_mismatch_raises` | `getaddrinfo` retorna IP distinta a la local | Lanza `DNSValidationError` con IPs en mensaje | `socket.getaddrinfo` |
| TC-016 | `test_dns_validator.py` | `test_skip_dns_check_bypasses` | `CertificateConfig(skip_dns_check=True)` | No llama `socket.getaddrinfo` | `socket.getaddrinfo` (no llamado) |
| TC-017 | `test_cert_registry.py` | `test_add_creates_entry` | `registry.add(record)` en `tmp_config` | JSON en disco contiene el registro | `tmp_path` |
| TC-018 | `test_cert_registry.py` | `test_list_empty` | `registry.list()` sin registros previos | Retorna lista vacía | `tmp_path` |
| TC-019 | `test_cert_registry.py` | `test_remove_existing` | `registry.remove("app.example.com")` | Registro eliminado del JSON | `tmp_path` |
| TC-020 | `test_cert_registry.py` | `test_add_idempotent` | `registry.add(record)` dos veces | Solo un registro en JSON | `tmp_path` |
| TC-021 | `test_template_renderer.py` | `test_render_nginx_contains_domain` | `render("nginx/site.conf.j2", config)` | Output contiene `server_name app.example.com` | `tmp_path` |
| TC-022 | `test_template_renderer.py` | `test_render_apache_debian_uses_apache2` | `render("apache/vhost-debian.conf.j2", ...)` | Output contiene `DocumentRoot` y `ProxyPass` | `tmp_path` |
| TC-023 | `test_template_renderer.py` | `test_render_traefik_compose_has_service` | `render("traefik/docker-compose.yml.j2", ...)` | Output YAML válido con servicios `traefik` y `app` | `tmp_path` |

### 7.2 Tests Unitarios — `providers/`

| ID | Archivo | Test | Escenario | Resultado esperado | Mock |
|---|---|---|---|---|---|
| TC-024 | `test_nginx_provider.py` | `test_install_calls_pkg_manager` | `nginx.install()` | `pkg_manager.install(["nginx", ...])` llamado | `PackageManager`, `SystemRunner` |
| TC-025 | `test_nginx_provider.py` | `test_configure_calls_template_renderer` | `nginx.configure(config)` | `template_renderer.render(...)` llamado con `config` | `TemplateRenderer` mock |
| TC-026 | `test_nginx_provider.py` | `test_verify_uses_sudo` | `nginx.verify()` | `runner.run(["nginx", "-t"], sudo=True)` | `SystemRunner` |
| TC-027 | `test_nginx_provider.py` | `test_remove_unlinks_site` | `nginx.remove("myapp")` | `runner.run(["unlink", ...], sudo=True)` y `reload` | `SystemRunner` |
| TC-028 | `test_apache_provider.py` | `test_install_debian_uses_apache2` | `DistroFamily.DEBIAN` | `pkg_manager.install(["apache2", ...])` | `PackageManager`, `SystemRunner` |
| TC-029 | `test_apache_provider.py` | `test_install_redhat_uses_httpd` | `DistroFamily.REDHAT` | `pkg_manager.install(["httpd", ...])` | `PackageManager`, `SystemRunner` |
| TC-030 | `test_apache_provider.py` | `test_install_suse_uses_apache2` | `DistroFamily.SUSE` | `pkg_manager.install(["apache2", ...])` | `PackageManager`, `SystemRunner` |
| TC-031 | `test_apache_provider.py` | `test_configure_uses_distro_template` | `configure(config, DistroFamily.REDHAT)` | Template `vhost-redhat.conf.j2` seleccionado | `TemplateRenderer` mock |
| TC-032 | `test_traefik_provider.py` | `test_configure_creates_files` | `traefik.configure(config)` | docker-compose.yml y traefik.yml creados en `tmp_path` | `SystemRunner`, `tmp_path` |
| TC-033 | `test_traefik_provider.py` | `test_acme_json_permissions` | `traefik.configure(config)` | `runner.run(["chmod", "600", "acme.json"], sudo=True)` | `SystemRunner` |

### 7.3 Tests Unitarios — `certbot/`

| ID | Archivo | Test | Escenario | Resultado esperado | Mock |
|---|---|---|---|---|---|
| TC-034 | `test_certbot_installer.py` | `test_install_debian_uses_snap` | `DistroFamily.DEBIAN` | cmd contiene `snap install certbot` con sudo | `SystemRunner` |
| TC-035 | `test_certbot_installer.py` | `test_install_fedora_uses_dnf` | `DistroFamily.REDHAT` | cmd contiene `dnf install certbot` con sudo | `SystemRunner` |
| TC-036 | `test_certbot_installer.py` | `test_install_suse_uses_zypper` | `DistroFamily.SUSE` | cmd contiene `zypper install certbot` con sudo | `SystemRunner` |
| TC-037 | `test_certbot_installer.py` | `test_skip_if_already_installed` | `is_installed("certbot") == True` | No ejecuta comandos de instalación | `SystemRunner` |
| TC-038 | `test_certbot_manager.py` | `test_certonly_nginx_cmd` | `certonly(config, server="nginx")` | cmd contiene `--nginx -d app.example.com` con sudo | `SystemRunner` |
| TC-039 | `test_certbot_manager.py` | `test_certonly_staging_flag` | `config.staging=True` | cmd contiene `--staging` | `SystemRunner` |
| TC-040 | `test_certbot_manager.py` | `test_renew_cmd` | `manager.renew()` | cmd contiene `certbot renew` con sudo | `SystemRunner` |
| TC-041 | `test_certbot_manager.py` | `test_revoke_cmd` | `manager.revoke("app.example.com")` | cmd contiene `certbot revoke --cert-name` con sudo | `SystemRunner` |
| TC-042 | `test_certbot_manager.py` | `test_list_parses_fixture_ok` | stdout = fixture `certificates_ok.txt` | retorna lista con 2 `CertificateRecord` | `SystemRunner` con fixture |
| TC-043 | `test_certbot_manager.py` | `test_list_returns_empty_when_no_certs` | stdout = fixture `certificates_empty.txt` | retorna lista vacía | `SystemRunner` con fixture |

### 7.4 Tests Unitarios — `domain/`

| ID | Archivo | Test | Escenario | Resultado esperado | Mock |
|---|---|---|---|---|---|
| TC-044 | `test_certbot_service.py` | `test_generate_calls_dns_check` | `service.generate(config)` | `dns_validator.check(config.domain)` llamado | todos los deps |
| TC-045 | `test_certbot_service.py` | `test_generate_skip_dns_when_flag` | `config.skip_dns_check=True` | `dns_validator.check` no llamado | todos los deps |
| TC-046 | `test_certbot_service.py` | `test_generate_sequence` | `service.generate(config)` happy path | secuencia: DNS → install → configure → verify → certbot | todos los deps |
| TC-047 | `test_certbot_service.py` | `test_generate_aborts_on_dns_error` | `dns_validator.check` lanza `DNSValidationError` | `generate` propaga excepción, no sigue | todos los deps |
| TC-048 | `test_certbot_service.py` | `test_generate_aborts_on_root` | `os.geteuid() == 0` | lanza `SudoError` antes de hacer cualquier cosa | `os.geteuid` mock |
| TC-049 | `test_certbot_service.py` | `test_list_delegates_to_certbot_manager` | `service.list()` | retorna lo que retorna `certbot_manager.list_certificates()` | `CertbotManager` mock |
| TC-050 | `test_certbot_service.py` | `test_renew_delegates_to_certbot_manager` | `service.renew()` | `certbot_manager.renew()` llamado | `CertbotManager` mock |
| TC-051 | `test_certbot_service.py` | `test_remove_sequence` | `service.remove("app.example.com")` | revoke → remove config → registry.remove | todos los deps |

### 7.5 Tests Unitarios — CLI, interactive/ e i18n/

| ID | Archivo | Test | Escenario | Resultado esperado | Mock |
|---|---|---|---|---|---|
| TC-052 | `test_cli.py` | `test_generate_exits_0_with_all_flags` | `generate --server nginx --domain X --port 8080 --project Y --email Z` | exit code 0 | `CertbotService` mock via `CliRunner` |
| TC-053 | `test_cli.py` | `test_generate_exits_nonzero_missing_domain` | `generate --server nginx --no-interactive` (sin `--domain`) | exit code != 0, mensaje de error | `CliRunner` |
| TC-054 | `test_cli.py` | `test_list_calls_service_list` | `gen-cerbot list` | `service.list()` llamado; exit code 0 | `CertbotService` mock |
| TC-055 | `test_cli.py` | `test_version_flag` | `gen-cerbot --version` | output contiene versión del paquete | ninguno |
| TC-056 | `test_cli.py` | `test_lang_flag_sets_locale` | `gen-cerbot --lang es generate ...` | `LocaleManager.set_lang("es")` llamado antes de Typer | `LocaleManager` mock |
| TC-057 | `interactive/test_wizard.py` | `test_wizard_happy_path` | respuestas predefinidas para 6 campos | retorna `CertificateConfig` con valores correctos | `questionary.unsafe_ask` |
| TC-058 | `interactive/test_wizard.py` | `test_wizard_rejects_invalid_email` | email `"not-an-email"` | re-pregunta (no avanza) | `questionary` mock |
| TC-059 | `interactive/test_wizard.py` | `test_wizard_rejects_invalid_port` | port `"99999"` | re-pregunta (no avanza) | `questionary` mock |
| TC-060 | `interactive/test_menu.py` | `test_menu_generate_routes_to_wizard` | selección "Generate certificate" | llama `wizard.run()` | `questionary.select`, `GenerateWizard` mock |
| TC-061 | `interactive/test_menu.py` | `test_menu_exit_calls_sys_exit` | selección "Exit" | `sys.exit(0)` llamado | `questionary.select`, `sys.exit` mock |
| TC-062 | `interactive/test_output.py` | `test_renderer_shows_check_on_success` | `renderer.step("Installing", success=True)` | output capturado contiene `[✔]` | `rich.Console(file=StringIO())` |
| TC-063 | `interactive/test_output.py` | `test_renderer_shows_cross_on_failure` | `renderer.step("Installing", success=False)` | output capturado contiene `[✗]` | `rich.Console(file=StringIO())` |
| TC-064 | `i18n/test_locale_manager.py` | `test_t_returns_correct_en_string` | `manager.set_lang("en"); manager.t("menu.exit")` | `"Exit"` | JSON en `tmp_path` |
| TC-065 | `i18n/test_locale_manager.py` | `test_t_returns_correct_es_string` | `manager.set_lang("es"); manager.t("menu.exit")` | `"Salir"` | JSON en `tmp_path` |
| TC-066 | `i18n/test_locale_manager.py` | `test_t_falls_back_to_en_for_missing_key` | clave existe en `en.json` pero no en `es.json` | retorna valor en inglés, sin excepción | JSON parcial en `tmp_path` |
| TC-067 | `i18n/test_locale_manager.py` | `test_t_interpolates_variables` | `manager.t("output.done", domain="app.example.com")` | string con dominio interpolado | JSON en `tmp_path` |
| TC-068 | `i18n/test_language_selector.py` | `test_resolve_reads_saved_preference` | `config.toml` contiene `lang = "es"` | `LocaleManager.set_lang("es")` llamado; no muestra prompt | `config.toml` en `tmp_path`, `questionary` mock |
| TC-069 | `i18n/test_language_selector.py` | `test_resolve_shows_prompt_on_first_run` | `config.toml` no existe | prompt `questionary.select` mostrado; respuesta persistida | `questionary.select` mock |
| TC-070 | `i18n/test_language_selector.py` | `test_resolve_lang_flag_skips_prompt` | `--lang es` pasado | `set_lang("es")` sin prompt ni lectura de `config.toml` | `questionary` no llamado |

### 7.6 Tests de Integración

| ID | Archivo | Test | Qué se prueba | Deps reales | Deps mockeados |
|---|---|---|---|---|---|
| TI-001 | `test_nginx_config_gen.py` | `test_nginx_configure_creates_valid_file` | Archivo de config Nginx generado en `tmp_path` contiene dominio, puerto y cabeceras correctas | `NginxProvider`, `TemplateRenderer`, `CertificateConfig` | `SystemRunner` |
| TI-002 | `test_apache_config_gen.py` | `test_apache_debian_template_selected` | `ApacheProvider` con `DistroFamily.DEBIAN` genera el VirtualHost con `apache2` syntax | `ApacheProvider`, `TemplateRenderer` | `SystemRunner`, `PackageManager` |
| TI-003 | `test_apache_config_gen.py` | `test_apache_redhat_template_selected` | `ApacheProvider` con `DistroFamily.REDHAT` genera el VirtualHost con `httpd` syntax | `ApacheProvider`, `TemplateRenderer` | `SystemRunner`, `PackageManager` |
| TI-004 | `test_apache_config_gen.py` | `test_apache_suse_template_selected` | `ApacheProvider` con `DistroFamily.SUSE` genera el VirtualHost correcto | `ApacheProvider`, `TemplateRenderer` | `SystemRunner`, `PackageManager` |
| TI-005 | `test_traefik_config_gen.py` | `test_traefik_generates_compose_and_yml` | `TraefikProvider` genera `docker-compose.yml` y `traefik.yml` en `tmp_path`; YAML parseable | `TraefikProvider`, `TemplateRenderer` | `SystemRunner` |
| TI-006 | `test_traefik_config_gen.py` | `test_traefik_acme_json_chmod_600` | `runner.run(["chmod", "600", ...])` llamado con `sudo=True` | `TraefikProvider` | `SystemRunner` mock que registra calls |
| TI-007 | `test_certbot_output.py` | `test_parse_certificates_ok_fixture` | `CertbotManager.list_certificates()` parsea fixture → 2 registros con dominio y expiración | `CertbotManager` | `SystemRunner` con stdout = fixture |
| TI-008 | `test_certbot_output.py` | `test_parse_certificates_empty_fixture` | `CertbotManager.list_certificates()` retorna `[]` con fixture vacía | `CertbotManager` | `SystemRunner` con stdout = fixture |
| TI-009 | `test_cert_registry_io.py` | `test_registry_persists_and_reads_back` | `add` + `list` + `remove` sobre JSON real en `tmp_path` | `CertRegistry` | ninguno |
| TI-010 | `test_full_flow.py` | `test_generate_full_flow_nginx_debian` | Flujo completo `CertbotService.generate()` con Nginx en Debian; verifica secuencia de mocks | `CertbotService`, `NginxProvider`, `CertbotManager`, `CertRegistry` | `SystemRunner`, `socket.getaddrinfo`, `tmp_path` |

---

## Historial de Cambios

| Versión | Fecha | Autor | Cambios |
|---|---|---|---|
| 1.0 | 2026-03-31 | Ernesto Crespo | Versión inicial: 6 fases, Nginx/Apache/Traefik, Certbot, CLI Typer |
| 1.1 | 2026-03-31 | Ernesto Crespo | Soporte multi-distro: F1-07 SystemRunner sudo, F1-08 DistroDetector, F1-09 PackageManager (apt/dnf/zypper); nueva VM Fedora en pre-requisitos; 2 nuevos riesgos de distro |
| 1.2 | 2026-03-31 | Ernesto Crespo | Modo interactivo: Fase 7 completa (15 tareas F7-01..F7-15); mapa de dependencias actualizado; resumen corregido a 7 fases/7 semanas; 2 nuevos riesgos de terminal/TUI |
| 1.3 | 2026-03-31 | Ernesto Crespo | Soporte i18n: Fase 8 completa (13 tareas F8-01..F8-13); resumen 8 fases/8 semanas/2026-05-26; mapa de dependencias Fase 7→Fase 8; nuevo riesgo traducciones incompletas; DoD actualizado con criterios i18n |
| 1.4 | 2026-03-31 | Ernesto Crespo | Empaquetado nativo: Fase 6 ampliada a 2 semanas con 25 tareas (F6-10..F6-34) para PyPI wheel, .deb (debian/) y .rpm (rpm/spec); pre-requisitos de build; resumen 9 semanas/2026-06-02; estructura packaging/; DoD global con criterios de instalación nativa |
| 1.5 | 2026-03-31 | Ernesto Crespo | Catálogo de tests: nueva Sección 7 con 80 casos de prueba (TC-001..TC-070 unitarios + TI-001..TI-010 integración) organizados por módulo con entradas, resultado esperado y estrategia de mock; cubre utils, providers, certbot, domain/services, CLI, interactive, i18n |
