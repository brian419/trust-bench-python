from hashlib import sha256
from platform import python_version

from pytest import raises

from provenance import (
    bytes_sha256,
    consistency_inputs_sha256,
    dataset_sha256,
    python_runtime_version,
)


def test_dataset_sha256_matches_known_digest(tmp_path):
    dataset = tmp_path / "dataset.json"
    contents = b'{"question": "What is 2 + 2?"}'

    dataset.write_bytes(contents)

    expected = sha256(contents).hexdigest()

    assert dataset_sha256(dataset) == expected


def test_identical_dataset_contents_have_same_hash(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    contents = b'[{"id": "test_001"}]'

    first.write_bytes(contents)
    second.write_bytes(contents)

    assert dataset_sha256(first) == dataset_sha256(second)


def test_modified_dataset_changes_hash(tmp_path):
    dataset = tmp_path / "dataset.json"
    dataset.write_text('{"expected": "Paris"}', encoding="utf-8")

    original_hash = dataset_sha256(dataset)

    dataset.write_text('{"expected": "London"}', encoding="utf-8")

    modified_hash = dataset_sha256(dataset)

    assert original_hash != modified_hash


def test_missing_dataset_raises_file_not_found(tmp_path):
    missing = tmp_path / "missing.json"

    with raises(FileNotFoundError):
        dataset_sha256(missing)


def test_bytes_sha256_matches_known_digest():
    contents = b'{"expected": "Paris"}'

    assert bytes_sha256(contents) == sha256(contents).hexdigest()


def test_bytes_sha256_detects_whitespace_changes():
    first = b'{"expected":"Paris"}'
    second = b'{"expected": "Paris"}'

    assert bytes_sha256(first) != bytes_sha256(second)


def test_consistency_inputs_same_values_same_hash():
    prompts = ["Question one?", "Question two?"]

    first = consistency_inputs_sha256(prompts, 3)
    second = consistency_inputs_sha256(prompts, 3)

    assert first == second
    assert len(first) == 64


def test_consistency_inputs_change_when_prompt_changes():
    first = consistency_inputs_sha256(["Question one?"], 3)
    second = consistency_inputs_sha256(["Different question?"], 3)

    assert first != second


def test_consistency_inputs_change_when_repetitions_change():
    first = consistency_inputs_sha256(["Question one?"], 3)
    second = consistency_inputs_sha256(["Question one?"], 2)

    assert first != second


def test_python_runtime_version_matches_environment():
    assert python_runtime_version() == python_version()
