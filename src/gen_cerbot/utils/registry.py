"""CertRegistry — JSON file tracking managed certificates."""

from __future__ import annotations

import json
from pathlib import Path

from gen_cerbot.domain.models import CertificateRecord


class CertRegistry:
    """Manages a JSON registry of certificate records.

    Operations are idempotent — adding the same domain twice updates the record.
    """

    def __init__(self, registry_path: Path) -> None:
        self._path = registry_path
        self._records: dict[str, CertificateRecord] = {}
        self._load()

    def _load(self) -> None:
        """Load records from the JSON file."""
        if self._path.exists():
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for domain, record_data in data.items():
                self._records[domain] = CertificateRecord.model_validate(record_data)

    def _save(self) -> None:
        """Persist records to the JSON file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {domain: record.model_dump(mode="json") for domain, record in self._records.items()}
        self._path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def add(self, record: CertificateRecord) -> None:
        """Add or update a certificate record (idempotent)."""
        self._records[record.domain] = record
        self._save()

    def get(self, domain: str) -> CertificateRecord | None:
        """Get a certificate record by domain."""
        return self._records.get(domain)

    def remove(self, domain: str) -> bool:
        """Remove a certificate record. Returns True if it existed."""
        if domain in self._records:
            del self._records[domain]
            self._save()
            return True
        return False

    def list_all(self) -> list[CertificateRecord]:
        """List all certificate records."""
        return list(self._records.values())

    def exists(self, domain: str) -> bool:
        """Check if a domain is in the registry."""
        return domain in self._records
