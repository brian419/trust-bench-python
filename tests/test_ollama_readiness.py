"""Readiness checks inspect the local model list without generating responses."""

from io import BytesIO
from json import dumps
from shlex import quote
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from pytest import mark

from ollama_readiness import (
    CHECK_TIMEOUT_SECONDS,
    MAX_RESPONSE_BYTES,
    MODELS_URL,
    check_ollama_readiness,
)


@mark.parametrize(
    "requested, available",
    [
        ("gemma3:1b", {"name": "gemma3:1b"}),
        (" gemma3:1b ", {"model": "gemma3:1b"}),
        ("gemma3", {"name": "gemma3:latest"}),
        ("gemma3:latest", {"name": "gemma3"}),
        ("team/model", {"name": "team/model:latest"}),
        ("localhost:5000/team/model", {"name": "localhost:5000/team/model:latest"}),
    ],
)
def test_ready_model_and_latest_tag_aliases(requested, available):
    payload = dumps({"models": [available]}).encode()
    with patch("ollama_readiness.urlopen", return_value=BytesIO(payload)) as fetch:
        result = check_ollama_readiness(requested)
    assert result.status == "READY"
    assert result.model == requested.strip()
    request = fetch.call_args.args[0]
    assert request.full_url == MODELS_URL
    assert request.get_method() == "GET"
    assert request.data is None
    assert fetch.call_args.kwargs == {"timeout": CHECK_TIMEOUT_SECONDS}


@mark.parametrize("models", [[], [{"name": "gemma3:latest"}]])
def test_missing_selected_tag_has_actionable_instructions(models):
    with patch(
        "ollama_readiness.urlopen",
        return_value=BytesIO(dumps({"models": models}).encode()),
    ):
        result = check_ollama_readiness("gemma3:1b")
    assert result.status == "MODEL_MISSING"
    assert "ollama pull gemma3:1b" in result.message
    assert "Check Ollama again" in result.message


@mark.parametrize("model", ["", "  ", None, 7])
def test_invalid_model_does_not_contact_service(model):
    with patch("ollama_readiness.urlopen") as fetch:
        result = check_ollama_readiness(model)
    assert result.status == "INVALID_MODEL"
    fetch.assert_not_called()


@mark.parametrize(
    "error",
    [URLError("refused"), URLError(TimeoutError()), TimeoutError(), ConnectionError()],
)
def test_unreachable_service_does_not_claim_ollama_is_uninstalled(error):
    with patch("ollama_readiness.urlopen", side_effect=error):
        result = check_ollama_readiness("gemma3:1b")
    assert result.status == "UNAVAILABLE"
    assert "Open it if installed" in result.message
    assert "not installed" not in result.message
    assert "Reports and Compare" in result.message


def test_http_failure_is_not_misreported_as_missing_model():
    error = HTTPError(MODELS_URL, 500, "Failure", None, None)
    with patch("ollama_readiness.urlopen", side_effect=error):
        result = check_ollama_readiness("gemma3:1b")
    assert result.status == "CHECK_FAILED"
    assert "HTTP 500" in result.message


@mark.parametrize(
    "payload",
    [
        b"not json",
        b"\xff",
        b"null",
        b"[]",
        b"{}",
        b'{"models":null}',
        b'{"models":[null]}',
        b'{"models":[{}]}',
        b'{"models":[{"name":7}]}',
    ],
)
def test_malformed_model_list_is_unverified(payload):
    with patch("ollama_readiness.urlopen", return_value=BytesIO(payload)):
        result = check_ollama_readiness("gemma3:1b")
    assert result.status == "CHECK_FAILED"
    assert "model list could not be read" in result.message


def test_model_list_has_a_response_size_limit():
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = b"x" * (MAX_RESPONSE_BYTES + 1)
    with patch("ollama_readiness.urlopen", return_value=response):
        result = check_ollama_readiness("gemma3:1b")
    assert result.status == "CHECK_FAILED"
    response.read.assert_called_once_with(MAX_RESPONSE_BYTES + 1)


def test_download_hint_quotes_model_and_never_runs_commands():
    model = "model; echo unexpected"
    with (
        patch("ollama_readiness.urlopen", return_value=BytesIO(b'{"models":[]}')),
        patch("subprocess.run") as command,
    ):
        result = check_ollama_readiness(model)
    assert f"ollama pull {quote(model)}" in result.message
    command.assert_not_called()


def test_retry_recovers_after_service_and_model_become_available():
    with patch(
        "ollama_readiness.urlopen",
        side_effect=[
            URLError("refused"),
            BytesIO(b'{"models":[]}'),
            BytesIO(b'{"models":[{"name":"gemma3:1b"}]}'),
        ],
    ):
        statuses = [check_ollama_readiness("gemma3:1b").status for _ in range(3)]
    assert statuses == ["UNAVAILABLE", "MODEL_MISSING", "READY"]


def test_model_choices_preserve_names_remove_duplicates_and_sort():
    payload = dumps(
        {
            "models": [
                {"name": "z-team/model:Q4_K_M"},
                {"model": "Alpha:latest"},
                {"name": "z-team/model:Q4_K_M"},
                {"name": "gemma3:1b"},
            ]
        }
    ).encode()
    with patch("ollama_readiness.urlopen", return_value=BytesIO(payload)):
        result = check_ollama_readiness("missing:latest")
    assert result.status == "MODEL_MISSING"
    assert result.models == ("Alpha:latest", "gemma3:1b", "z-team/model:Q4_K_M")


@mark.parametrize(
    "models, status", [([], "NO_MODELS"), ([{"name": "gemma3:1b"}], "MODELS_AVAILABLE")]
)
def test_discovery_does_not_require_a_known_model_name(models, status):
    with patch(
        "ollama_readiness.urlopen",
        return_value=BytesIO(dumps({"models": models}).encode()),
    ):
        result = check_ollama_readiness(" ", allow_empty=True)
    assert result.status == status
    assert result.models == tuple(item["name"] for item in models)


def test_failed_discovery_does_not_supply_a_verified_empty_list():
    with patch("ollama_readiness.urlopen", side_effect=URLError("refused")):
        result = check_ollama_readiness("", allow_empty=True)
    assert result.status == "UNAVAILABLE"
    assert result.models is None
