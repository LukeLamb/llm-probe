"""
backends.py — Ollama and HuggingFace backends with auto-detection.
Auto-detects Ollama first (already running), falls back to HuggingFace.
"""

import requests
import json
import time


def detect_backend(model_name: str) -> str:
    """Auto-detect available backend. Returns 'ollama' or 'hf'."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        if r.ok:
            tags = r.json().get("models", [])
            names = [m["name"] for m in tags]
            # Check if model is available in Ollama
            short = model_name.split(":")[0]
            for n in names:
                if short in n or model_name in n:
                    return "ollama"
            # Ollama is running but model not pulled
            print(f"  [!] Ollama is running but '{model_name}' not found.")
            print(f"      Available: {', '.join(names) or 'none'}")
            print(f"      Run: ollama pull {model_name}")
            raise SystemExit(1)
    except requests.exceptions.ConnectionError:
        pass
    return "hf"


class OllamaBackend:
    def __init__(self, model_name: str):
        self.model = model_name
        self.base_url = "http://localhost:11434"

    def generate(self, prompt: str, max_tokens: int = 80, temperature: float = 0.1) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "stop": ["\n\n", "###", "---"],
            },
        }
        try:
            r = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60,
            )
            r.raise_for_status()
            return r.json().get("response", "").strip()
        except Exception as e:
            return f"[ERROR: {e}]"

    def name(self) -> str:
        return f"ollama:{self.model}"


class HFBackend:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._tokenizer = None

    def _load(self):
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        print(f"  Loading {self.model_name} via HuggingFace (this may take a minute)...")
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.bfloat16,
            device_map="auto",
        )
        print("  Model loaded.\n")

    def generate(self, prompt: str, max_tokens: int = 80, temperature: float = 0.1) -> str:
        self._load()
        import torch

        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        with torch.no_grad():
            output = self._model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=max(temperature, 0.01),
                do_sample=temperature > 0.05,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        # Return only the newly generated tokens
        new_tokens = output[0][inputs["input_ids"].shape[1]:]
        return self._tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    def name(self) -> str:
        return f"hf:{self.model_name}"


def get_backend(model_name: str, force: str = None):
    """Return the appropriate backend instance."""
    backend_type = force or detect_backend(model_name)
    if backend_type == "ollama":
        print(f"  Backend: Ollama  (model: {model_name})")
        return OllamaBackend(model_name)
    else:
        print(f"  Backend: HuggingFace  (model: {model_name})")
        return HFBackend(model_name)
