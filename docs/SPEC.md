# gen_cerbot — CLI para Generación de Certificados TLS/SSL

## Product Requirements Document (PRD)

| Campo | Valor |
|---|---|
| **Autor** | Ernesto Crespo |
| **Estado** | `DRAFT` |
| **Versión** | 1.5 |
| **Fecha** | 2026-03-31 |
| **Reviewers** | Por definir |
| **Última actualización** | 2026-03-31 |

---

## 1. Resumen Ejecutivo

`gen_cerbot` es una herramienta CLI en Python que automatiza la configuración de certificados TLS/SSL para servidores web Nginx, Apache y Traefik usando Let's Encrypt (Certbot). El objetivo es eliminar el proceso manual y propenso a errores de instalar dependencias, editar archivos de configuración y solicitar certificados: el usuario simplemente declara sus parámetros en el CLI y la herramienta se encarga del proceso completo.

La herramienta ofrece dos modos de uso: un **modo interactivo** con menú guiado donde el usuario selecciona opciones paso a paso y ve la salida de ejecución en tiempo real, y un **modo comando directo** donde todos los parámetros se pasan como flags para uso en scripts y CI/CD. En el modo interactivo el usuario indica: el subdominio, el puerto del servicio dockerizado, la familia de paquetes del sistema (`deb` o `rpm`) y el servidor web (`nginx`, `apache` o `traefik`); la herramienta configura el proxy reverso y genera el certificado automáticamente.

Internamente, usa el gestor de paquetes adecuado (`apt` en Debian/Ubuntu, `dnf` en Fedora, `zypper` en openSUSE) para instalar al vuelo todo lo necesario: el servidor web, Certbot y sus plugins. Invoca `sudo` cuando se requieren privilegios elevados, de modo que el usuario ejecuta el CLI como usuario normal.

El proyecto nace de un script bash existente (`nginx-setup.sh`) que resolvía el problema de forma ad-hoc para Nginx en Ubuntu/Debian. `gen_cerbot` lo evoluciona hacia una solución robusta, multi-servidor, multi-distro, testeada y empaquetable como herramienta Python reutilizable.

El público objetivo son ingenieros de infraestructura, DevOps y desarrolladores que administran servidores Linux y necesitan configurar HTTPS de forma rápida y repetible para múltiples proyectos o dominios, independientemente de la distribución del servidor.

---

## 2. Contexto y Problema

### 2.1 Situación Actual

Hoy, configurar TLS/SSL en un servidor nuevo implica una secuencia manual de comandos: actualizar el sistema, instalar Nginx/Apache, crear archivos de configuración del virtual host, activar el sitio, instalar Certbot (con diferentes métodos según la distro), solicitar el certificado y verificar que todo funcione. El script bash `nginx-setup.sh` resuelve parte de este problema para Nginx en Ubuntu/Debian, pero no cubre Apache ni Traefik, no soporta Fedora ni openSUSE, no es testeado ni empaquetado, y no ofrece operaciones de mantenimiento (renovación, listado, eliminación).

### 2.2 Problema

El proceso de configuración SSL es repetitivo, manual y propenso a errores. Cada vez que se levanta un nuevo servidor o proyecto hay que recordar los pasos correctos, el orden de los comandos y los detalles de configuración (timeouts, proxy headers, etc.). Los errores en este proceso dejan servicios sin HTTPS o con configuraciones inseguras.

### 2.3 Oportunidad

Empaquetar este conocimiento operacional en un CLI Python reutilizable, testeado y multi-servidor reduce el tiempo de configuración de ~20 minutos manuales a un único comando. Además, la herramienta se puede integrar en pipelines CI/CD y scripts de aprovisionamiento de infraestructura.

---

## 3. Usuarios Objetivo

### Persona 1: DevOps / SRE

- **Descripción:** Ingeniería de operaciones que administra múltiples servidores y proyectos
- **Necesidad principal:** Configurar HTTPS en servidores nuevos de forma rápida, repetible y segura
- **Frecuencia de uso:** Semanal / por evento de aprovisionamiento
- **Nivel técnico:** Alto

### Persona 2: Desarrollador Backend

- **Descripción:** Desarrollador que levanta sus propios servidores en VPS o EC2 para proyectos personales o de equipo
- **Necesidad principal:** No tener que recordar la secuencia de comandos para configurar Nginx+SSL cada vez
- **Frecuencia de uso:** Eventual (por proyecto nuevo)
- **Nivel técnico:** Medio-Alto

### Persona 3: Técnico de Infraestructura

- **Descripción:** Administrador de sistemas que gestiona flotas de servidores para clientes
- **Necesidad principal:** Herramienta estandarizada y auditable para configurar SSL en múltiples clientes
- **Frecuencia de uso:** Frecuente
- **Nivel técnico:** Alto

---

## 4. Objetivos y Métricas de Éxito

### 4.1 Objetivos del Proyecto

| Objetivo | Métrica | Target | Plazo |
|---|---|---|---|
| Reducir tiempo de configuración SSL | Minutos por configuración | < 3 min (vs ~20 min manual) | v1.0 |
| Soporte multi-servidor | Servidores soportados | Nginx, Apache, Traefik | v1.0 |
| Confiabilidad del proceso | Tasa de éxito en primera ejecución | > 95% | v1.0 |
| Mantenibilidad del código | Cobertura de tests | > 80% | v1.0 |

