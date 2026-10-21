from collections import Counter


def analyze_consistency(responses: list[str]) -> dict:
    normalized = [response.lower().strip() for response in responses]
    counts = Counter(normalized)

    if not normalized:
        return {
            "total_responses": 0,
            "unique_responses": 0,
            "disagreement_count": 0,
            "consistent": None,
        }

    most_common_count = counts.most_common(1)[0][1]

    return {
        "total_responses": len(normalized),
        "unique_responses": len(counts),
        "disagreement_count": len(normalized) - most_common_count,
        "consistent": len(counts) == 1,
    }
