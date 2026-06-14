"""
Quantize Zomi model for laptop inference.
Converts to GGUF 4-bit format — runs on your RTX 4050.

Usage:
  python3 scripts/quantize.py                              # Convert Phase 1 model
  python3 scripts/quantize.py --adapter adapters/translation  # Convert adapter
  
Output: models/zomi-q4.gguf (~2 GB)
"""

import os, sys, subprocess, glob
from pathlib import Path

BASE = Path(__file__).parent.parent

def find_phase1_model():
    """Find the best Phase 1 checkpoint."""
    ckpts = sorted(
        (BASE / "zomi-qlora-v1").glob("checkpoint-*"),
        key=lambda x: int(x.name.split("-")[-1])
    )
    return ckpts[-1] if ckpts else (BASE / "zomi-qlora-v1")

def find_phase2_model():
    """Check for Phase 2 instruction model."""
    ckpts = sorted(
        (BASE / "zomi-instruct-v1").glob("checkpoint-*"),
        key=lambda x: int(x.name.split("-")[-1])
    )
    return ckpts[-1] if ckpts else (BASE / "zomi-instruct-v1" if (BASE / "zomi-instruct-v1").exists() else None)

def check_install():
    """Ensure llama.cpp is available for quantization."""
    # Check if llama-quantize is available
    for cmd in ["llama-quantize", "llama.cpp-quantize", "quantize"]:
        try:
            r = subprocess.run(["which", cmd], capture_output=True, text=True, timeout=5)
            if r.stdout.strip():
                return r.stdout.strip()
        except:
            pass
    return None

def convert_to_gguf(model_path, output_path):
    """Convert HuggingFace model to GGUF format."""
    print(f"\nConverting {model_path} to GGUF...")

    # Step 1: Convert to GGUF (FP16 first)
    convert_script = "convert_hf_to_gguf.py"
    convert_path = None

    # Check common locations
    for p in [
        "/usr/local/bin/convert_hf_to_gguf.py",
        "/usr/lib/llama.cpp/convert_hf_to_gguf.py",
        str(Path.home() / "llama.cpp" / "convert_hf_to_gguf.py"),
    ]:
        if os.path.exists(p):
            convert_path = p
            break

    if not convert_path:
        # Download llama.cpp
        print("Downloading llama.cpp for conversion...")
        subprocess.run(
            ["git", "clone", "--depth=1", "https://github.com/ggerganov/llama.cpp",
             str(BASE / "llama.cpp")],
            capture_output=True, text=True, timeout=60
        )
        convert_path = str(BASE / "llama.cpp" / "convert_hf_to_gguf.py")

    if not os.path.exists(convert_path):
        print("Could not find conversion script. Install llama.cpp manually.")
        return False

    # Convert to FP16 GGUF
    fp16_path = output_path.replace("q4", "f16")
    result = subprocess.run(
        [sys.executable, convert_path, str(model_path), "--outfile", fp16_path],
        capture_output=True, text=True, timeout=600
    )
    if result.returncode != 0:
        print(f"Conversion failed: {result.stderr[:200]}")
        return False
    print(f"  ✓ FP16 GGUF created: {fp16_path}")

    # Step 2: Quantize to 4-bit
    quantize_cmd = check_install()
    if not quantize_cmd:
        # Build llama.cpp quantize
        print("Building llama-quantize...")
        build_dir = str(BASE / "llama.cpp" / "build")
        os.makedirs(build_dir, exist_ok=True)
        subprocess.run(
            ["cmake", "..", "-DLLAMA_CUDA=ON"],
            cwd=build_dir, capture_output=True, text=True, timeout=120
        )
        subprocess.run(
            ["cmake", "--build", ".", "--target", "quantize", "--config", "Release"],
            cwd=build_dir, capture_output=True, text=True, timeout=300
        )
        quantize_cmd = os.path.join(build_dir, "bin", "quantize")

    if not os.path.exists(quantize_cmd):
        print("Could not build quantize tool.")
        print(f"Manual command: llama-quantize {fp16_path} {output_path} Q4_K_M")
        return False

    # Run quantization
    result = subprocess.run(
        [quantize_cmd, fp16_path, output_path, "Q4_K_M"],
        capture_output=True, text=True, timeout=600
    )
    if result.returncode != 0:
        print(f"Quantization failed: {result.stderr[:200]}")
        return False

    print(f"  ✓ 4-bit GGUF created: {output_path}")
    size_gb = os.path.getsize(output_path) / (1024**3)
    print(f"  Size: {size_gb:.1f} GB")

    # Cleanup FP16
    os.remove(fp16_path)
    return True


def main():
    BASE.mkdir(exist_ok=True)

    # Find model to quantize
    model_path = find_phase2_model() or find_phase1_model()
    if not model_path:
        print("No trained model found. Train Phase 1 or Phase 2 first.")
        return

    output_path = BASE / "models" / "zomi-q4_K_M.gguf"
    output_path.parent.mkdir(exist_ok=True)

    print(f"Model: {model_path}")
    print(f"Output: {output_path}")
    print(f"Format: Q4_K_M (~2 GB, runs on RTX 4050)")

    success = convert_to_gguf(str(model_path), str(output_path))
    if success:
        print(f"\n✓ Quantization complete!")
        print(f"  Use with: python3 scripts/chat_local.py")
    else:
        print(f"\n⚠ Manual quantization needed.")
        print(f"  Install llama.cpp and run:")
        print(f"  python3 llama.cpp/convert_hf_to_gguf.py {model_path}")
        print(f"  ./quantize output.f16.gguf output.q4.gguf Q4_K_M")


if __name__ == "__main__":
    main()
