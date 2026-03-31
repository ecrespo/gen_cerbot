# gen_cerbot

> CLI interactivo en Python para generar y gestionar certificados TLS/SSL para servidores web (Nginx, Apache, Traefik) usando Let's Encrypt / Certbot. Soporta modo menú guiado y modo comando directo.

---

## ¿Qué es gen_cerbot?

`gen_cerbot` es una herramienta de línea de comandos que automatiza el proceso completo de configuración TLS/SSL para los servidores web más utilizados. En lugar de ejecutar comandos manuales y editar archivos de configuración a mano, el usuario declara sus parámetros en el CLI y `gen_cerbot` se encarga del resto: instalación de dependencias, configuración del servidor, solicitud del certificado y renovación automática.

## Características principales

- **Modo interactivo (menú)**: Guía al usuario paso a paso con menús de selección y campos de entrada; muestra la salida de ejecución en tiempo real
- **Multi-idioma (i18n)**: Interfaz interactiva disponible en inglés y español; selector de idioma al primer uso, preferencia guardada automáticamente; flag `--lang` para forzar el idioma
- **Modo comando directo**: Todos los subcomandos disponibles también como flags CLI para uso en scripts y CI/CD
- **Multi-servidor**: Soporte para Nginx, Apache y Traefik con configuración de proxy reverso y certificados
- **Multi-distro**: Selección manual o detección automática de la familia de paquetes (`deb` para Debian/Ubuntu, `rpm` para Fedora/openSUSE)
- **sudo interno**: Invoca `sudo` de forma transparente cuando se necesitan privilegios elevados; no es necesario ejecutar el CLI como root
- **Integración con Let's Encrypt**: Solicitud y renovación de certificados vía Certbot (ACME protocol)
- **Proxy reverso automático**: Genera la configuración completa de reverse proxy en Nginx, Apache o Traefik
- **Validación de DNS**: Verificación previa de que el dominio apunta correctamente antes de solicitar el certificado
- **Renovación automática**: Configuración de cron/systemd timer para renovación automática
- **Dry-run mode**: Prueba de configuración sin aplicar cambios reales
- **Idempotente**: Re-ejecutar el comando en un sistema ya configurado no rompe nada

## Instalación

`gen_cerbot` está disponible en tres formatos: paquete Python (PyPI), paquete nativo para Debian/Ubuntu (`.deb`) y paquete nativo para Fedora/openSUSE (`.rpm`).

### Opción 1 — pip / pipx (todas las distribuciones)

```bash
# Recomendado: pipx instala en entorno aislado y expone gen-cerbot en el PATH
pipx install gen-cerbot

# Alternativa con pip
pip install gen-cerbot
```

### Opción 2 — Paquete nativo .deb (Debian / Ubuntu)

