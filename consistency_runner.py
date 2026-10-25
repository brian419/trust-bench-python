from urllib.error import HTTPError, URLError

from consistency_analyzer import analyze_consistency
from ollama_client import generate_response, MalformedResponseError


def run_consistency_experiment(
        prompts: list[str],
        repetitions: int = 3,
        model: str = "gemma3:1b",
        options: dict | None = None,
) -> list[dict]:
    if not 1 <= len(prompts) <= 3:
        raise ValueError("Provide between 1 and 3 prompts.")

    if any(
        not isinstance(prompt, str) or not prompt.strip()
        for prompt in prompts
    ):
        raise ValueError("Prompts must be nonempty strings.")

    if type(repetitions) is not int or not 1 <= repetitions <= 3:
        raise ValueError("Repetitions must be between 1 and 3.")

    if not isinstance(model, str) or not model.strip():
        raise ValueError("Model must be a nonempty string.")

    if options is not None and not isinstance(options, dict):
        raise ValueError("Options must be a dictionary.")

    results = []

    for prompt in prompts:
        attempts = []
        successful_responses = []

        for attempt_number in range(1, repetitions + 1):
            try:
                if options is None:
                    generated = generate_response(prompt, model)
                else:
                    generated = generate_response(
                        prompt,
                        model,
                        options=options,
                    )

                if not isinstance(generated, str):
                    raise TypeError("Model response must be a string.")

                attempts.append({
                    "attempt": attempt_number,
                    "status": "SUCCESS",
                    "generated": generated,
                })

                successful_responses.append(generated)

            except (HTTPError, URLError, TimeoutError, MalformedResponseError) as error:
                attempts.append({
                    "attempt": attempt_number,
                    "status": "ERROR",
                    "generated": None,
                    "error": str(error)
                })

        results.append({
            "prompt": prompt,
            "model": model,
            "options": options.copy() if options is not None else None,
            "attempts": attempts,
            "consistency": analyze_consistency(
                successful_responses
            ),
        })

    return results
