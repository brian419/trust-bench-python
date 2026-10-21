import json
import pytest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError
from ollama_client import generate_response

def test_generate_response():
    fake_data = {
        "model": "gemma3:1b",
        "response": "Paris",
        "done": True
    }

    fake_json = json.dumps(fake_data).encode("utf-8")

    fake_response = MagicMock()
    fake_response.read.return_value = fake_json
    fake_response.__enter__.return_value = fake_response

    with patch("ollama_client.urlopen", return_value=fake_response) as mock_urlopen:
        answer = generate_response(
            "What is the capital of France? Answer with only the English city name.",
            "gemma3:1b"
        )

        called_request = mock_urlopen.call_args.args[0]

    sent_data = json.loads(called_request.data)
    assert called_request.full_url == "http://localhost:11434/api/generate"
    assert called_request.get_method() == "POST"
    assert answer == "Paris"
    assert sent_data["model"] == "gemma3:1b"
    assert sent_data["prompt"] == "What is the capital of France? Answer with only the English city name."
    assert sent_data["stream"] is False


def test_generate_response_connection_error():
    with patch(
        "ollama_client.urlopen",
        side_effect=URLError("Connection refused")
    ):
        with pytest.raises(URLError):
            generate_response(
                "What is the capital of France? Answer with only the English city name.",
                "gemma3:1b"
            )


def test_generate_response_http_error():

    fake_error = HTTPError(
        url="http://localhost:11434/api/generate",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=None
    )

    with patch(
        "ollama_client.urlopen",
        side_effect=fake_error
    ):
        with pytest.raises(HTTPError) as error:
            generate_response(
                "What is the capital of France? Answer with only the English city name.",
                "missing-model"
            )

    assert error.value.code == 404


def test_generate_response_timeout():
    with patch(
        "ollama_client.urlopen",
        side_effect=TimeoutError("timed out")
    ):
        with pytest.raises(TimeoutError):
            generate_response(
                "What is the capital of France? Answer with only the English city name.",
                "gemma3:1b"
            )
