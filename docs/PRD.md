# gen_cerbot — Product Requirements Document (PRD)

## Metadata

| Campo | Valor |
|---|---|
| **Producto** | gen_cerbot |
| **Autor** | Ernesto Crespo |
| **Estado** | `DRAFT` |
| **Versión** | 1.0 |
| **Fecha** | 2026-03-31 |
| **Última actualización** | 2026-03-31 |
| **Documentos relacionados** | [SPEC.md](./SPEC.md) · [ARCHITECTURE.md](./ARCHITECTURE.md) · [TASKS.md](./TASKS.md) |

---

## 1. Resumen Ejecutivo

`gen_cerbot` es una herramienta de línea de comandos (CLI) en Python que automatiza la configuración completa de TLS/SSL para servidores web Linux. Convierte una tarea manual de 20–30 minutos — instalar un servidor web, configurar un proxy reverso, obtener un certificado Let's Encrypt y activar la renovación automática — en un único comando o una experiencia guiada de menos de 5 minutos. Soporta Nginx, Apache y Traefik sobre Debian/Ubuntu, Fedora y openSUSE, y se distribuye como paquete instalable via `pip`, `.deb` y `.rpm`.

---

## 2. Problema

Configurar HTTPS en un servidor Linux nuevo implica una secuencia manual de pasos propensos a error:

1. Actualizar el sistema e instalar el servidor web con el gestor de paquetes correcto para la distro
2. Crear y activar archivos de configuración de virtual host o proxy reverso
3. Instalar Certbot (método diferente según la distribución: `snap`, `dnf` o `zypper`)
4. Solicitar el certificado con los flags correctos según el servidor web
5. Verificar que la configuración resultante es válida
6. Configurar la renovación automática

Este proceso varía en detalle según el servidor web y la distribución Linux, no está documentado de forma consistente, y es difícil de automatizar en pipelines CI/CD sin una herramienta dedicada. El script bash original `nginx-setup.sh` resolvía el problema parcialmente para Nginx en Ubuntu/Debian, pero no era extensible ni testeable.

---

## 3. Objetivos del Producto

| Objetivo | Métrica de éxito |
|---|---|
| Reducir el tiempo de configuración TLS/SSL | < 5 minutos desde cero en servidor limpio |
| Soportar los 3 servidores web más usados | Nginx, Apache y Traefik funcionan en v1.0 |
| Soportar las 3 familias de distros Linux | Debian/Ubuntu, Fedora y openSUSE funcionan en v1.0 |
| Ser usable sin documentación adicional | Modo interactivo guiado que no requiere leer el manual |
| Integrarse en pipelines CI/CD | Todos los pasos accesibles como flags CLI (`--no-interactive`) |
| Ser distribuible como paquete nativo | `pip install`, `apt install` y `dnf install` funcionales en v1.0 |
| Alcanzar calidad de software profesional | Cobertura de tests > 80%; `ruff` y `mypy` sin errores |

### Fuera de alcance (v1.0)