### 4.2 Objetivos de Usuario

| Objetivo del Usuario | Indicador |
|---|---|
| Configurar HTTPS sin editar archivos manualmente | El comando `generate` completa el flujo sin intervención |
| Saber qué certificados tiene gestionados | El comando `list` muestra estado, dominio y fecha de expiración |
| Renovar certificados fácilmente | El comando `renew` no requiere parámetros adicionales |
| Probar antes de aplicar | El flag `--dry-run` ejecuta sin efectos reales |

---

## 5. Alcance

### 5.1 In Scope (Incluido)

- [x] Subcomando `generate`: configuración completa de servidor + SSL para Nginx, Apache y Traefik
- [x] Subcomando `renew`: renovación de certificados existentes
- [x] Subcomando `list`: listado de certificados gestionados con estado y fecha de expiración
- [x] Subcomando `remove`: eliminación de configuración y certificado de un dominio
- [x] Validación previa de DNS (verificar que el dominio resuelve a la IP del servidor)
- [x] Soporte para `--dry-run` (simula sin aplicar cambios)
- [x] Generación de configuración Nginx con reverse proxy y headers seguros
- [x] Generación de configuración Apache con VirtualHost y proxy
- [x] Generación de configuración Traefik (docker-compose + traefik.yml)
- [x] **Modo interactivo con menú**: menú principal navegable + asistente paso a paso para `generate` con salida de ejecución en tiempo real
- [x] Selección interactiva de: subdominio, puerto del servicio dockerizado, familia de paquetes (`deb`/`rpm`) y servidor web
- [x] Pantalla de resumen y confirmación antes de ejecutar en modo interactivo
- [x] Instalación automática de Certbot si no está presente
- [x] Detección automática de la distribución Linux; en modo interactivo el usuario también puede seleccionarla manualmente (`deb`/`rpm`)
- [x] Instalación al vuelo de paquetes necesarios (servidor web, Certbot, plugins) usando el gestor detectado
- [x] Invocación interna de `sudo` para operaciones que requieren privilegios elevados
- [x] Configuración de renovación automática vía cron/systemd timer
- [x] Soporte para múltiples dominios / SAN en un mismo certificado
- [x] Output con colores y mensajes claros de progreso y errores
- [x] Logging a archivo para auditoría

### 5.2 Out of Scope (Excluido)

