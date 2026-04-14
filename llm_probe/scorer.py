"""
scorer.py — Scoring logic for all probe types.

Scoring scale per probe: 0, 1, or 2
  2 = clear pass   (expected keyword found, clean completion)
  1 = partial pass (expected keyword found but completion is noisy/verbose)
  0 = fail         (no expected keyword in completion)

Consistency probes score differently:
  2 = all 3 runs contain the expected keyword
  1 = 2 of 3 runs contain it
  0 = 0 or 1 run contains it
"""

import re
from typing import List


def _contains_any(text: str, keywords: List[str], case_sensitive: bool = False) -> bool:
    """Check if text contains any of the expected keywords."""
    if not case_sensitive:
        text = text.lower()
        keywords = [k.lower() for k in keywords]
    return any(kw in text for kw in keywords)


def _is_clean(completion: str, max_len: int = 120) -> bool:
    """Heuristic: is the completion reasonably short and on-topic?"""
    return len(completion.strip()) <= max_len


def score_probe(probe: dict, completion: str) -> dict:
    """
    Score a single probe given a completion.
    Returns {"score": int, "passed": bool, "completion": str}
    """
    expected = probe.get("expected", [])
    case = probe.get("case_sensitive", False)
    found = _contains_any(completion, expected, case)

    if not found:
        score = 0
    elif _is_clean(completion):
        score = 2
    else:
        score = 1  # found but verbose

    return {
        "probe_id":    probe["id"],
        "description": probe["description"],
        "prompt":      probe["prompt"],
        "completion":  completion,
        "expected":    expected,
        "score":       score,
        "passed":      score > 0,
    }


def score_consistency_probe(probe: dict, completions: List[str]) -> dict:
    """
    Score a consistency probe given multiple completions.
    """
    expected = probe.get("expected", [])
    case = probe.get("case_sensitive", False)

    passing_runs = sum(
        1 for c in completions
        if _contains_any(c, expected, case)
    )
    total_runs = len(completions)

    if passing_runs == total_runs:
        score = 2
    elif passing_runs >= total_runs - 1:
        score = 1
    else:
        score = 0

    return {
        "probe_id":      probe["id"],
        "description":   probe["description"],
        "prompt":        probe["prompt"],
        "completions":   completions,
        "expected":      expected,
        "passing_runs":  passing_runs,
        "total_runs":    total_runs,
        "score":         score,
        "passed":        score > 0,
    }


def category_score(results: List[dict]) -> dict:
    """
    Compute overall category score from a list of probe results.
    Returns percentage (0-100) and counts.
    """
    total   = len(results)
    passed  = sum(1 for r in results if r["passed"])
    partial = sum(1 for r in results if r["score"] == 1)
    full    = sum(1 for r in results if r["score"] == 2)
    max_pts = total * 2
    earned  = sum(r["score"] for r in results)
    pct     = round((earned / max_pts) * 100) if max_pts > 0 else 0

    return {
        "total":   total,
        "passed":  passed,
        "partial": partial,
        "full":    full,
        "failed":  total - passed,
        "score":   pct,
    }


def overall_score(category_scores: dict) -> int:
    """Weighted average across all categories."""
    if not category_scores:
        return 0
    scores = [v["score"] for v in category_scores.values()]
    return round(sum(scores) / len(scores))


def grade(score: int) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90: return "A"
    if score >= 75: return "B"
    if score >= 60: return "C"
    if score >= 40: return "D"
    return "F"
