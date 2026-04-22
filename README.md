# llm-probe

> **Know your model before you train it.**

A lightweight tool for evaluating base LLMs across six categories before fine-tuning. Runs against Ollama or HuggingFace, outputs a scored terminal report plus saved JSON and Markdown files.

---

## What it does

Before you start fine-tuning, llm-probe tells you:

- What the base model already does well (don't waste training data here)
- Where it consistently fails (target these with SFT examples)
- How it responds to different prompt formats (critical for SFT data design)
- Whether its outputs are stable across repeated runs

It runs 40+ completion-style probes across six categories and scores each one, giving you a map of the model's baseline before a single training step.

---

## Probe Categories

| Category | What it measures |
|----------|-----------------|
| **Completion Consistency** | Does the model give stable answers across repeated runs? |
| **Knowledge & Factual Recall** | Does it complete factual statements correctly? |
| **Format Compliance** | Can it continue JSON, lists, markdown, code patterns? |
| **Instruction Following Patterns** | How well does it respond to Q&A, Alpaca, chat formats? |
| **Geometry & Spatial Reasoning** | Angles, shapes, rotation, spatial logic |
| **Reasoning & Logic** | Syllogisms, sequences, multi-step arithmetic, analogies |

> **Note on base models:** All probes are written as completions, not instructions. Base models complete text — they do not follow instructions. Every prompt is the beginning of a sentence or pattern the model should continue. This also reveals which prompt formats are already baked into the base model, directly informing your SFT data design.

---

## Requirements

- Python 3.10+
- **Ollama** (recommended) — already running with your model pulled, OR
- **HuggingFace** — transformers + PyTorch with ROCm or CUDA

```bash
pip install requests
# For HuggingFace backend only:
pip install transformers accelerate
# PyTorch ROCm (AMD):
pip install torch --index-url https://download.pytorch.org/whl/rocm7.2
```

---

## Quick Start

```bash
git clone https://github.com/LukeLamb/llm-probe.git
cd llm-probe

# Run against Ollama (auto-detected if running)
python probe.py --model llama3.1:8b

# Run against HuggingFace directly
python probe.py --model meta-llama/Meta-Llama-3.1-8B --backend hf

# Run specific categories only
python probe.py --model llama3.1:8b --categories geometry reasoning

# Show individual probe completions
python probe.py --model llama3.1:8b --verbose
```

---

## Output

**Terminal:**
```
  ── Summary ──────────────────────────────────────────
  Completion Consistency        ████████████████░░░░  82%
  Knowledge & Factual Recall    ██████████████░░░░░░  71%
  Format Compliance             ████████████░░░░░░░░  62%
  Instruction Following         ██████████░░░░░░░░░░  50%
  Geometry & Spatial            ████████░░░░░░░░░░░░  43%
  Reasoning & Logic             ██████████████████░░  88%

  Overall score : 66%  Grade: C

  ── Pre-Training Recommendations ─────────────────────
  ● GEOMETRY (43%) — High priority. Add spatial reasoning examples...
  ● INSTRUCTION FOLLOWING (50%) — Prioritise Q&A and Alpaca-format pairs...
  ● FORMAT COMPLIANCE (62%) — Include structured output examples...
```

**Saved files** (in `./reports/` by default):
- `probe_llama3.1_8b_20260414_1030.json` — full results with all completions
- `probe_llama3.1_8b_20260414_1030.md` — human-readable markdown summary

---

## Options

```
--model         Model name (required)
--backend       Force 'ollama' or 'hf' (default: auto-detect)
--categories    Run specific categories only
--verbose       Show individual probe completions in terminal
--output-dir    Report output directory (default: ./reports)
--no-save       Skip saving report files
```

---

## Adding Custom Probes

Edit `llm_probe/probes.py`. Each probe is a simple dict:

```python
{
    "id":          "my_001",
    "description": "What this tests",
    "prompt":      "The completion prompt goes",   # no full stop — model completes it
    "expected":    ["here", "expected keyword"],   # ANY of these = pass
}
```

Add it to the relevant category list and it's automatically included.

---

## Credits

Built by [Remy & Remi](https://github.com/LukeLamb) — independent AI/ML research and tooling.

---

## License

MIT — use freely, attribution appreciated.
