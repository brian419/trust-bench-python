from json import dumps, load
from urllib.request import Request, urlopen

def generate_response(
        prompt: str,
        model: str,
        options: dict | None = None,
    ) -> str:

    url = "http://localhost:11434/api/generate"

    data = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    if options is not None:
        data["options"] = options

    json_data = dumps(data).encode("utf-8")

    request = Request(
        url,
        data=json_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urlopen(request, timeout=120) as response:
        result = load(response)

    return result["response"]