Descarga el `.deb` desde [GitHub Releases](https://github.com/user/gen_cerbot/releases) e instala:

```bash
sudo dpkg -i gen-cerbot_<version>_all.deb

# Si hay dependencias faltantes, resuélvelas con:
sudo apt-get install -f
```

Tras la instalación, `gen-cerbot` queda disponible en `/usr/bin/gen-cerbot`.

### Opción 3 — Paquete nativo .rpm (Fedora / openSUSE)

Descarga el `.rpm` desde [GitHub Releases](https://github.com/user/gen_cerbot/releases) e instala:

```bash
# Fedora
sudo dnf install ./gen-cerbot-<version>-1.noarch.rpm

# openSUSE
sudo zypper install ./gen-cerbot-<version>-1.noarch.rpm
```

Tras la instalación, `gen-cerbot` queda disponible en `/usr/bin/gen-cerbot`.

### Desde el repositorio (desarrollo)

```bash
git clone https://github.com/user/gen_cerbot.git
cd gen_cerbot
pip install -e .
```

## Selector de idioma

En la **primera ejecución**, antes de mostrar el menú principal, `gen_cerbot` muestra un selector de idioma:

```
  Select your language / Selecciona tu idioma:
   ❯  English
      Español
```

La selección se guarda en `~/.config/gen_cerbot/config.toml`. Las siguientes ejecuciones abren el menú directamente en el idioma guardado, sin preguntar de nuevo.

Para forzar un idioma específico en cualquier momento (sin cambiar la preferencia):

```bash
gen-cerbot --lang en   # inglés
gen-cerbot --lang es   # español
```

---

## Modo interactivo (recomendado)

Ejecutar sin argumentos lanza el selector de idioma (si aplica) y luego el menú guiado:

```bash
gen-cerbot
```

Con preferencia guardada o con `--lang`:

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

O en español si se seleccionó ese idioma:

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

Al seleccionar **Generar nuevo certificado SSL**, el asistente guía al usuario:

```
  Subdominio o dominio completo: api.miempresa.com
  Puerto del servicio dockerizado: 8000
  Familia de paquetes del sistema:
    ❯  deb  — Debian / Ubuntu  (apt)
       rpm  — Fedora / openSUSE (dnf / zypper)
  Servidor web:
    ❯  nginx
       apache
       traefik
  Email para Let's Encrypt: admin@miempresa.com
  Nombre del proyecto: miapi

  ──────────────────────────────────────────────────
  Resumen:
    Dominio  : api.miempresa.com → localhost:8000
    Servidor : nginx  |  Distro: deb (apt)
    Email    : admin@miempresa.com
  ──────────────────────────────────────────────────
  ¿Continuar?  ❯ Sí    No
```

A continuación se muestra la salida de ejecución en tiempo real:

```
  [✔] Distro detectada: Ubuntu 22.04 → apt
  [✔] DNS OK: api.miempresa.com → 203.0.113.5
  [→] Instalando nginx...
      sudo apt-get install -y nginx
  [✔] nginx instalado
  [→] Generando configuración...
      sudo tee /etc/nginx/sites-available/miapi
  [✔] Configuración creada
  [→] Verificando sintaxis (nginx -t)...
  [✔] Configuración válida
  [→] Instalando Certbot via snap...
  [✔] Certbot listo
  [→] Solicitando certificado Let's Encrypt...
      sudo certbot --nginx -d api.miempresa.com
  [✔] Certificado obtenido. Expira: 2026-06-29

  ══════════════════════════════════════════════════
  ✅  https://api.miempresa.com  está listo con SSL
  ══════════════════════════════════════════════════
```

## Modo comando directo

Para uso en scripts, CI/CD o automatización:

```bash
# Configurar Nginx con SSL (en inglés)
gen-cerbot --lang en generate --server nginx --domain sub.example.com --port 8000 --project myapp

# Configurar Apache con SSL (en español)
gen-cerbot --lang es generate --server apache --domain api.example.com --port 3000 --project myapi

# Configurar Traefik (sin prompts — modo CI/CD)
gen-cerbot generate --server traefik --domain app.example.com --email admin@example.com --no-interactive

# Renovar todos los certificados
gen-cerbot renew

# Listar certificados gestionados
gen-cerbot list

# Eliminar configuración de un dominio
gen-cerbot remove --domain sub.example.com
```

## Requisitos del sistema

- Python 3.11+ (no necesario si se instala via `.deb` o `.rpm` — el paquete lo gestiona)
- Linux — distribuciones soportadas:
  - **Debian/Ubuntu** (20.04, 22.04, 24.04 / Debian 11, 12) — usa `apt`
  - **Fedora** (38+) — usa `dnf`
  - **openSUSE Leap / Tumbleweed** — usa `zypper`
- Docker (para modo Traefik)
- El dominio debe tener DNS resolviendo a la IP del servidor
- El usuario debe poder ejecutar `sudo` — gen_cerbot lo invoca internamente cuando necesita privilegios elevados; no es necesario ejecutar el CLI como root

---

## Construcción de paquetes

Esta sección describe cómo compilar los tres formatos de distribución desde el código fuente.

### Requisitos previos comunes

```bash
git clone https://github.com/user/gen_cerbot.git
cd gen_cerbot
```

### Wheel para PyPI

Herramientas necesarias: `python-build`, `twine`

```bash
pip install build twine

# Generar wheel (.whl) y source distribution (.tar.gz)
python -m build

# Los artefactos quedan en dist/
ls dist/
# gen_cerbot-1.0.0-py3-none-any.whl
# gen_cerbot-1.0.0.tar.gz

# Verificar el paquete antes de publicar
twine check dist/*

# Publicar en TestPyPI (prueba)
twine upload --repository testpypi dist/*

# Publicar en PyPI (producción)
twine upload dist/*
```

### Paquete Debian/Ubuntu (.deb)

Requiere una VM o contenedor **Debian 12 (Bookworm)** o **Ubuntu 22.04+**.

```bash
# Instalar herramientas de empaquetado
sudo apt-get install -y fakeroot dpkg-dev debhelper dh-python python3-all

# Construir el paquete (sin firmar, para distribución manual)
dpkg-buildpackage -us -uc -b

# El .deb queda en el directorio padre
ls ../
# gen-cerbot_1.0.0-1_all.deb

# Validar el paquete
lintian --no-tag-display-limit ../gen-cerbot_1.0.0-1_all.deb

# Instalar y probar
sudo dpkg -i ../gen-cerbot_1.0.0-1_all.deb
gen-cerbot --version
```

Los archivos de packaging se encuentran en `packaging/debian/`:

```
packaging/debian/
├── changelog   # Historia de versiones (formato Debian)
├── compat      # Nivel de compatibilidad debhelper (13)
├── control     # Metadatos: nombre, arch, dependencias, descripción
├── copyright   # Licencia en formato DEP-5
├── install     # Lista de archivos a instalar
└── rules       # Script de build con dh helper
```

### Paquete RPM para Fedora/openSUSE (.rpm)

Requiere una VM o contenedor **Fedora 40+**.

```bash
# Instalar herramientas de empaquetado
sudo dnf install -y rpm-build python3-devel python3-pip rpmdevtools rpmlint

# Configurar el árbol de build
rpmdev-setuptree
# Crea ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Crear el tarball fuente
python -m build --sdist
cp dist/gen_cerbot-1.0.0.tar.gz ~/rpmbuild/SOURCES/

# Copiar el spec
cp packaging/rpm/gen-cerbot.spec ~/rpmbuild/SPECS/

# Construir el .rpm binario
rpmbuild -bb ~/rpmbuild/SPECS/gen-cerbot.spec

# El .rpm queda en ~/rpmbuild/RPMS/noarch/
ls ~/rpmbuild/RPMS/noarch/
# gen-cerbot-1.0.0-1.noarch.rpm

# Validar el paquete
rpmlint ~/rpmbuild/RPMS/noarch/gen-cerbot-1.0.0-1.noarch.rpm

# Instalar y probar (Fedora)
sudo dnf install ~/rpmbuild/RPMS/noarch/gen-cerbot-1.0.0-1.noarch.rpm
gen-cerbot --version

# Instalar y probar (openSUSE)
sudo zypper install ~/rpmbuild/RPMS/noarch/gen-cerbot-1.0.0-1.noarch.rpm
gen-cerbot --version
```

El spec file se encuentra en `packaging/rpm/gen-cerbot.spec`.

### Release automatizado (GitHub Actions)

Al hacer push de un tag `v*` (por ejemplo `git tag v1.0.0 && git push --tags`), el workflow `.github/workflows/release.yml` ejecuta automáticamente:

1. Build del wheel + source distribution → upload a PyPI
2. Build del `.deb` en runner Ubuntu → subido a GitHub Releases
3. Build del `.rpm` en runner Fedora → subido a GitHub Releases

---

## Estructura del proyecto

```
gen_cerbot/
├── README.md               ← Este archivo
├── ARCHITECTURE.md         ← Diseño técnico y decisiones de arquitectura
├── SPEC.md                 ← Especificación de producto (PRD)
├── TASKS.md                ← Plan de implementación por fases
├── pyproject.toml
├── src/
│   └── gen_cerbot/
│       ├── __init__.py
│       ├── cli.py              ← Punto de entrada CLI (Typer)
│       ├── core/
│       │   ├── config.py       ← Configuración global
│       │   └── exceptions.py   ← Excepciones del dominio
│       ├── domain/
│       │   ├── models.py       ← Modelos de datos
│       │   └── services.py     ← Lógica de negocio principal
│       ├── providers/
│       │   ├── base.py         ← Interfaz abstracta de servidor
│       │   ├── nginx.py        ← Implementación Nginx
│       │   ├── apache.py       ← Implementación Apache
│       │   └── traefik.py      ← Implementación Traefik
│       ├── certbot/
│       │   ├── installer.py    ← Instalación de Certbot
│       │   └── manager.py      ← Gestión de certificados
│       ├── interactive/
│       │   ├── menu.py             ← Menú principal y navegación
│       │   ├── wizard.py           ← Asistente paso a paso (generate)
│       │   └── output.py           ← Salida en tiempo real con rich
│       ├── i18n/
│       │   ├── locale_manager.py   ← LocaleManager: t("key") con fallback a en
│       │   ├── selector.py         ← Selector de idioma + persistencia config.toml
│       │   └── locales/
│       │       ├── en.json         ← Cadenas en inglés (por defecto)
│       │       └── es.json         ← Cadenas en español
│       └── utils/
│           ├── dns.py              ← Validación DNS
│           ├── system.py           ← Comandos de sistema (sudo interno)
│           ├── distro.py           ← Detección de distribución Linux
│           ├── package_manager.py  ← Abstracción apt / dnf / zypper
│           └── templates.py        ← Renderizado de plantillas
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│       └── os-release/     ← Fixtures de /etc/os-release por distro
├── packaging/
│   ├── debian/             ← Archivos para construir el paquete .deb
│   │   ├── changelog       ← Historia de versiones (formato Debian)
│   │   ├── compat          ← Nivel debhelper (13)
│   │   ├── control         ← Metadatos y dependencias del paquete
│   │   ├── copyright       ← Licencia en formato DEP-5
│   │   ├── install         ← Archivos a instalar en el sistema
│   │   └── rules           ← Script de build con dh helper
│   └── rpm/
│       └── gen-cerbot.spec ← Spec file para rpmbuild
├── .github/
│   └── workflows/
│       ├── ci.yml          ← CI: tests en Ubuntu/Fedora en cada PR
│       └── release.yml     ← Release: build wheel+.deb+.rpm y upload
├── nginx-setup.sh          ← Script bash original (referencia)
└── docs/
```

## Documentación SDD

Este proyecto sigue la metodología **Spec-Driven Design**. Los documentos de especificación viven en la raíz del repositorio:

| Documento | Descripción |
|---|---|
| [SPEC.md](./SPEC.md) | Requisitos funcionales y no funcionales (PRD) |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Diseño técnico, componentes y decisiones |
| [TASKS.md](./TASKS.md) | Plan de implementación por fases |

## Licencia

Ver [LICENSE](./LICENSE).
