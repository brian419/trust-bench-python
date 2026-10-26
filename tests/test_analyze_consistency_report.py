from collections import Counter
from hashlib import sha256
from json import dumps, loads

from pytest import raises

from analyze_consistency_report import REVIEW_SPEC, main


def make_source_report():
    generated_groups = [
        ["Gram", "gram", "gram"],
        [" Canberra", " Canberra", " Canberra"],
        ["T\n", "Adenine", "Adenine"],
    ]

    results = []

    for specification, responses in zip(
        REVIEW_SPEC,
        generated_groups,
    ):
        results.append(
            {
                "prompt": specification["prompt"],
                "attempts": [
                    {
                        "attempt": number,
                        "status": "SUCCESS",
                        "generated": response,
                    }
                    for number, response in enumerate(responses, start=1)
                ],
                "consistency": {
                    "total_responses": 3,
                    "unique_responses": len(
                        {response.lower().strip() for response in responses}
                    ),
                    "disagreement_count": (
                        len(responses)
                        - Counter(
                            response.lower().strip() for response in responses
                        ).most_common(1)[0][1]
                    ),
                    "consistent": (
                        len({response.lower().strip() for response in responses}) == 1
                    ),
                },
            }
        )

    return {
        "metadata": {
            "model": "gemma3:1b",
            "options": {
                "temperature": 0.7,
                "seed": 42,
                "num_predict": 64,
            },
        },
        "results": results,
    }


def write_source(tmp_path, report):
    source_path = tmp_path / "source.json"
    raw = dumps(report).encode("utf-8")
    source_path.write_bytes(raw)
    return source_path, sha256(raw).hexdigest()


def test_analyze_verified_report(tmp_path, monkeypatch):
    source_path, digest = write_source(
        tmp_path,
        make_source_report(),
    )
    monkeypatch.setattr("analyze_consistency_report.SOURCE_SHA256", digest)

    original_bytes = source_path.read_bytes()
    output_path = main(
        report_path=source_path,
        output_dir=tmp_path,
    )

    analysis = loads(output_path.read_text(encoding="utf-8"))

    assert analysis["metadata"]["source_sha256"] == digest
    assert analysis["summary"]["total_attempts"] == 9
    assert analysis["summary"]["classification_counts"] == {
        "CORRECT": 3,
        "FORMATTING_MISMATCH": 1,
        "INCORRECT": 5,
    }

    assert source_path.read_bytes() == original_bytes


def test_rejects_modified_source(tmp_path, monkeypatch):
    source_path, digest = write_source(
        tmp_path,
        make_source_report(),
    )
    monkeypatch.setattr("analyze_consistency_report.SOURCE_SHA256", digest)

    source_path.write_bytes(source_path.read_bytes() + b" ")

    with raises(ValueError, match="SHA-256 mismatch"):
        main(source_path, tmp_path)


def test_rejects_wrong_prompt(tmp_path, monkeypatch):
    source = make_source_report()
    source["results"][0]["prompt"] = "Different question"

    source_path, digest = write_source(tmp_path, source)
    monkeypatch.setattr("analyze_consistency_report.SOURCE_SHA256", digest)

    with raises(ValueError, match="prompts do not match"):
        main(source_path, tmp_path)
