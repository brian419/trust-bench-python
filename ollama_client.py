import json
from urllib.request import Request, urlopen

def generate_response(prompt: str, model: str) -> str:
    url = "http://localhost:11434/api/generate"

    data = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    json_data = json.dumps(data).encode("utf-8")

    request = Request(
        url,
        data=json_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urlopen(request, timeout=120) as response:
        result = json.load(response)

    return result["response"]
