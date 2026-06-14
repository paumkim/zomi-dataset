"""
Multi-Adapter Manager — train, list, and swap LoRA adapters on Qwen base.

Usage:
  python3 scripts/adapter_manager.py list              # List all adapters
  python3 scripts/adapter_manager.py train translation  # Train a new adapter
  python3 scripts/adapter_manager.py load translation   # Load adapter for inference
  python3 scripts/adapter_manager.py info               # Show current status
"""

import os, json, glob, sys, subprocess
from pathlib import Path

BASE = Path(__file__).parent.parent
ADAPTERS_DIR = BASE / "adapters"
QEN_DIR = BASE / "zomi-qlora-v1"  # Phase 1 trained model
CONFIG_FILE = ADAPTERS_DIR / "registry.json"

# ─── REGISTRY ──────────────────────────────────────────────────────────────

def load_registry():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {"base_model": "Qwen/Qwen2.5-3B", "current": None, "adapters": {}}

def save_registry(reg):
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(reg, indent=2))

def list_adapters():
    reg = load_registry()
    print(f"Base model: {reg['base_model']}")
    print(f"Active: {reg['current'] or 'None (base model)'}\n")

    if not reg["adapters"]:
        print("No adapters trained yet.")
        print("  python3 adapter_manager.py train <name>")
        return

    print(f"{'Name':<20} {'Type':<20} {'Steps':<10} {'Loss':<10} {'Size':<10}")
    print("-" * 70)
    for name, info in reg["adapters"].items():
        active = " ← active" if name == reg["current"] else ""
        size = info.get("size_mb", "?")
        print(f"{name:<20} {info.get('type','?')[:18]:<20} {info.get('steps','?'):<10} {info.get('loss','?'):<10} {size:<10}{active}")

# ─── TRAINING ──────────────────────────────────────────────────────────────

def train_adapter(name, data_path=None):
    reg = load_registry()
    ADAPTERS_DIR.mkdir(exist_ok=True)
    out_dir = ADAPTERS_DIR / name
    out_dir.mkdir(exist_ok=True)

    print(f"Training adapter: {name}")

    # Use Phase 1 checkpoint as base
    ckpts = sorted(glob.glob(str(QEN_DIR / "checkpoint-*")), key=lambda x: int(x.split("-")[-1]))
    base_model = ckpts[-1] if ckpts else str(QEN_DIR)
    print(f"Base: {base_model}")

    # Default: train on translation data
    if not data_path:
        data_path = BASE / "data" / "zomi_instructions.jsonl"
        if not data_path.exists():
            print("No data specified and no default found.")
            return

    # Launch training
    cmd = [
        sys.executable, "-m", "torchrun", "--standalone", "--nproc_per_node=1",
        str(BASE / "scripts" / "train_instructions.py"),
        "--output", str(out_dir),
        "--base", base_model,
        "--data", str(data_path),
    ]
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)

    # Register
    size = sum(f.stat().st_size for f in out_dir.rglob("*")) // (1024*1024)
    reg["adapters"][name] = {
        "type": "instruction",
        "path": str(out_dir),
        "steps": "?",
        "loss": "?",
        "size_mb": f"{size} MB",
    }
    save_registry(reg)
    print(f"Registered adapter: {name}")

# ─── LOADING ──────────────────────────────────────────────────────────────

def load_adapter(name):
    reg = load_registry()
    if name not in reg["adapters"]:
        print(f"Adapter '{name}' not found.")
        print("Available:", ", ".join(reg["adapters"].keys()) or "none")
        return

    info = reg["adapters"][name]
    reg["current"] = name
    save_registry(reg)
    print(f"✓ Active adapter: {name}")
    print(f"  Path: {info['path']}")
    print(f"  Size: {info.get('size_mb', '?')}")
    print(f"\nRun inference with: python3 scripts/chat_zomi.py --adapter {name}")


def show_info():
    reg = load_registry()
    print(f"Adapter Manager")
    print(f"{'='*40}")
    print(f"Base model: {reg['base_model']}")
    print(f"Active adapter: {reg['current'] or 'None (base model)'}")
    print(f"Total adapters: {len(reg['adapters'])}")
    print(f"Adapters dir: {ADAPTERS_DIR}")
    for name, info in reg["adapters"].items():
        active = " ◀ ACTIVE" if name == reg["current"] else ""
        print(f"  - {name} ({info.get('type','?')}){active}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        list_adapters()
    elif cmd == "train":
        name = sys.argv[2] if len(sys.argv) > 2 else input("Adapter name: ")
        train_adapter(name)
    elif cmd == "load":
        if len(sys.argv) > 2:
            load_adapter(sys.argv[2])
        else:
            print("Usage: adapter_manager.py load <name>")
    elif cmd == "info":
        show_info()
    else:
        print(f"Unknown: {cmd}")
        print(__doc__)
