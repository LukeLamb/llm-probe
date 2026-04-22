"""
reporter.py — Terminal (coloured) report and file output (JSON + Markdown).
"""

import json
import os
from datetime import datetime
from typing import Dict, List

# Terminal colours
RED    = "\033[0;31m"
GREEN  = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE   = "\033[0;34m"
CYAN   = "\033[0;36m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
NC     = "\033[0m"

GRADE_COLOUR = {
    "A": GREEN,
    "B": GREEN,
    "C": YELLOW,
    "D": YELLOW,
    "F": RED,
}

BAR_FULL  = "█"
BAR_HALF  = "▌"
BAR_EMPTY = "░"


def _bar(score: int, width: int = 20) -> str:
    filled = round((score / 100) * width)
    empty  = width - filled
    colour = GREEN if score >= 75 else YELLOW if score >= 50 else RED
    return f"{colour}{'█' * filled}{'░' * empty}{NC} {score:3d}%"


def _score_colour(score: int) -> str:
    if score >= 75: return GREEN
    if score >= 50: return YELLOW
    return RED


def _probe_lang_from_id(probe_id: str) -> str:
    """Infer probe language from ID suffix. Mirrors scorer._probe_lang logic.

    Returns one of 'en', 'fr', 'de', 'nl', or 'unknown' if no language suffix.
    """
    for lang in ("en", "fr", "de", "nl"):
        if probe_id.endswith(f"_{lang}"):
            return lang
    return "unknown"


def compute_eu_political_breakdown(results: list) -> dict:
    """Compute per-language sub-scores, Gate 9 parity check, and Belgian-context
    separation for the eu_political probe category.

    Gate 9: no pan-EU language may score more than 20% below the cross-language
    mean. Belgian-context probes (eup_bel_*) are excluded from parity math and
    reported separately per the eval spec.
    """
    by_lang = {"en": [], "fr": [], "de": [], "nl": []}
    belgian = []

    for r in results:
        pid = r["probe_id"]
        if pid.startswith("eup_bel_"):
            belgian.append(r)
        else:
            lang = _probe_lang_from_id(pid)
            if lang in by_lang:
                by_lang[lang].append(r)

    def _score(rs):
        if not rs:
            return {"total": 0, "passed": 0, "score": 0}
        earned = sum(r["score"] for r in rs)
        maxp   = len(rs) * 2
        return {
            "total":  len(rs),
            "passed": sum(1 for r in rs if r["passed"]),
            "score":  round(earned / maxp * 100) if maxp > 0 else 0,
        }

    per_lang      = {lang: _score(rs) for lang, rs in by_lang.items()}
    belgian_score = _score(belgian)

    # Gate 9 parity check (pan-EU languages only, exclude Belgian-context).
    lang_scores = [per_lang[l]["score"] for l in ("en", "fr", "de", "nl")
                   if per_lang[l]["total"] > 0]
    if lang_scores:
        mean           = sum(lang_scores) / len(lang_scores)
        parity_pass    = all(s >= mean - 20 for s in lang_scores)
        parity_deltas  = {l: per_lang[l]["score"] - mean
                          for l in ("en", "fr", "de", "nl")
                          if per_lang[l]["total"] > 0}
    else:
        mean, parity_pass, parity_deltas = 0, True, {}

    return {
        "per_language":   per_lang,
        "belgian_context": belgian_score,
        "parity_mean":    round(mean, 1),
        "parity_pass":    parity_pass,
        "parity_deltas":  {l: round(d, 1) for l, d in parity_deltas.items()},
    }


