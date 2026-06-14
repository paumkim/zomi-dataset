"""
Chat with Zomi model locally on your laptop (RTX 4050).

Usage:
  python3 scripts/chat_local.py "Translate hello to Zomi"
  python3 scripts/chat_local.py --interactive
"""

import sys, subprocess, os, glob
from pathlib import Path

BASE = Path(__file__).parent.parent
MODELS_DIR = BASE / "models"

def find_gguf():
    models = sorted(glob.glob(str(MODELS_DIR / "*.gguf")))
    return models[-1] if models else None

def main():
    model = find_gguf()

    if not model:
        print("No quantized model found. Run scripts/quantize.py first.")
        return

    size_gb = os.path.getsize(model) / (1024**3)

    # Check for llama.cpp
    llama_paths = [
        "/usr/local/bin/llama-cli",
        "/usr/bin/llama-cli",
        str(BASE / "llama.cpp" / "build" / "bin" / "llama-cli"),
        str(Path.home() / "llama.cpp" / "build" / "bin" / "llama-cli"),
    ]

    llama = None
    for p in llama_paths:
        if os.path.exists(p):
            llama = p
            break

    if not llama:
        print("llama-cli not found. Install llama.cpp first.")
        print(f"Model ready at: {model} ({size_gb:.1f} GB)")
        return

    print(f"Zomi Model — loaded")
    print(f"{'='*40}")
    print(f"Model: {Path(model).name} ({size_gb:.1f} GB)")
    print(f"GPU:   RTX 4050 (6 GB)")
    print(f"{'='*40}\n")

    args = sys.argv[1:]
    if "--interactive" in args or "-i" in args:
        print("Interactive mode. Type /quit to exit.\n")
        while True:
            try:
                prompt = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not prompt or prompt == "/quit":
                break

            subprocess.run([
                llama,
                "-m", model,
                "-p", f"### Instruction:\nTranslate to Zomi if English, or to English if Zomi.\n\n### Input:\n{prompt}\n\n### Response:\n",
                "-n", "200",
                "-t", "8",
                "--temp", "0.7",
                "--top-p", "0.9",
                "--repeat-penalty", "1.1",
                "--no-display-prompt",
            ])
            print()
    else:
        prompt = " ".join(args)
        if not prompt:
            print(__doc__)
            return

        subprocess.run([
            llama,
            "-m", model,
            "-p", f"### Instruction:\nRespond appropriately.\n\n### Input:\n{prompt}\n\n### Response:\n",
            "-n", "200",
            "-t", "8",
            "--temp", "0.7",
            "--no-display-prompt",
        ])


if __name__ == "__main__":
    main()
