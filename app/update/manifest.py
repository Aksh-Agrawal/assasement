"""Versioned update manifest parsing and canonical serialization."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema
from packaging.version import InvalidVersion, Version

from app.update.errors import ManifestError

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "update_manifest.schema.json"


def canonical_manifest_bytes(data: dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


@dataclass(frozen=True, slots=True)
class UpdateManifest:
    data: dict[str, Any]

    @classmethod
    def parse(cls, raw: bytes) -> "UpdateManifest":
        try:
            data = json.loads(raw)
            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(data)
            Version(data["release"]["version"])
            Version(data["release"]["min_supported_version"])
        except (json.JSONDecodeError, jsonschema.ValidationError, InvalidVersion, KeyError) as error:
            raise ManifestError("Update manifest is invalid") from error
        return cls(data)

    @property
    def version(self) -> Version:
        return Version(self.data["release"]["version"])

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_manifest_bytes(self.data)
