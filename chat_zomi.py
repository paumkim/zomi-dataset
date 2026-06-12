"""
Chat with the Zomi QLoRA model.

Usage:
    python chat_zomi.py                    # interactive chat
    python chat_zomi.py --prompt "..."     # single prompt
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "paumkim/zomi-qlora-v1"  # Hugging Face model ID


def generate(prompt, max_new=200, temperature=0.7):
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new,
        temperature=temperature,
        top_p=0.9,
        do_sample=True,
    )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)


if __name__ == "__main__":
    import sys

    if "--prompt" in sys.argv:
        idx = sys.argv.index("--prompt")
        prompt = sys.argv[idx + 1]
        print(generate(prompt))
    else:
        print("Zomi Chat — type 'quit' to exit\n")
        while True:
            prompt = input("> ")
            if prompt.lower() in ("quit", "exit", "q"):
                break
            print(generate(prompt))
            print()
