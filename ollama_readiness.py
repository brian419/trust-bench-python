"""Read-only checks for a local Ollama service and selected model."""

from dataclasses import dataclass
from json import loads
from shlex import quote
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MODELS_URL = "http://localhost:11434/api/tags"
CHECK_TIMEOUT_SECONDS = 2.0
MAX_RESPONSE_BYTES = 1024 * 1024


@dataclass(frozen=True)
class OllamaReadiness:
    status: str
    model: str
    message: str
    models: tuple[str, ...] | None = None


def _canonical_name(name: str) -> str:
    """Treat an omitted tag as latest without changing namespaces or case."""
    return name if ":" in name.rsplit("/", 1)[-1] else f"{name}:latest"


def check_ollama_readiness(model: str, *, allow_empty: bool = False) -> OllamaReadiness:
    """Inspect model availability without inference, installation or downloads.

    The socket timeout and response-size cap bound ordinary request failures.
    A listed model does not guarantee that a later inference request succeeds.
    """
    if not isinstance(model, str) or (not model.strip() and not allow_empty):
        return OllamaReadiness("INVALID_MODEL", "", "Enter an Ollama model name.")

    model = model.strip()
    request = Request(MODELS_URL, headers={"Accept": "application/json"}, method="GET")

    try:
        with urlopen(request, timeout=CHECK_TIMEOUT_SECONDS) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as error:
        return OllamaReadiness(
            "CHECK_FAILED", model,
            f"Ollama's model check returned HTTP {error.code}. "
            "Open or update Ollama, then choose Check Ollama again.",
        )
    except (URLError, TimeoutError, OSError):
        return OllamaReadiness(
            "UNAVAILABLE", model,
            "Cannot reach Ollama. Open it if installed, or use Get Ollama to "
            "install it. Then choose Check Ollama again. "
            "Reports and Compare still work without Ollama.",
        )

    try:
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Model list exceeds the response limit.")
        payload = loads(raw)
        if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
            raise ValueError("Expected a model list.")
        names = []
        for item in payload["models"]:
            if not isinstance(item, dict):
                raise ValueError("Expected model objects.")
            name = item.get("name") or item.get("model")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Expected model names.")
            names.append(name.strip())
    except ValueError:
        return OllamaReadiness(
            "CHECK_FAILED", model,
            "Ollama replied, but its model list could not be read. "
            "Open or update Ollama, then choose Check Ollama again.",
        )

    models = tuple(sorted(set(names), key=str.casefold))
    if not model:
        return OllamaReadiness(
            "MODELS_AVAILABLE" if models else "NO_MODELS", model,
            "Models refreshed. Choose a model from the dropdown, then Start Evaluation."
            if models else "Ollama is running, but no models are listed. "
            "Download a local model in Ollama, then choose Refresh Models.",
            models,
        )
    if _canonical_name(model) not in {_canonical_name(name) for name in models}:
        return OllamaReadiness(
            "MODEL_MISSING", model,
            f"Ollama is running, but '{model}' is not available. "
            "Choose an installed model from the dropdown, or check the name. "
            f"Download that model in Ollama, or run: ollama pull {quote(model)}. "
            "Then choose Check Ollama again. Downloads need internet and disk space.",
            models,
        )

    return OllamaReadiness(
        "READY", model,
        f"Ollama is available and '{model}' is listed. You can start an evaluation.",
        models,
    )
