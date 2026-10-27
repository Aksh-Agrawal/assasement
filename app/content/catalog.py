"""Typed remote catalog metadata and deterministic local comparison."""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.data.repo import Repository

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class RemotePack:
    set_id: str
    version: int
    title: str
    subject: str
    chapter: str
    question_count: int
    size_bytes: int
    sha256: str
    published_at: datetime

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RemotePack":
        required = {
            "set_id",
            "version",
            "title",
            "subject",
            "chapter",
            "question_count",
            "size_bytes",
            "sha256",
            "published_at",
        }
        if set(value) != required:
            raise ValueError("Invalid catalog pack fields")
        digest = str(value["sha256"]).lower()
        if not _SHA256.fullmatch(digest):
            raise ValueError("Invalid catalog SHA-256")
        published_at = datetime.fromisoformat(str(value["published_at"]).replace("Z", "+00:00"))
        result = cls(
            set_id=str(value["set_id"]),
            version=int(value["version"]),
            title=str(value["title"]),
            subject=str(value["subject"]),
            chapter=str(value["chapter"]),
            question_count=int(value["question_count"]),
            size_bytes=int(value["size_bytes"]),
            sha256=digest,
            published_at=published_at,
        )
        if result.version < 1 or result.question_count < 1 or result.size_bytes < 1:
            raise ValueError("Invalid non-positive catalog metadata")
        if published_at.tzinfo is None or published_at.utcoffset() is None:
            raise ValueError("Catalog timestamp must include a timezone")
        return result


@dataclass(frozen=True, slots=True)
class ContentCatalog:
    schema_version: int
    packs: tuple[RemotePack, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ContentCatalog":
        if set(value) != {"schema_version", "packs"} or value["schema_version"] != 1:
            raise ValueError("Unsupported content catalog")
        if not isinstance(value["packs"], list):
            raise ValueError("Catalog packs must be a list")
        packs = tuple(RemotePack.from_dict(item) for item in value["packs"])
        identities = [(pack.set_id, pack.version) for pack in packs]
        if len(identities) != len(set(identities)):
            raise ValueError("Catalog contains duplicate set versions")
        return cls(schema_version=1, packs=packs)


class Availability(StrEnum):
    NOT_INSTALLED = "not_installed"
    NEW_VERSION = "new_version"
    ALREADY_INSTALLED = "already_installed"
    HISTORICAL_VERSION = "historical_version"


@dataclass(frozen=True, slots=True)
class CatalogComparison:
    pack: RemotePack
    availability: Availability

    @property
    def eligible(self) -> bool:
        return self.availability is not Availability.ALREADY_INSTALLED


def compare_catalog(catalog: ContentCatalog, repository: Repository) -> tuple[CatalogComparison, ...]:
    """Classify exact versions without treating remote absence as local deletion."""
    local = {(item.id, item.version) for item in repository.list_question_sets()}
    newest_local: dict[str, int] = {}
    for set_id, version in local:
        newest_local[set_id] = max(newest_local.get(set_id, 0), version)
    comparisons = []
    for pack in sorted(catalog.packs, key=lambda item: (item.subject, item.set_id, item.version)):
        identity = (pack.set_id, pack.version)
        if identity in local:
            availability = Availability.ALREADY_INSTALLED
        elif pack.set_id not in newest_local:
            availability = Availability.NOT_INSTALLED
        elif pack.version > newest_local[pack.set_id]:
            availability = Availability.NEW_VERSION
        else:
            availability = Availability.HISTORICAL_VERSION
        comparisons.append(CatalogComparison(pack, availability))
    return tuple(comparisons)
