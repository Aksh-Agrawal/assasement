"""Unit tests for schema, semantic, UTF-8, and integrity validation."""

import json
from pathlib import Path

import pytest

from app.content.hashing import sha256_bytes, sha256_file
from app.content.validator import (
    PackErrorCode,
    PackValidationError,
    validate_pack,
    validate_pack_bytes,
)

FIXTURES = Path("tests/fixtures/packs")


def error_codes(path: Path) -> set[PackErrorCode]:
    with pytest.raises(PackValidationError) as captured:
        validate_pack(path)
    return {issue.code for issue in captured.value.issues}


def test_valid_twenty_question_fixture_and_phase0_sample_pass() -> None:
    fixture = validate_pack(FIXTURES / "valid_20_questions.json")
    sample = validate_pack(Path("content/sample_biology.json"))

    assert fixture.summary.questions == 20
    assert sample.summary.set_id == "biology-cell-practice-01"
    assert sample.summary.questions == 20
    assert len(sample.sha256) == 64


@pytest.mark.parametrize(
    ("filename", "code"),
    [
        ("malformed.json", PackErrorCode.INVALID_JSON),
        ("unsupported_schema_version.json", PackErrorCode.UNSUPPORTED_SCHEMA_VERSION),
        ("duplicate_question_id.json", PackErrorCode.DUPLICATE_QUESTION_ID),
        ("duplicate_position.json", PackErrorCode.DUPLICATE_POSITION),
        ("three_options.json", PackErrorCode.INVALID_OPTION_KEYS),
        ("duplicate_option_key.json", PackErrorCode.INVALID_OPTION_KEYS),
        ("invalid_option_key.json", PackErrorCode.INVALID_OPTION_KEYS),
        ("invalid_correct_key.json", PackErrorCode.INVALID_CORRECT_KEY),
        ("empty_question_text.json", PackErrorCode.EMPTY_QUESTION_TEXT),
        ("invalid_media_ref.json", PackErrorCode.INVALID_MEDIA_REF),
    ],
)
def test_invalid_fixtures_have_structured_codes(filename: str, code: PackErrorCode) -> None:
    assert code in error_codes(FIXTURES / filename)


def test_invalid_utf8_empty_json_and_file_size_have_structured_errors() -> None:
    for data, code in (
        (b"\xff\xfe", PackErrorCode.INVALID_UTF8),
        (b"", PackErrorCode.INVALID_JSON),
    ):
        with pytest.raises(PackValidationError) as captured:
            validate_pack_bytes(data)
        assert captured.value.issues[0].code is code

    with pytest.raises(PackValidationError) as captured:
        validate_pack_bytes(b"{}", max_bytes=1)
    assert captured.value.issues[0].code is PackErrorCode.FILE_TOO_LARGE


def test_blank_option_text_and_non_contiguous_positions_are_rejected() -> None:
    raw = json.loads((FIXTURES / "valid_20_questions.json").read_text(encoding="utf-8"))
    raw["questions"][0]["options"][0]["text"] = "  "
    raw["questions"][1]["position"] = 22

    with pytest.raises(PackValidationError) as captured:
        validate_pack_bytes(json.dumps(raw).encode())
    codes = {issue.code for issue in captured.value.issues}
    assert PackErrorCode.EMPTY_REQUIRED_TEXT in codes
    assert PackErrorCode.INVALID_POSITION_SEQUENCE in codes


def test_safe_relative_media_path_is_accepted() -> None:
    raw = json.loads((FIXTURES / "valid_20_questions.json").read_text(encoding="utf-8"))
    raw["questions"][0]["media_ref"] = "media/cell/q001.png"

    validated = validate_pack_bytes(json.dumps(raw).encode())

    assert validated.question_set.questions[0].media_ref == "media/cell/q001.png"


def test_sha256_is_exact_deterministic_and_expected_hash_is_verified(tmp_path: Path) -> None:
    data = b"abc"
    known = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    path = tmp_path / "bytes.bin"
    path.write_bytes(data)
    assert sha256_bytes(data) == known
    assert sha256_bytes(data) == sha256_file(path)
    assert sha256_bytes(b"abd") != known

    pack_bytes = (FIXTURES / "valid_20_questions.json").read_bytes()
    expected = sha256_bytes(pack_bytes)
    assert validate_pack_bytes(pack_bytes, expected_sha256=expected).sha256 == expected
    with pytest.raises(PackValidationError) as captured:
        validate_pack_bytes(pack_bytes, expected_sha256="0" * 64)
    assert captured.value.issues[0].code is PackErrorCode.HASH_MISMATCH
