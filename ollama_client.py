from json import JSONDecodeError, dumps, load
from urllib.request import Request, urlopen


class MalformedResponseError(ValueError):
    """Ollama returned JSON that cannot be used as a model response."""


def generate_response(
    prompt: str,
    model: str,
    options: dict | None = None,
) -> str:

    url = "http://localhost:11434/api/generate"

    data = {"model": model, "prompt": prompt, "stream": False}

    if options is not None:
        data["options"] = options

    json_data = dumps(data).encode("utf-8")

    request = Request(
        url, data=json_data, headers={"Content-Type": "application/json"}, method="POST"
    )

    with urlopen(request, timeout=120) as response:
        try:
            result = load(response)
        except (JSONDecodeError, UnicodeDecodeError) as error:
            raise MalformedResponseError(
                "Invalid Ollama response: expected valid JSON."
            ) from error

    if not isinstance(result, dict):
        raise MalformedResponseError("Invalid Ollama response: expected a JSON object.")

    if not isinstance(result.get("response"), str):
        raise MalformedResponseError(
            "Invalid Ollama response: expected a string 'response' field."
        )

    return result["response"]
