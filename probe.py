#!/usr/bin/env python3
"""
probe.py — llm-probe CLI entry point.

Usage:
    python probe.py --model llama3.1:8b
    python probe.py --model llama3.1:8b --backend ollama
    python probe.py --model llama3.1:8b --backend hf
    python probe.py --model llama3.1:8b --categories geometry reasoning
    python probe.py --model llama3.1:8b --verbose
    python probe.py --model llama3.1:8b --output-dir ./my_reports
"""

import argparse
import sys
import os
from datetime import datetime

# Ensure llm_probe package is importable from the project root
sys.path.insert(0, os.path.dirname(__file__))

from llm_probe.backends  import get_backend
from llm_probe.probes    import ALL_CATEGORIES
from llm_probe.scorer    import score_probe, score_consistency_probe, category_score, overall_score, grade
from llm_probe.reporter  import (
    print_header, print_category, print_summary,
    print_training_recommendations, save_json, save_markdown,
)


def run_category(category_key: str, backend, verbose: bool) -> tuple:
    """Run all probes in a category. Returns (results, cat_score_dict)."""
    cat    = ALL_CATEGORIES[category_key]
    label  = cat["label"]
    probes = cat["probes"]
    results = []

    print(f"  Running: {label}...", end="", flush=True)

    for probe in probes:
        if category_key == "consistency":
            runs = probe.get("runs", 3)
            completions = [
                backend.generate(probe["prompt"], max_tokens=60, temperature=0.7)
                for _ in range(runs)
            ]
            result = score_consistency_probe(probe, completions)
        else:
            completion = backend.generate(probe["prompt"], max_tokens=80, temperature=0.1)
            result = score_probe(probe, completion)

        results.append(result)

    cs = category_score(results)
    print(f" {cs['passed']}/{cs['total']} passed ({cs['score']}%)")
    return results, cs


def build_report(model_name: str, backend_name: str, all_results: dict, all_scores: dict) -> dict:
    """Assemble full report dict for JSON/Markdown output."""
    cats = {}
    for key in all_results:
        cats[key] = {
            "label":        ALL_CATEGORIES[key]["label"],
            "score_summary": all_scores[key],
            "results":      all_results[key],
        }
    return {
        "model":         model_name,
        "backend":       backend_name,
        "timestamp":     datetime.now().isoformat(),
        "overall_score": overall_score(all_scores),
        "grade":         grade(overall_score(all_scores)),
        "categories":    cats,
    }


def main():
    parser = argparse.ArgumentParser(
        description="llm-probe — evaluate a base LLM before fine-tuning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python probe.py --model llama3.1:8b
  python probe.py --model llama3.1:8b --categories geometry reasoning
  python probe.py --model llama3.1:8b --verbose
  python probe.py --model meta-llama/Meta-Llama-3.1-8B --backend hf
        """,
    )
    parser.add_argument(
        "--model", required=True,
        help="Model name. For Ollama: 'llama3.1:8b'. For HF: 'meta-llama/Meta-Llama-3.1-8B'",
    )
    parser.add_argument(
        "--backend", choices=["ollama", "hf"], default=None,
        help="Force backend. Default: auto-detect (tries Ollama first)",
    )
    parser.add_argument(
        "--categories", nargs="+",
        choices=list(ALL_CATEGORIES.keys()),
        default=list(ALL_CATEGORIES.keys()),
        help="Categories to run. Default: all",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Show individual probe completions in terminal output",
    )
    parser.add_argument(
        "--output-dir", default="./reports",
        help="Directory to save JSON and Markdown reports (default: ./reports)",
    )
    parser.add_argument(
        "--no-save", action="store_true",
        help="Skip saving report files",
    )

    args = parser.parse_args()

    # ── Backend ────────────────────────────────────────────────────────────
    print()
    print("  Detecting backend...")
    backend = get_backend(args.model, force=args.backend)
    print_header(args.model, backend.name())

    # ── Run probes ─────────────────────────────────────────────────────────
    print("  Running probes:\n")
    all_results = {}
    all_scores  = {}

    for key in args.categories:
        results, cs = run_category(key, backend, args.verbose)
        all_results[key] = results
        all_scores[key]  = cs

    print()

    # ── Terminal report ────────────────────────────────────────────────────
    for key in args.categories:
        label = ALL_CATEGORIES[key]["label"]
        print_category(label, all_scores[key], all_results[key], verbose=args.verbose)

    ov = overall_score(all_scores)
    gr = grade(ov)
    print_summary(ov, gr, all_scores)
    print_training_recommendations(all_scores)

    # ── Save files ─────────────────────────────────────────────────────────
    if not args.no_save:
        slug   = args.model.replace("/", "_").replace(":", "_")
        report = build_report(args.model, backend.name(), all_results, all_scores)
        json_path = save_json(report, args.output_dir, slug)
        md_path   = save_markdown(report, args.output_dir, slug)
        print(f"  Reports saved:")
        print(f"    JSON     : {json_path}")
        print(f"    Markdown : {md_path}")
        print()


if __name__ == "__main__":
    main()