- Soporte para Windows o macOS
- Certificados de pago o de otras CAs (solo Let's Encrypt / ACME)
- Gestión de múltiples servidores remotos (SSH)
- Interfaz gráfica (GUI o web)
- Soporte para distribuciones distintas a las declaradas (CentOS, Arch, Alpine, etc.)
- Integración con servicios DNS para validación DNS-01

---

## 4. Usuarios Objetivo

### Perfil primario — DevOps / Administrador de sistemas

- **Contexto:** Gestiona múltiples servidores Linux, configura nuevos entornos regularmente, trabaja en distintas distribuciones
- **Pain point:** Configurar HTTPS manualmente consume tiempo y es fuente de errores; necesita automatizarlo en scripts o pipelines
- **Necesidades clave:** Modo comando directo, flag `--no-interactive`, compatibilidad multi-distro, salida verbose en tiempo real

### Perfil secundario — Desarrollador

- **Contexto:** Desarrolla aplicaciones web dockerizadas, configura su propio servidor de staging o producción
- **Pain point:** No conoce en detalle la diferencia entre configuraciones de Nginx y Apache, no sabe qué plugin de Certbot usar
- **Necesidades clave:** Modo interactivo guiado que le pregunte lo que necesita, mensajes de error claros y accionables

### Perfil terciario — Equipo internacional

- **Contexto:** Equipos con miembros en distintos países o idiomas
- **Pain point:** Herramientas en inglés únicamente generan fricción en equipos hispanohablantes
- **Necesidades clave:** Interfaz interactiva disponible en español e inglés, selección de idioma al primer uso

---

## 5. Características del Producto

### 5.1 Capacidades centrales (MUST — v1.0)

| Característica | Descripción |
|---|---|
| Generación de certificado TLS/SSL | Solicita e instala certificado Let's Encrypt para un dominio, configura el servidor web con proxy reverso y activa renovación automática |
| Soporte Nginx | Provider completo: instalación, configuración de virtual host, proxy reverso, verificación de sintaxis, activación del sitio |
| Soporte Apache | Provider completo con templates distintos por familia de distro; módulos `mod_proxy` y `mod_ssl` activados automáticamente |
| Soporte Traefik | Generación de `docker-compose.yml` y `traefik.yml` con ACME integrado; `acme.json` con permisos 600 |
| Multi-distro | Detección automática de la distro vía `/etc/os-release`; invocación del gestor de paquetes correcto (`apt`, `dnf`, `zypper`) |
| sudo interno | El CLI corre como usuario normal; privilegios elevados obtenidos de forma granular y transparente mediante `sudo` |
| Modo interactivo | Menú principal navegable + asistente paso a paso (6 campos con validación) + salida de ejecución en tiempo real |
| Modo comando directo | Todos los parámetros disponibles como flags CLI; compatible con scripts y pipelines CI/CD |
| Flag `--no-interactive` | Deshabilita todos los prompts; falla con error si falta algún parámetro requerido |
| Validación DNS previa | Verifica que el dominio resuelve a la IP del servidor antes de solicitar el certificado |
| Registro local de certificados | JSON en `~/.config/gen_cerbot/registry.json` que rastrea los certificados gestionados |
| Operaciones de ciclo de vida | `generate`, `list`, `renew` y `remove` para gestión completa del ciclo de vida |
| Soporte multi-idioma (i18n) | Interfaz interactiva en inglés (defecto) y español; selector de idioma al primer uso; flag `--lang` |
| Distribución PyPI | `pip install gen-cerbot` y `pipx install gen-cerbot` funcionales |
| Distribución .deb | Paquete nativo para Debian/Ubuntu instalable con `apt` o `dpkg` |
| Distribución .rpm | Paquete nativo para Fedora/openSUSE instalable con `dnf` o `zypper` |

### 5.2 Características de calidad (MUST — v1.0)

| Característica | Descripción |
|---|---|
| Suite de tests automatizados | 80 casos de prueba unitarios (TC-001..TC-070) + 10 de integración (TI-001..TI-010); cobertura > 80% |
| CI con GitHub Actions | Tests en Ubuntu 22.04/24.04 y Fedora 40 en cada PR; release automático al publicar un tag |
| Type hints y linting | `mypy --strict` y `ruff check` sin errores en todo el código |
| Idempotencia | Re-ejecutar el comando en un sistema ya configurado no produce errores ni cambios innecesarios |
| Dry-run mode | `--dry-run` muestra qué haría el comando sin aplicar ningún cambio real |

### 5.3 Deseables (SHOULD — backlog v1.1+)

- Soporte para certificados wildcard (`*.example.com`) via DNS-01
- Integración con repositorios de paquetes (PPA para Ubuntu, COPR para Fedora)
- Soporte para más idiomas (portugués, francés)
- Plugin para `ansible` o `terraform`

---

## 6. Requisitos No Funcionales Clave

| Atributo | Requisito |
|---|---|
| **Rendimiento** | `generate` completa en < 5 min (excluye descarga de paquetes en primera instalación) |
| **Seguridad** | Rechaza ejecución como root; `sudo` solo en comandos que lo requieren; claves privadas nunca en stdout |
| **Compatibilidad** | Python 3.11+; Debian 11/12, Ubuntu 20.04/22.04/24.04, Fedora 38/39/40, openSUSE Leap 15.5+ |
| **Usabilidad** | `--help` detallado en cada subcomando; errores claros e indicando cómo resolverlos |
| **Portabilidad** | Instalable via `pip`, `.deb` y `.rpm` sin exponer detalles de Python al usuario final |
| **Mantenibilidad** | Cobertura > 80%; cero `TODO` o `FIXME` sin ticket asociado en la release |

---

## 7. Restricciones

- Requiere acceso a internet para contactar los servidores ACME de Let's Encrypt
- El puerto 80 debe estar libre durante la validación HTTP-01
- El usuario debe tener acceso a `sudo` (no se requiere ejecutar como root)
- Certbot se instala por distro: `snap` en Debian/Ubuntu, `dnf` en Fedora, `zypper` en openSUSE

---

## 8. Métricas de Éxito

| Métrica | Objetivo v1.0 |
|---|---|
| Tiempo medio de configuración TLS/SSL (modo interactivo) | < 5 minutos en servidor limpio |
| Cobertura de tests automatizados | > 80% global; módulos críticos > 90% |
| Distribuciones Linux soportadas | 3 familias (Debian, RedHat/Fedora, SUSE) |
| Servidores web soportados | 3 (Nginx, Apache, Traefik) |
| Formatos de distribución | 3 (pip/PyPI, .deb, .rpm) |
| Tests E2E pasando en VM limpia | Ubuntu 22.04, Fedora 40, openSUSE Leap 15.5 |
| Idiomas de interfaz interactiva | 2 (English, Español) |

---

## 9. Roadmap de Alto Nivel

| Fase | Duración | Entregable principal |
|---|---|---|
| **Fase 1:** Foundation | 1 semana | Estructura del proyecto, modelos, utils (SystemRunner, DistroDetector, PackageManager) |
| **Fase 2:** Nginx Provider | 1 semana | Provider Nginx completo y testeado en las 3 distros |
| **Fase 3:** Apache + Traefik | 1 semana | Providers Apache (3 templates por distro) y Traefik |
| **Fase 4:** Certbot Manager | 1 semana | Instalación y gestión de certificados completa |
| **Fase 5:** CLI completo | 1 semana | Subcomandos `generate`, `list`, `renew`, `remove` funcionales |
| **Fase 6:** Testing & Packaging | 2 semanas | Cobertura > 80%; PyPI wheel + paquete .deb + paquete .rpm |
| **Fase 7:** Modo Interactivo | 1 semana | Menú, asistente guiado, salida en tiempo real |
| **Fase 8:** Soporte i18n | 1 semana | Selector de idioma, LocaleManager, locales en/es |
| **Total** | **9 semanas** | **Release v1.0.0** (objetivo: 2026-06-02) |

---

## 10. Aprobaciones

| Rol | Nombre | Fecha | Estado |
|---|---|---|---|
| Product Owner | Ernesto Crespo | — | ☐ Pendiente |
| Tech Lead | Por definir | — | ☐ Pendiente |

---

## Historial de Cambios

| Versión | Fecha | Autor | Cambios |
|---|---|---|---|
| 1.0 | 2026-03-31 | Ernesto Crespo | Versión inicial: problema, objetivos, usuarios, features MUST/SHOULD, RNF, restricciones, métricas de éxito, roadmap de 9 fases |
