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

    # Compare multiple models side by side:
    python probe.py --compare llama3.1:8b-text-q4_K_M mistral:7b-text gemma2:9b
"""

import argparse
import json
import sys
import os
from datetime import datetime

# Ensure llm_probe package is importable from the project root
sys.path.insert(0, os.path.dirname(__file__))

from llm_probe.backends  import get_backend
from llm_probe.probes    import ALL_CATEGORIES, DEEP_CATEGORIES, STANDARD_CATEGORIES
from llm_probe.scorer    import (score_probe, score_consistency_probe, score_mirror_pair,
                                  category_score, overall_score, grade)
from llm_probe.reporter  import (
    print_header, print_category, print_summary,
    print_training_recommendations, save_json, save_markdown,
)

# ── Colours ────────────────────────────────────────────────────────────────
RED    = "\033[0;31m"
GREEN  = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN   = "\033[0;36m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
NC     = "\033[0m"

def _sc(score):
    if score >= 75: return GREEN
    if score >= 50: return YELLOW
    return RED


def run_category(category_key: str, backend, verbose: bool) -> tuple:
    """Run all probes in a category. Returns (results, cat_score_dict)."""
    cat    = ALL_CATEGORIES[category_key]
    label  = cat["label"]
    probes = cat["probes"]
    results = []

    print(f"  Running: {label}...", end="", flush=True)

    # Mirror pairs — run both sides and score together
    if category_key == "bias":
        paired = {}
        for probe in probes:
            completion = backend.generate(probe["prompt"], max_tokens=80, temperature=0.1)
            paired[probe["id"]] = (probe, completion)

        processed = set()
        for probe_id, (probe, completion) in paired.items():
            if probe_id in processed:
                continue
            pair_id = probe.get("pair")
            if pair_id and pair_id in paired:
                probe_b, completion_b = paired[pair_id]
                result_a, result_b = score_mirror_pair(
                    probe, completion, probe_b, completion_b
                )
                results.extend([result_a, result_b])
                processed.add(probe_id)
                processed.add(pair_id)
            else:
                result = score_probe(probe, completion)
                results.append(result)
                processed.add(probe_id)

    elif category_key == "consistency":
        for probe in probes:
            runs = probe.get("runs", 3)
            completions = [
                backend.generate(probe["prompt"], max_tokens=60, temperature=0.7)
                for _ in range(runs)
            ]
            result = score_consistency_probe(probe, completions)
            results.append(result)

    else:
        for probe in probes:
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


def run_model(model_name: str, categories: list, backend_force: str = None) -> dict:
    """Run all probes for one model. Returns scores dict keyed by category."""
    print(f"\n  {BOLD}── {model_name} ──{NC}")
    backend = get_backend(model_name, force=backend_force)
    all_results = {}
    all_scores  = {}
    for key in categories:
        results, cs = run_category(key, backend, verbose=False)
        all_results[key] = results
        all_scores[key]  = cs
    return {
        "model":      model_name,
        "backend":    backend.name(),
        "scores":     all_scores,
        "results":    all_results,
        "overall":    overall_score(all_scores),
        "grade":      grade(overall_score(all_scores)),
        "timestamp":  datetime.now().isoformat(),
    }


def print_comparison(model_data: list, categories: list):
    """Print side-by-side comparison table to terminal."""
    names = [d["model"].split(":")[0][:12] for d in model_data]  # short names
    col   = 10
    pad   = 28

    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}{CYAN}║              llm-probe — Model Comparison                    ║{NC}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════╝{NC}\n")

    # Header row
    header = f"  {'Category':<{pad}}"
    for d in model_data:
        short = d["model"].split(":")[0][:col]
        header += f"  {short:>{col}}"
    print(f"{BOLD}{header}{NC}")
    print(f"  {'─' * pad}" + f"  {'─' * col}" * len(model_data))

    # Category rows
    for key in categories:
        label = ALL_CATEGORIES[key]["label"][:pad]
        row   = f"  {label:<{pad}}"
        for d in model_data:
            sc = d["scores"][key]["score"]
            c  = _sc(sc)
            row += f"  {c}{sc:>{col-1}}%{NC}"
        print(row)

    # Separator
    print(f"  {'─' * pad}" + f"  {'─' * col}" * len(model_data))

    # Overall row
    row = f"  {BOLD}{'Overall':<{pad}}{NC}"
    for d in model_data:
        sc = d["overall"]
        c  = _sc(sc)
        row += f"  {c}{BOLD}{sc:>{col-1}}%{NC}"
    print(row)

    # Grade row
    row = f"  {'Grade':<{pad}}"
    for d in model_data:
        row += f"  {d['grade']:>{col}}"
    print(row)
    print()

    # Winner per category
    print(f"{BOLD}  ── Strongest model per category: ─────────────────────────────{NC}\n")
    for key in categories:
        label  = ALL_CATEGORIES[key]["label"]
        scores = [(d["model"].split(":")[0], d["scores"][key]["score"]) for d in model_data]
        best   = max(scores, key=lambda x: x[1])
        tied   = [n for n, s in scores if s == best[1]]
        winner = " & ".join(tied) if len(tied) > 1 else best[0]
        print(f"  {label:<35} {GREEN}{winner}{NC} ({best[1]}%)")
    print()


def save_comparison(model_data: list, categories: list, output_dir: str) -> tuple:
    """Save comparison as JSON and Markdown."""
    os.makedirs(output_dir, exist_ok=True)
    ts    = datetime.now().strftime("%Y%m%d_%H%M")
    names = "_vs_".join(d["model"].replace(":", "_").replace("/", "_")[:12] for d in model_data)

    # JSON
    json_path = os.path.join(output_dir, f"compare_{names}_{ts}.json")
    with open(json_path, "w") as f:
        json.dump(model_data, f, indent=2)

    # Markdown
    md_path = os.path.join(output_dir, f"compare_{names}_{ts}.md")
    lines = [
        "# llm-probe — Model Comparison",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Scores",
        "",
    ]

    # Table header
    header = "| Category |" + "".join(f" {d['model'].split(':')[0]} |" for d in model_data)
    sep    = "|----------|" + "".join("---------|" for _ in model_data)
    lines += [header, sep]

    for key in categories:
        label = ALL_CATEGORIES[key]["label"]
        row   = f"| {label} |"
        for d in model_data:
            sc  = d["scores"][key]["score"]
            row += f" {sc}% |"
        lines.append(row)

    # Overall
    overall_row = "| **Overall** |" + "".join(f" **{d['overall']}%** |" for d in model_data)
    grade_row   = "| **Grade** |"   + "".join(f" **{d['grade']}** |"    for d in model_data)
    lines += [overall_row, grade_row, "", "---", "", "## Winner Per Category", ""]

    for key in categories:
        label  = ALL_CATEGORIES[key]["label"]
        scores = [(d["model"].split(":")[0], d["scores"][key]["score"]) for d in model_data]
        best   = max(scores, key=lambda x: x[1])
        tied   = [n for n, s in scores if s == best[1]]
        winner = " & ".join(tied) if len(tied) > 1 else best[0]
        lines.append(f"- **{label}**: {winner} ({best[1]}%)")

    lines += ["", "---", "", "## Pre-Training Recommendation for Forge", ""]
    lines.append("Based on the weakest categories across all models, priority SFT data:")
    lines.append("")

    avg_scores = {}
    for key in categories:
        avg = sum(d["scores"][key]["score"] for d in model_data) / len(model_data)
        avg_scores[key] = round(avg)

    for key, avg in sorted(avg_scores.items(), key=lambda x: x[1]):
        label = ALL_CATEGORIES[key]["label"]
        lines.append(f"- **{label}** (avg {avg}%) — {'high priority' if avg < 60 else 'medium priority' if avg < 75 else 'strong baseline'}")

    with open(md_path, "w") as f:
        f.write("\n".join(lines))

    return json_path, md_path


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
  python probe.py --compare llama3.1:8b-text-q4_K_M mistral:7b-text gemma2:9b
        """,
    )
    parser.add_argument(
        "--model", default=None,
        help="Model name. For Ollama: 'llama3.1:8b'. For HF: 'meta-llama/Meta-Llama-3.1-8B'",
    )
    parser.add_argument(
        "--compare", nargs="+", default=None, metavar="MODEL",
        help="Compare multiple models side by side",
    )
    parser.add_argument(
        "--backend", choices=["ollama", "hf"], default=None,
        help="Force backend. Default: auto-detect (tries Ollama first)",
    )
    parser.add_argument(
        "--categories", nargs="+",
        choices=list(ALL_CATEGORIES.keys()),
        default=None,
        help="Specific categories to run. Default: standard 6. Use --deep for all 9.",
    )
    parser.add_argument(
        "--deep", action="store_true",
        help="Run all 9 categories including bias, safety boundary, and residue probes",
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

    if not args.model and not args.compare:
        parser.error("Provide --model for a single run or --compare for multi-model comparison.")

    # Resolve which categories to run
    if args.categories:
        active_categories = args.categories
    elif args.deep:
        active_categories = DEEP_CATEGORIES
    else:
        active_categories = STANDARD_CATEGORIES
    args.categories = active_categories

    # ── Compare mode ───────────────────────────────────────────────────────
    if args.compare:
        print(f"\n{BOLD}  llm-probe — Comparing {len(args.compare)} models{NC}")
        print(f"  {DIM}Models: {', '.join(args.compare)}{NC}\n")
        model_data = []
        for model_name in args.compare:
            data = run_model(model_name, args.categories, args.backend)
            model_data.append(data)
        print_comparison(model_data, args.categories)
        if not args.no_save:
            json_path, md_path = save_comparison(model_data, args.categories, args.output_dir)
            print(f"  Comparison reports saved:")
            print(f"    JSON     : {json_path}")
            print(f"    Markdown : {md_path}")
            print()
        return
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
