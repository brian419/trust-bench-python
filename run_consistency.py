import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from consistency_runner import run_consistency_experiment


MODEL = "gemma3:1b"
REPETITIONS = 3

PROMPTS = [
    "What is the SI base unit of mass? Answer with only the unit name.",
    "What is the capital of Australia? Answer with only the city name.",
    "Which DNA base pairs with adenine? Answer with only the base name.",
]

OPTIONS = {
    "temperature": 0.7,
    "seed": 42,
    "num_predict": 64,
}


def main(report_dir: Path = Path("reports")) -> Path:
    results = run_consistency_experiment(
        prompts=PROMPTS,
        repetitions=REPETITIONS,
        model=MODEL,
        options=OPTIONS,
    )

    report = {
        "metadata": {
            "model": MODEL,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "repetitions": REPETITIONS,
            "prompt_count": len(PROMPTS),
            "options": OPTIONS.copy(),
        },
        "results": results,
    }

    report_dir.mkdir(parents=True, exist_ok=True)

    report_path = report_dir / f"consistency-{uuid4().hex}.json"

    with report_path.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print(f"Saved consistency report: {report_path}")
    return report_path


if __name__ == "__main__":
    main()
