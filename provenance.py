"""Helpers for recording evaluation provenance."""

from hashlib import sha256
from json import dumps
from pathlib import Path
from platform import python_version


EXACT_SCORING_ID = "normalized-exact-v1"
ALTERNATIVE_SCORING_ID = "accepted-alternatives-v1"


def dataset_sha256(filename: str | Path) -> str:
    """Return the SHA-256 digest of a dataset's exact file bytes."""
    digest = sha256()

    with Path(filename).open("rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def bytes_sha256(contents: bytes) -> str:
    """Return the SHA-256 digest of exact bytes."""
    return sha256(contents).hexdigest()


def consistency_inputs_sha256(prompts: list[str], repetitions: int) -> str:
    """Fingerprint the prompts and repetition count."""
    inputs = {
        "prompts": prompts,
        "repetitions": repetitions,
    }

    encoded = dumps(
        inputs,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return bytes_sha256(encoded)


def python_runtime_version() -> str:
    """Return the Python version running TrustBench."""
    return python_version()
