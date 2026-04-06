"""Domain models for gen_cerbot."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ServerType(str, Enum):
    """Supported web server types."""

    NGINX = "nginx"
    APACHE = "apache"
    TRAEFIK = "traefik"


class DistroFamily(str, Enum):
    """Supported Linux distribution families."""

    DEBIAN = "debian"
    REDHAT = "redhat"
    SUSE = "suse"


class CertificateStatus(str, Enum):
    """Certificate lifecycle status."""

    OK = "ok"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class CertificateConfig(BaseModel):
    """Configuration for a certificate generation request."""

    domain: str
    email: str
    server_type: ServerType
    port: int = Field(default=8000, ge=1, le=65535)
    project_name: str = ""
    dry_run: bool = False
    staging: bool = False
    skip_dns_check: bool = False


class CertificateRecord(BaseModel):
    """Record of a managed certificate stored in the registry."""

    domain: str
    email: str
    server_type: ServerType
    distro_family: DistroFamily
    project_name: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime | None = None
    status: CertificateStatus = CertificateStatus.OK
    config_path: str = ""