- Soporte para Windows o macOS como sistema operativo del servidor (solo Linux)
- Interfaz gráfica (GUI) o aplicación web — solo CLI/TUI en consola
- Gestión de certificados privados / CA interna (solo Let's Encrypt / ACME público)
- Integración con proveedores DNS para challenge DNS-01 (solo HTTP-01 en v1.0)
- Configuración de firewall (ufw, iptables) — queda fuera del alcance del CLI
- Interfaz web o TUI — solo CLI
- Soporte para servidores Windows IIS

### 5.3 Futuras Consideraciones

- Challenge DNS-01 para dominios con restricciones de firewall
- Soporte para Caddy como servidor web adicional
- Integración con Ansible / Terraform para aprovisionamiento declarativo
- Soporte para wildcard certificates
- Plugin para renovación automática vía GitHub Actions

---

## 6. Requisitos Funcionales

### RF-001: Generar configuración SSL para Nginx

- **Descripción:** El sistema debe instalar Nginx (si no está instalado), crear la configuración del virtual host con reverse proxy y obtener el certificado TLS/SSL con Certbot.
- **Actor:** Usuario (CLI)
- **Precondiciones:** El servidor corre una distribución Linux soportada (Debian/Ubuntu, Fedora, openSUSE), el dominio tiene DNS configurado apuntando a la IP del servidor, el usuario puede ejecutar `sudo`.
- **Flujo principal:**
  1. Usuario ejecuta `gen-cerbot generate --server nginx --domain sub.example.com --port 8000 --project myapp`
  2. El CLI valida los parámetros de entrada
  3. El CLI detecta la distribución Linux y selecciona el gestor de paquetes (`apt`/`dnf`/`zypper`)
  4. El CLI verifica que el dominio resuelve a la IP del servidor (DNS check)
  5. El CLI instala Nginx si no está presente usando `sudo <pkg-manager> install nginx`
  6. El CLI genera el archivo de configuración del sitio en `/etc/nginx/sites-available/`
  7. El CLI activa el sitio (symlink en Debian/Ubuntu, include en Fedora/openSUSE)
  8. El CLI verifica la configuración con `sudo nginx -t`
  9. El CLI instala Certbot si no está presente (snap en Debian/Ubuntu, `dnf`/`zypper` en Fedora/openSUSE)
  10. El CLI solicita el certificado con `sudo certbot --nginx -d domain`
  11. El CLI muestra mensaje de éxito con la URL HTTPS resultante
- **Flujo alternativo:** Si el DNS check falla, el CLI informa al usuario y ofrece continuar con `--skip-dns-check` o abortar.
- **Postcondiciones:** El dominio responde por HTTPS con certificado válido. La renovación automática está configurada.
- **Prioridad:** `MUST`

### RF-002: Generar configuración SSL para Apache

- **Descripción:** El sistema debe instalar Apache (si no está instalado), crear la configuración del VirtualHost con reverse proxy y obtener el certificado TLS/SSL con Certbot.
- **Actor:** Usuario (CLI)
- **Precondiciones:** El servidor corre una distribución Linux soportada, el dominio tiene DNS configurado, el usuario puede ejecutar `sudo`.
- **Flujo principal:**
  1. Usuario ejecuta `gen-cerbot generate --server apache --domain api.example.com --port 3000 --project myapi`
  2. Validación de parámetros y DNS check
  3. Detección de la distribución y selección del gestor de paquetes
  4. Instalación de Apache y módulos necesarios usando `sudo <pkg-manager>`:
     - Debian/Ubuntu: `apache2`, `libapache2-mod-proxy-html`
     - Fedora: `httpd`, `mod_ssl`
     - openSUSE: `apache2`, `apache2-mod_proxy`
  5. Habilitación de módulos (`a2enmod proxy` en Debian/Ubuntu; `httpd_module` en Fedora/openSUSE)
  6. Generación del VirtualHost con ProxyPass vía template Jinja2
  7. Instalación de Certbot y plugin Apache (`python3-certbot-apache` / `certbot-apache` según distro)
  8. Solicitud del certificado con `sudo certbot --apache`
  9. Mensaje de éxito con URL HTTPS
- **Flujo alternativo:** Si el puerto está en uso, el CLI informa del conflicto y sugiere alternativas.
- **Postcondiciones:** El dominio responde por HTTPS con certificado válido.
- **Prioridad:** `MUST`

### RF-003: Generar configuración SSL para Traefik

- **Descripción:** El sistema debe generar los archivos de configuración para Traefik (docker-compose.yml y traefik.yml) con HTTPS automático vía Let's Encrypt.
- **Actor:** Usuario (CLI)
- **Precondiciones:** Docker y Docker Compose están instalados, el dominio tiene DNS configurado.
- **Flujo principal:**
  1. Usuario ejecuta `gen-cerbot generate --server traefik --domain app.example.com --email admin@example.com`
  2. Validación de parámetros y DNS check
  3. Verificación de que Docker está instalado
  4. Generación de `docker-compose.yml` con servicio Traefik y red Docker
  5. Generación de `traefik.yml` con configuración ACME (Let's Encrypt)
  6. Creación de `acme.json` con permisos correctos (600)
  7. Instrucciones finales para levantar con `docker compose up -d`
- **Flujo alternativo:** Si Docker no está instalado, el CLI informa y opcionalmente instala Docker.
- **Postcondiciones:** Los archivos de configuración están generados y listos para usar.
- **Prioridad:** `MUST`

### RF-004: Listar certificados gestionados

- **Descripción:** El sistema debe mostrar todos los certificados que ha generado, con su estado, fecha de expiración y servidor asociado.
- **Actor:** Usuario (CLI)
- **Precondiciones:** Existe al menos un certificado generado por `gen_cerbot`.
- **Flujo principal:**
  1. Usuario ejecuta `gen-cerbot list`
  2. El CLI lee el registro local de certificados gestionados
  3. Para cada certificado, consulta la fecha de expiración real con Certbot
  4. Muestra tabla con: dominio, servidor, fecha de expiración, estado (OK / EXPIRANDO / EXPIRADO)
- **Prioridad:** `MUST`

### RF-005: Renovar certificados

- **Descripción:** El sistema debe renovar todos los certificados próximos a expirar o un certificado específico.
- **Actor:** Usuario (CLI) o cron/systemd timer
- **Flujo principal:**
  1. Usuario ejecuta `gen-cerbot renew` o `gen-cerbot renew --domain sub.example.com`
  2. El CLI ejecuta `certbot renew` (o con `--cert-name` para dominio específico)
  3. Muestra resultado de la renovación
- **Prioridad:** `MUST`

### RF-006: Eliminar configuración de un dominio

- **Descripción:** El sistema debe revocar el certificado, eliminar la configuración del servidor y limpiar el registro local.
- **Actor:** Usuario (CLI)
- **Flujo principal:**
  1. Usuario ejecuta `gen-cerbot remove --domain sub.example.com`
  2. CLI muestra confirmación con los cambios que se aplicarán
  3. Usuario confirma
  4. CLI revoca y elimina el certificado con Certbot
  5. CLI elimina la configuración del servidor (Nginx/Apache)
  6. CLI actualiza el registro local
- **Prioridad:** `SHOULD`

### RF-007: Modo dry-run

- **Descripción:** Cualquier subcomando debe poder ejecutarse con `--dry-run` para mostrar qué haría sin aplicar cambios reales.
- **Actor:** Usuario (CLI)
- **Prioridad:** `SHOULD`

### RF-008: Validación DNS previa

- **Descripción:** Antes de solicitar un certificado, el CLI debe verificar que el dominio resuelve a una de las IPs del servidor actual.
- **Prioridad:** `MUST`

### RF-009: Detección automática del gestor de paquetes y uso de sudo

- **Descripción:** El sistema debe detectar la distribución Linux en tiempo de ejecución e invocar el gestor de paquetes correcto con `sudo` para instalar todas las dependencias necesarias sin que el usuario tenga que especificarlas manualmente.
- **Actor:** CertbotService (interno)
- **Precondiciones:** El usuario puede ejecutar `sudo` en el servidor.
- **Flujo principal:**
  1. Al inicio de cualquier operación de instalación, `DistroDetector` lee `/etc/os-release`
  2. Identifica la familia de la distribución: Debian, RedHat/Fedora, SUSE
  3. `PackageManager` selecciona el gestor: `apt-get` (Debian/Ubuntu), `dnf` (Fedora/RHEL), `zypper` (openSUSE)
  4. Cada comando de instalación se ejecuta con `sudo <pkg-manager> install -y <paquete>`
  5. Para Certbot: en Debian/Ubuntu usa snap; en Fedora usa `dnf install certbot python3-certbot-nginx`; en openSUSE usa `zypper install certbot`
- **Flujo alternativo:** Si la distribución no es reconocida, el CLI muestra error claro indicando las distribuciones soportadas y aborta.
- **Postcondiciones:** Todos los paquetes necesarios están instalados independientemente de la distribución.
- **Prioridad:** `MUST`

### RF-010: Modo interactivo con menú y asistente guiado

- **Descripción:** El sistema debe ofrecer un modo interactivo accesible ejecutando `gen-cerbot` sin argumentos, que presente un menú principal navegable y, al generar un certificado, guíe al usuario con un asistente paso a paso recogiendo todos los parámetros necesarios y mostrando la salida de ejecución en tiempo real.
- **Actor:** Usuario (consola)
- **Precondiciones:** La herramienta está instalada y el usuario tiene una terminal con soporte de colores (ANSI).
- **Flujo principal:**
  1. El usuario ejecuta `gen-cerbot` sin argumentos
  2. Se muestra el menú principal con opciones: Generar certificado, Listar, Renovar, Eliminar, Salir
  3. El usuario navega con las flechas del teclado y selecciona con Enter
  4. Si elige **Generar certificado**, el asistente solicita en secuencia:
     - **Subdominio**: campo de texto libre con validación de formato de dominio
     - **Puerto del servicio dockerizado**: campo numérico (1–65535) con valor por defecto 8000
     - **Familia de paquetes**: selección entre `deb` (Debian/Ubuntu) y `rpm` (Fedora/openSUSE)
     - **Servidor web**: selección entre `nginx`, `apache`, `traefik`
     - **Email para Let's Encrypt**: campo de texto con validación de formato email
     - **Nombre del proyecto**: campo de texto libre (para nombrar el archivo de config)
  5. Se muestra una pantalla de resumen con todos los parámetros capturados y una confirmación `¿Continuar? [Sí/No]`
  6. Al confirmar, se ejecuta el proceso y la salida de cada paso (instalación, configuración, Certbot) se imprime en tiempo real con indicadores visuales (`[✔]`, `[→]`, `[✗]`)
  7. Al finalizar, se muestra la URL HTTPS resultante y el menú principal vuelve a aparecer
- **Flujo alternativo A:** Si el usuario selecciona `No` en la confirmación, regresa al menú principal sin ejecutar nada.
- **Flujo alternativo B:** Si ocurre un error en algún paso, se muestra `[✗]` con el mensaje de error y la opción de reintentar o volver al menú.
- **Flujo alternativo C:** El usuario puede salir con `Ctrl+C` en cualquier momento; la herramienta muestra un mensaje de salida limpio.
- **Postcondiciones:** El dominio tiene HTTPS configurado y el menú principal vuelve a mostrarse.
- **Prioridad:** `MUST`

### RF-011: Soporte multi-idioma (i18n) en la interfaz interactiva

- **Descripción:** La interfaz interactiva debe soportar múltiples idiomas. El idioma por defecto es **inglés**. Antes de mostrar el menú principal, el sistema debe presentar un selector de idioma (o respetar el flag `--lang`) para que el usuario elija el idioma de la sesión. La preferencia se guarda en `~/.config/gen_cerbot/config.toml` y se usa automáticamente en sesiones posteriores.
- **Actor:** Usuario (consola)
- **Precondiciones:** El sistema tiene al menos los archivos de locale `en.json` y `es.json` disponibles.
- **Flujo principal:**
  1. El usuario ejecuta `gen-cerbot` sin argumentos
  2. Si no existe preferencia guardada y no se pasó `--lang`, el sistema muestra un prompt de selección de idioma:
     ```
     Select your language / Selecciona tu idioma:
      ❯  English
         Español
     ```
  3. El usuario selecciona un idioma; la selección se persiste en `~/.config/gen_cerbot/config.toml`
  4. El menú principal se presenta completamente en el idioma seleccionado
- **Flujo alternativo A:** El usuario pasa `--lang en` o `--lang es` — el selector se omite y se usa el idioma indicado.
- **Flujo alternativo B:** Sesiones posteriores cargan el idioma desde `config.toml` y omiten el selector automáticamente.
- **Flujo alternativo C:** Si el archivo de locale solicitado no existe, se usa `en` como fallback sin error.
- **Postcondiciones:** Todos los textos de la interfaz interactiva (menú, asistente, resumen, indicadores, errores) se muestran en el idioma elegido.
- **Prioridad:** `MUST`

### RF-012: Distribución como paquete instalable (PyPI, .deb, .rpm)

- **Descripción:** La herramienta debe estar disponible en tres formatos de distribución para facilitar la adopción en diferentes entornos: paquete Python en PyPI (`pip install gen-cerbot`), paquete nativo Debian/Ubuntu (`.deb`), y paquete nativo RPM para Fedora y openSUSE (`.rpm`). Los paquetes nativos deben instalar el comando `gen-cerbot` sin exponer al usuario a detalles de Python.
- **Actor:** Administrador de sistema / DevOps
- **Flujo pip/PyPI:**
  1. `pip install gen-cerbot` instala la última versión desde PyPI
  2. El comando `gen-cerbot` queda disponible en el PATH del entorno activo
- **Flujo .deb (Debian/Ubuntu):**
  1. `sudo apt install ./gen-cerbot_<version>_all.deb` o via repositorio
  2. El paquete declara dependencias (`python3 >= 3.11`, `python3-pip`) y el postinst instala las dependencias Python
  3. `gen-cerbot` queda disponible en `/usr/bin/gen-cerbot`
- **Flujo .rpm (Fedora/openSUSE):**
  1. `sudo dnf install ./gen-cerbot-<version>-1.noarch.rpm` (Fedora) o `sudo zypper install ./gen-cerbot-*.rpm`
  2. El `.spec` declara `Requires: python3 >= 3.11` y las dependencias necesarias como sub-paquetes
  3. `gen-cerbot` queda disponible en `/usr/bin/gen-cerbot`
- **Postcondiciones:** La herramienta está instalada y el comando `gen-cerbot --version` funciona.
- **Prioridad:** `MUST`

### RF-013: Suite de pruebas automatizadas (unit + integración)

- **Descripción:** El proyecto debe incluir una suite de tests automatizados que cubra la lógica de negocio mediante tests unitarios y los flujos críticos de generación de archivos mediante tests de integración. Los tests deben ejecutarse sin red, sin `sudo` real y sin servidores web instalados, usando mocks y fixtures estáticas.
- **Actor:** Desarrollador / CI pipeline
- **Requisitos de tests unitarios:**
  - Cada módulo en `src/gen_cerbot/` debe tener un archivo `tests/unit/test_<modulo>.py` correspondiente.
  - Todos los tests unitarios deben pasar con `pytest -m unit` sin acceso a red ni a `/etc/` real.
  - `SystemRunner` debe mockearse en todos los tests unitarios — ningún test unitario ejecuta subprocesos reales.
  - `DistroDetector` debe probarse con al menos 4 fixtures de `/etc/os-release`: Ubuntu 22.04, Debian 12, Fedora 40, openSUSE Leap 15.5 y una distribución desconocida.
  - Los tres `PackageManager` (`Apt`, `Dnf`, `Zypper`) deben probarse de forma independiente verificando que la construcción del comando sea correcta.
  - `ApacheProvider` debe probarse con los tres `DistroFamily` para verificar que el nombre del paquete Apache y el template usado sean los correctos.
  - `GenerateWizard` debe probarse con respuestas predefinidas usando `questionary.unsafe_ask()` para cada campo, incluyendo casos de validación fallida (email inválido, puerto fuera de rango).
  - `LocaleManager.t("clave")` debe retornar el texto del idioma activo; para claves inexistentes en el idioma secundario, debe retornar el texto en inglés sin lanzar excepción.
- **Requisitos de tests de integración:**
  - Los tests de integración deben usar `tmp_path` de pytest — nunca escriben en el sistema de archivos real.
  - Debe existir un test que verifique que `NginxProvider.configure()` genera un archivo de configuración con el dominio y el puerto del backend correctamente interpolados.
  - Debe existir un test que verifique que `ApacheProvider.configure()` genera templates distintos para `DistroFamily.DEBIAN`, `REDHAT` y `SUSE`.
  - Debe existir un test que verifique que `TraefikProvider.configure()` crea `acme.json` con permisos 600 y genera `docker-compose.yml` funcional.
  - Debe existir un test que verifique el parseo de la salida de `certbot certificates` contra la fixture `tests/fixtures/certbot-outputs/certificates_ok.txt`.
  - Debe existir un test de flujo completo de `CertbotService.generate()` con todos los componentes reales excepto `SystemRunner` (mockeado) y el sistema de archivos (`tmp_path`).
- **Postcondiciones:** `pytest -m "unit or integration"` pasa con cobertura > 80% en entorno de CI sin red ni privilegios.
- **Prioridad:** `MUST`

---

## 7. Requisitos No Funcionales

### Compatibilidad del sistema

- **Familia Debian:** Ubuntu 20.04 LTS, 22.04 LTS y 24.04 LTS / Debian 11 (Bullseye) y 12 (Bookworm)
- **Familia RedHat:** Fedora 38, 39, 40
- **Familia SUSE:** openSUSE Leap 15.5+ / openSUSE Tumbleweed
- Python 3.11 o superior

### Rendimiento

- El comando `generate` debe completarse en menos de 5 minutos en condiciones normales (excluyendo tiempo de descarga de paquetes en primera instalación)
- El comando `list` debe responder en menos de 10 segundos

### Seguridad

- El CLI debe advertir cuando se ejecuta como root y abortar; los privilegios elevados se obtienen internamente vía `sudo` de forma granular
- `sudo` se invoca únicamente en los comandos que lo requieren (instalación de paquetes, escritura en `/etc/`, reinicio de servicios) — no se eleva todo el proceso
- Los archivos `acme.json` de Traefik deben generarse con permisos 600
- Las claves privadas generadas nunca deben imprimirse en stdout ni en logs
- El CLI nunca debe loguear contraseñas ni tokens

### Usabilidad

- Mensajes de error deben ser claros y accionables (indicar qué salió mal y cómo resolverlo)
- El CLI debe incluir `--help` detallado en cada subcomando
- La salida estándar debe usar colores para distinguir INFO, WARNING y ERROR

### Calidad y Testing

- Cobertura de tests > 80% global; módulos críticos (`utils/system.py`, `utils/distro.py`) > 90%
- El código debe seguir PEP 8 y estar formateado con `ruff`
- Tipo de anotaciones (type hints) en todas las funciones públicas

### Portabilidad

- La herramienta debe ser instalable vía `pip` como paquete estándar publicado en PyPI
- La herramienta debe poder instalarse como paquete nativo `.deb` en Debian/Ubuntu sin necesidad de Python explícito por parte del usuario
- La herramienta debe poder instalarse como paquete nativo `.rpm` en Fedora y openSUSE sin necesidad de Python explícito por parte del usuario
- Los archivos de configuración generados deben estar basados en plantillas (Jinja2) versionadas en el repositorio

---

## 8. Restricciones y Dependencias

### Restricciones Técnicas

- Requiere acceso a internet para contactar los servidores ACME de Let's Encrypt
- El puerto 80 debe estar libre durante el proceso de validación HTTP-01 de Let's Encrypt
- El usuario que ejecuta el CLI debe tener acceso a `sudo` (no se requiere ejecutar como root)
- Certbot se instala por distro: snap en Debian/Ubuntu (requiere `snapd`), `dnf` en Fedora, `zypper` en openSUSE
- Se require `/etc/os-release` disponible para la detección de distribución (presente en todas las distros soportadas)

### Restricciones de Let's Encrypt

- Rate limits: 50 certificados por dominio registrado por semana
- Los certificados tienen validez de 90 días
- El servidor de ACME challenge debe poder recibir peticiones HTTP en el puerto 80

### Dependencias Externas

| Dependencia | Tipo | Propósito | Estado |
|---|---|---|---|
| Let's Encrypt / ACME | Servicio externo | Emisión de certificados | Requerido |
| Certbot | Herramienta del sistema | Cliente ACME | Instalado automáticamente por gen_cerbot |
| Nginx / Apache | Servidor web | Servidor a configurar | Instalado automáticamente por gen_cerbot |
| apt / dnf / zypper | Gestor de paquetes del sistema | Instalación de dependencias | Nativo de la distro |
| Docker | Runtime | Para modo Traefik | Pre-instalado por usuario |
| snapd | Gestor de paquetes | Para instalar Certbot | Requerido en Ubuntu/Debian |
| python3-build / twine | Herramienta de build | Construcción y publicación del wheel en PyPI | Solo en entorno de desarrollo |
| fakeroot / dpkg-dev / debhelper / dh-python | Herramientas de build | Construcción del paquete `.deb` | Solo en entorno de build Debian |
| rpm-build / python3-devel | Herramientas de build | Construcción del paquete `.rpm` | Solo en entorno de build Fedora/SUSE |

---

## 9. User Stories

### Épica 1: Generación de certificados

**US-001:** Como DevOps, quiero ejecutar un único comando para configurar HTTPS en Nginx, para no tener que recordar la secuencia de comandos manual.
- Criterios de aceptación:
  - [ ] El comando `gen-cerbot generate --server nginx --domain X --port Y --project Z` completa sin errores
  - [ ] El dominio responde por HTTPS con un certificado válido de Let's Encrypt
  - [ ] La configuración de Nginx incluye headers de seguridad y proxy settings correctos

**US-002:** Como desarrollador, quiero soporte para Apache, para poder usar la misma herramienta independientemente del servidor web de mi proyecto.
- Criterios de aceptación:
  - [ ] El comando funciona con `--server apache`
  - [ ] El VirtualHost generado tiene ProxyPass configurado correctamente
  - [ ] El certificado se obtiene con el plugin certbot-apache

**US-003:** Como DevOps que usa Docker, quiero generar configuración de Traefik con HTTPS automático, para no configurar Certbot manualmente en contenedores.
- Criterios de aceptación:
  - [ ] Se generan `docker-compose.yml` y `traefik.yml` funcionales
  - [ ] `acme.json` tiene permisos 600
  - [ ] Las instrucciones post-generación son claras

### Épica 2: Gestión de certificados

**US-004:** Como administrador, quiero ver el estado de todos mis certificados, para saber cuáles están próximos a expirar.
- Criterios de aceptación:
  - [ ] `gen-cerbot list` muestra dominio, servidor, fecha de expiración y estado
  - [ ] Los certificados con menos de 30 días de validez se muestran con alerta visual

**US-005:** Como DevOps, quiero renovar certificados con un único comando, para mantener el servicio HTTPS sin interrupciones.
- Criterios de aceptación:
  - [ ] `gen-cerbot renew` funciona sin parámetros adicionales
  - [ ] Se puede especificar un dominio individual con `--domain`
  - [ ] El comando es idempotente (ejecutarlo cuando no hay renovación pendiente no produce error)

### Épica 3: Seguridad y confiabilidad

**US-006:** Como técnico de seguridad, quiero que el CLI valide el DNS antes de solicitar el certificado, para evitar errores de Certbot causados por DNS mal configurado.
- Criterios de aceptación:
  - [ ] Si el DNS del dominio no resuelve a la IP del servidor, el CLI muestra advertencia clara
  - [ ] Con `--skip-dns-check` se puede omitir esta validación
  - [ ] El mensaje de error indica qué IP se esperaba y cuál se encontró

### Épica 4: Modo interactivo

**US-007:** Como administrador que usa la herramienta por primera vez, quiero un menú interactivo, para no tener que recordar la sintaxis de los comandos.
- Criterios de aceptación:
  - [ ] Ejecutar `gen-cerbot` sin argumentos muestra el menú principal
  - [ ] La navegación funciona con las flechas del teclado y Enter
  - [ ] Las 4 opciones principales están disponibles: Generar, Listar, Renovar, Eliminar

**US-008:** Como técnico de infraestructura, quiero un asistente guiado para generar certificados, para asegurarme de no olvidar ningún parámetro.
- Criterios de aceptación:
  - [ ] El asistente solicita: subdominio, puerto del servicio, familia de paquetes (`deb`/`rpm`) y servidor web
  - [ ] Los campos tienen validación en línea (formato de dominio, rango de puerto)
  - [ ] Se muestra pantalla de resumen con todos los valores antes de ejecutar
  - [ ] La confirmación `¿Continuar?` previene ejecuciones accidentales

**US-009:** Como usuario, quiero ver la salida de ejecución en tiempo real durante la generación del certificado, para saber en qué paso está el proceso y detectar errores rápidamente.
- Criterios de aceptación:
  - [ ] Cada paso muestra su estado: `[→]` en progreso, `[✔]` completado, `[✗]` error
  - [ ] Los comandos `sudo` ejecutados se muestran en pantalla
  - [ ] Si ocurre un error, se muestra el mensaje del sistema y se ofrece reintentar o salir
  - [ ] Al finalizar correctamente se muestra la URL HTTPS con indicador de éxito

**US-010:** Como DevOps que automatiza con scripts, quiero que todos los comandos interactivos también funcionen como flags CLI, para poder usar la herramienta en CI/CD sin intervención manual.
- Criterios de aceptación:
  - [ ] `gen-cerbot generate --server nginx --domain X --port Y --pkg-family deb --project Z` funciona sin modo interactivo
  - [ ] El flag `--no-interactive` deshabilita cualquier prompt y falla con error si falta algún parámetro requerido

**US-011:** Como administrador internacional, quiero seleccionar el idioma de la interfaz antes de empezar, para poder operar la herramienta en mi lengua nativa.
- Criterios de aceptación:
  - [ ] Al ejecutar `gen-cerbot` por primera vez (sin preferencia guardada) se muestra un selector de idioma antes del menú
  - [ ] El idioma seleccionado se persiste en `~/.config/gen_cerbot/config.toml` y no vuelve a preguntar
  - [ ] El flag `--lang en|es` omite el selector y fuerza el idioma en esa sesión
  - [ ] Todos los textos de la interfaz interactiva (menú, asistente, confirmaciones, errores) se muestran en el idioma elegido
  - [ ] Si no hay preferencia y no se pasa `--lang`, el idioma por defecto es inglés
  - [ ] Se soportan al menos `en` (English) y `es` (Español) en la v1.0

### Épica 5: Distribución y empaquetado

**US-012:** Como administrador de sistemas en Debian/Ubuntu, quiero instalar `gen_cerbot` con `apt install` o `dpkg -i`, para no necesitar Python ni pip configurados explícitamente.
- Criterios de aceptación:
  - [ ] Existe un archivo `.deb` descargable en GitHub Releases para cada versión
  - [ ] `sudo dpkg -i gen-cerbot_<version>_all.deb` instala la herramienta correctamente
  - [ ] `gen-cerbot --version` funciona tras la instalación sin configuración adicional
  - [ ] El paquete pasa `lintian` sin errores graves (solo informativos permitidos)
  - [ ] La desinstalación con `sudo apt remove gen-cerbot` limpia correctamente

**US-013:** Como administrador de sistemas en Fedora u openSUSE, quiero instalar `gen_cerbot` con `dnf` o `zypper`, para integrarla en mi flujo de gestión de paquetes nativo.
- Criterios de aceptación:
  - [ ] Existe un archivo `.rpm` descargable en GitHub Releases para cada versión
  - [ ] `sudo dnf install ./gen-cerbot-<version>-1.noarch.rpm` funciona en Fedora 40
  - [ ] `sudo zypper install ./gen-cerbot-<version>-1.noarch.rpm` funciona en openSUSE Leap 15.5
  - [ ] `gen-cerbot --version` funciona tras la instalación
  - [ ] El paquete pasa `rpmlint` sin errores graves

**US-014:** Como desarrollador Python, quiero instalar `gen_cerbot` con `pip install gen-cerbot` desde PyPI, para integrarlo en mis entornos virtuales o herramientas de aprovisionamiento.
- Criterios de aceptación:
  - [ ] `pip install gen-cerbot` instala la última versión estable desde PyPI
  - [ ] `pip install gen-cerbot==<version>` permite instalar versiones específicas
  - [ ] El paquete incluye wheel (`.whl`) para instalación rápida sin compilación
  - [ ] `gen-cerbot --version` muestra la versión correcta tras la instalación

---

## 10. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Rate limit de Let's Encrypt excedido en desarrollo | Alta | Medio | Usar `--staging` para pruebas con certificados de prueba |
| Cambios en API de Certbot / snap | Baja | Alto | Abstracción del proveedor Certbot con tests de integración |
| Puerto 80 bloqueado por otro proceso | Media | Alto | Validación previa del puerto y mensaje de error claro |
| DNS propagation lag | Media | Medio | Mensaje informativo + flag `--skip-dns-check` |
| Diferencias entre distros Linux | Media | Medio | Tests en matriz de distros (Ubuntu 20/22/24, Debian 11/12) |
| Dependencias Python no disponibles como paquetes .deb/.rpm | Media | Medio | Usar `dh_python3` + `pip install --prefix` en postinst; listar dependencias explícitas en .spec |
| Lintian / rpmlint reportan errores en paquetes | Media | Bajo | Seguir guías de empaquetado Debian Policy y Fedora Packaging Guidelines desde el inicio |
| Rotura de pip install en entornos con Python gestionado por el sistema (PEP 668) | Media | Medio | Documentar uso de `pipx install gen-cerbot` como método de instalación recomendado |

---

## 11. Timeline Estimado

| Fase | Duración Estimada | Entregable |
|---|---|---|
| Fase 1: Foundation | 1 semana | Estructura del proyecto, CLI esqueleto, tests |
| Fase 2: Nginx Provider | 1 semana | Provider Nginx completo y testeado |
| Fase 3: Apache + Traefik Providers | 1 semana | Providers Apache y Traefik |
| Fase 4: Certbot Manager | 1 semana | Integración Certbot completa |
| Fase 5: Operaciones (list/renew/remove) | 1 semana | Todos los subcomandos |
| Fase 6: Testing, Hardening & Empaquetado | 2 semanas | Cobertura > 80%, docs; wheel PyPI + paquete .deb + paquete .rpm |
| Fase 7: Modo Interactivo | 1 semana | Menú principal + asistente generate + salida en tiempo real |
| Fase 8: Soporte i18n | 1 semana | Selector de idioma, LocaleManager, locales en/es |

---

## Historial de Cambios

| Versión | Fecha | Autor | Cambios |
|---|---|---|---|
| 1.0 | 2026-03-31 | Ernesto Crespo | Versión inicial: PRD base con RF-001..RF-008, Épicas 1-3, 6 user stories, timeline 6 fases |
| 1.1 | 2026-03-31 | Ernesto Crespo | Multi-distro: RF-009 detección automática gestor de paquetes y sudo interno; actualización de constraints y dependencias (dnf, zypper) |
| 1.2 | 2026-03-31 | Ernesto Crespo | Modo interactivo: RF-010 modo interactivo con menú y asistente guiado; Épica 4 con US-007..US-010; timeline ampliado a Fase 7 |
| 1.3 | 2026-03-31 | Ernesto Crespo | Soporte i18n: RF-011 selector de idioma previo al menú, flag --lang, preferencia persistida; US-011; Fase 8 al timeline |
| 1.4 | 2026-03-31 | Ernesto Crespo | Empaquetado nativo: RF-012 distribución PyPI/.deb/.rpm; Épica 5 con US-012..US-014; dependencias de build en tabla; RNF portabilidad extendida; Fase 6 ampliada a 2 semanas; 3 nuevos riesgos de empaquetado |
| 1.5 | 2026-03-31 | Ernesto Crespo | Especificaciones de testing: RF-013 suite de tests unitarios e integración con requisitos por módulo (DistroDetector fixtures, PackageManager 3 impls, ApacheProvider 3 DistroFamily, GenerateWizard unsafe_ask, LocaleManager fallback, 6 escenarios de integración, flujo completo CertbotService); RNF Calidad actualizado con cobertura mínima por módulo |

## Aprobaciones

| Rol | Nombre | Fecha | Estado |
|---|---|---|---|
| Tech Lead | Ernesto Crespo | | ☐ Pendiente |