def print_header(model_name: str, backend: str):
    print()
    print(f"{BOLD}{CYAN}╔══════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}{CYAN}║              llm-probe — Base Model Report           ║{NC}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════╝{NC}")
    print(f"  {DIM}Model  : {NC}{model_name}")
    print(f"  {DIM}Backend: {NC}{backend}")
    print(f"  {DIM}Time   : {NC}{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()


def print_category(label: str, cat_score: dict, results: List[dict], verbose: bool = False, category_key: str = None):
    sc    = cat_score["score"]
    total = cat_score["total"]
    passed = cat_score["passed"]
    colour = _score_colour(sc)

    print(f"  {BOLD}{label}{NC}")
    print(f"  {_bar(sc)}  {passed}/{total} passed")

    if verbose:
        for r in results:
            icon  = f"{GREEN}✓{NC}" if r["passed"] else f"{RED}✗{NC}"
            comp = r.get("completion") or " | ".join(r.get("completions", []))
            short = comp[:60].replace("\n", " ")
            if len(comp) > 60:
                short += "…"
            print(f"    {icon} {DIM}{r['description']}{NC}")
            print(f"      {DIM}→ {short}{NC}")

    # EU Political breakdown: per-language, parity check, Belgian-context.
    if category_key == "eu_political":
        bd = compute_eu_political_breakdown(results)
        print(f"    {DIM}── Per-language breakdown ──{NC}")
        for lang in ("en", "fr", "de", "nl"):
            sub = bd["per_language"][lang]
            if sub["total"] > 0:
                lang_col = _score_colour(sub["score"])
                delta    = bd["parity_deltas"].get(lang, 0)
                delta_s  = f"  (Δ {delta:+.1f} from mean {bd['parity_mean']})" if bd["parity_deltas"] else ""
                print(f"    {lang.upper()}: {lang_col}{sub['score']:3d}%{NC} ({sub['passed']}/{sub['total']}){DIM}{delta_s}{NC}")
        # Parity verdict
        if bd["parity_deltas"]:
            verdict_col = GREEN if bd["parity_pass"] else RED
            verdict     = "PASS" if bd["parity_pass"] else "FAIL"
            print(f"    {DIM}Gate 9 parity (no lang > 20% below mean): {verdict_col}{verdict}{NC}")
        # Belgian-context reported separately
        bel = bd["belgian_context"]
        if bel["total"] > 0:
            bel_col = _score_colour(bel["score"])
            print(f"    {DIM}Belgian-context (separate):{NC} {bel_col}{bel['score']:3d}%{NC} ({bel['passed']}/{bel['total']})")
    print()


def print_summary(overall: int, grade: str, category_scores: dict):
    gc = GRADE_COLOUR.get(grade, NC)
    print(f"{BOLD}{CYAN}  ── Summary ─────────────────────────────────────────{NC}")
    print()
    for key, cs in category_scores.items():
        label = key.capitalize().replace("_", " ")
        print(f"  {label:<35} {_bar(cs['score'], 16)}")
    print()
    print(f"  Overall score : {_score_colour(overall)}{BOLD}{overall}%{NC}  Grade: {gc}{BOLD}{grade}{NC}")
    print()
    if overall >= 75:
        print(f"  {GREEN}{BOLD}✓ Strong baseline — model is well-suited for targeted SFT.{NC}")
    elif overall >= 50:
        print(f"  {YELLOW}{BOLD}⚠ Moderate baseline — focus SFT data on weak categories.{NC}")
    else:
        print(f"  {RED}{BOLD}✗ Weak baseline — extensive SFT required across most areas.{NC}")
    print()


def print_training_recommendations(category_scores: dict):
    """Print actionable pre-training recommendations based on scores."""
    print(f"{BOLD}{CYAN}  ── Pre-Training Recommendations ────────────────────{NC}\n")

    recs = []
    for key, cs in category_scores.items():
        sc = cs["score"]
        if key == "geometry" and sc < 75:
            recs.append(f"  {RED}●{NC} GEOMETRY ({sc}%) — High priority. "
                        "Add spatial reasoning examples: angle sums, shape properties, "
                        "rotation descriptions, coordinate problems.")
        elif key == "reasoning" and sc < 75:
            recs.append(f"  {RED}●{NC} REASONING ({sc}%) — Add chain-of-thought examples: "
                        "syllogisms, numeric patterns, multi-step word problems.")
        elif key == "instruction" and sc < 75:
            recs.append(f"  {YELLOW}●{NC} INSTRUCTION FOLLOWING ({sc}%) — "
                        "Prioritise Q&A and Alpaca-format pairs in SFT data. "
                        "Model does not reliably pick up instruction patterns yet.")
        elif key == "format" and sc < 75:
            recs.append(f"  {YELLOW}●{NC} FORMAT COMPLIANCE ({sc}%) — "
                        "Include structured output examples: JSON, numbered lists, "
                        "markdown, key-value pairs.")
        elif key == "knowledge" and sc < 75:
            recs.append(f"  {YELLOW}●{NC} KNOWLEDGE ({sc}%) — "
                        "Consider factual recall pairs in SFT. "
                        "Knowledge gaps at this stage may need continued pre-training.")
        elif key == "consistency" and sc < 75:
            recs.append(f"  {RED}●{NC} CONSISTENCY ({sc}%) — "
                        "Model gives unstable outputs. Lower training temperature, "
                        "check dataset diversity before SFT.")

    if recs:
        for r in recs:
            print(r)
    else:
        print(f"  {GREEN}●{NC} All categories strong — model is ready for targeted SFT.")
        print(f"      Focus training data on your specific task domain.")
    print()


def save_json(report: dict, output_dir: str, model_slug: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M")
    path = os.path.join(output_dir, f"probe_{model_slug}_{ts}.json")
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    return path


def save_markdown(report: dict, output_dir: str, model_slug: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M")
    path = os.path.join(output_dir, f"probe_{model_slug}_{ts}.md")

    model   = report["model"]
    backend = report["backend"]
    overall = report["overall_score"]
    grade   = report["grade"]
    cats    = report["categories"]

    lines = [
        f"# llm-probe Report — {model}",
        f"",
        f"**Date:** {report['timestamp']}  ",
        f"**Backend:** {backend}  ",
        f"**Overall Score:** {overall}%  ({grade})",
        f"",
        f"---",
        f"",
        f"## Category Scores",
        f"",
        f"| Category | Score | Passed | Failed |",
        f"|----------|-------|--------|--------|",
    ]

    for key, cat in cats.items():
        cs  = cat["score_summary"]
        lbl = key.replace("_", " ").title()
        lines.append(f"| {lbl} | {cs['score']}% | {cs['passed']} | {cs['failed']} |")

    lines += ["", "---", "", "## Pre-Training Recommendations", ""]

    for key, cat in cats.items():
        sc  = cat["score_summary"]["score"]
        lbl = key.replace("_", " ").title()
        if sc < 75:
            lines.append(f"- **{lbl}** ({sc}%) — below threshold, prioritise in SFT data.")
        else:
            lines.append(f"- **{lbl}** ({sc}%) — strong baseline.")

    lines += ["", "---", "", "## Probe Results", ""]

    for key, cat in cats.items():
        lbl = key.replace("_", " ").title()
        lines += [f"### {lbl}", ""]

        # EU Political breakdown: per-language, parity, Belgian-context separate.
        if key == "eu_political":
            bd = compute_eu_political_breakdown(cat["results"])
            lines += ["**Per-language breakdown:**", ""]
            lines += ["| Language | Score | Passed | Δ from mean |",
                      "|----------|------:|-------:|-----------:|"]
            for lang in ("en", "fr", "de", "nl"):
                sub = bd["per_language"][lang]
                if sub["total"] > 0:
                    delta = bd["parity_deltas"].get(lang, 0)
                    lines.append(f"| {lang.upper()} | {sub['score']}% | {sub['passed']}/{sub['total']} | {delta:+.1f} |")
            lines += ["", f"**Gate 9 parity check** (no language > 20% below mean {bd['parity_mean']}): "
                          f"**{'PASS' if bd['parity_pass'] else 'FAIL'}**", ""]
            bel = bd["belgian_context"]
            if bel["total"] > 0:
                lines += [f"**Belgian-context (separate sub-score):** {bel['score']}% ({bel['passed']}/{bel['total']})", ""]
            lines += ["---", "", "**Individual probe results:**", ""]

        for r in cat["results"]:
            status = "✓" if r["passed"] else "✗"
            lines.append(f"**{status} {r['description']}**")
            lines.append(f"- Prompt: `{r['prompt'][:80]}`")
            comp = r.get("completion") or " | ".join(r.get("completions", []))
            lines.append(f"- Completion: `{comp[:100]}`")
            lines.append(f"- Score: {r['score']}/2")
            lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))
    return path
