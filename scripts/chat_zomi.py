"""
Zomi Adapter Router — auto-switches between adapters based on intent.

Detects what the user wants and loads the right skill:
  - "Translate hello to Zomi" → translation adapter
  - "Pasian in vantung le" → Zomi language adapter
  - "What does kei mean?" → tutor adapter

Usage:
  python3 scripts/chat_zomi.py "Translate hello to Zomi"
  python3 scripts/chat_zomi.py "Pasian in vantung le"
"""

import sys, re, json, importlib
from pathlib import Path

BASE = Path(__file__).parent.parent

# Intent classifiers — simple keyword matching
INTENTS = {
    "translation": {
        "keywords": ["translate", "translation", "translate to", "in english", "in zomi",
                     "what is the zomi word", "how do you say", "meaning of",
                     "zomi for", "english for"],
        "adapter": "translation",
        "description": "English ↔ Zomi translation",
    },
    "tutor": {
        "keywords": ["what does", "mean", "explain", "difference between", "how to use",
                     "grammar", "rule", "when to use", "why is"],
        "adapter": "tutor",
        "description": "Zomi language tutoring",
    },
    "zomi_chat": {
        "keywords": [],  # Default — any Zomi text
        "adapter": "current",  # Phase 1 checkpoint
        "description": "Natural Zomi conversation",
    },
}

# Zomi language markers
ZOMI_MARKERS = {"hi", "pen", "in", "tawh", "leh", "mah", "zong", "kei", "Pasian", "Topa",
                "ciang", "bang", "mahmah", "hiam", "hong", "khempeuh", "zaw", "tampi",
                "mite", "ciangin", "bangin", "tua", "ahi", "om", "nawn", "lo"}

def detect_intent(text):
    """Detect what the user wants based on their input."""
    lower = text.lower()

    # Check if input contains Zomi markers
    words = set(lower.split())
    is_zomi = len(words & ZOMI_MARKERS) >= 2

    if is_zomi:
        # Input is Zomi — route to Zomi chat
        return "zomi_chat", "Zomi text detected — using Zomi language adapter"

    # Check translation patterns
    for intent, config in INTENTS.items():
        for keyword in config["keywords"]:
            if keyword in lower:
                return intent, f"Detected: {config['description']}"

    # Check for English translation requests
    if "translate" in lower or "translation" in lower or "meaning" in lower:
        return "translation", "Translation request detected"

    # Default to translation (most common use case)
    return "translation", "Defaulting to translation mode"


def get_adapter_path(intent):
    """Get the adapter path for the detected intent."""
    reg_path = BASE / "adapters" / "registry.json"

    if intent == "zomi_chat":
        # Use Phase 1 checkpoint
        ckpts = sorted(
            (BASE / "zomi-qlora-v1").glob("checkpoint-*"),
            key=lambda x: int(x.name.split("-")[-1])
        )
        return ckpts[-1] if ckpts else str(BASE / "zomi-qlora-v1")

    if reg_path.exists():
        reg = json.loads(reg_path.read_text())
        if intent in reg.get("adapters", {}):
            return reg["adapters"][intent]["path"]

    return None


def chat(text):
    """Process user input with automatic adapter routing."""
    if not text.strip():
        return "Please enter some text."

    # Detect intent
    intent, reason = detect_intent(text)
    print(f"[Router] {reason}", file=sys.stderr)

    # Get adapter path
    adapter = get_adapter_path(intent)
    if adapter:
        print(f"[Router] Using: {adapter}", file=sys.stderr)
    else:
        print(f"[Router] Adapter '{intent}' not trained yet. Use base model.", file=sys.stderr)

    # Import and run inference
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        model_id = adapter if adapter else "Qwen/Qwen2.5-3B"
        tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
        )

        # Format prompt based on intent
        if intent == "translation":
            prompt = f"### Instruction:\nTranslate the following English text to Zomi.\n\n### Input:\n{text}\n\n### Response:\n"
        elif intent == "tutor":
            prompt = f"### Instruction:\nExplain this Zomi language question.\n\n### Input:\n{text}\n\n### Response:\n"
        else:
            prompt = text

        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=150,
            temperature=0.7,
            do_sample=True,
            top_p=0.9,
        )
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Clean response
        if "### Response:" in response:
            response = response.split("### Response:")[-1].strip()

        return response

    except Exception as e:
        return f"[Error] {e}"


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if not text:
        print(__doc__)
    else:
        print(chat(text))
