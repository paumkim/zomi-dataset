"""
Personal AI Agent — runs on your laptop, no GPU needed.
Uses Hugging Face Inference API (free) so it's always ready.
"""

import os, json, datetime, readline, sys

MEMORY_FILE = os.path.expanduser("~/.paumkim_agent_memory.json")

AGENT_PROMPT = """You are Paumkim's personal AI assistant.
You help with coding, writing, research, and anything else.
You are helpful, direct, and remember context.
Always respond in clear language. When unsure, say so."""

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE) as f:
            return json.load(f)
    return {"conversations": [], "facts": []}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def chat(prompt, memory):
    import requests

    # Build context from recent history
    context = AGENT_PROMPT + "\n\n"
    for msg in memory["conversations"][-6:]:
        context += f"{msg['role']}: {msg['content']}\n"
    context += f"User: {prompt}\nAssistant:"

    HF_TOKEN = os.environ.get("HF_TOKEN")
    if not HF_TOKEN:
        return "Set your HF token: export HF_TOKEN=hf_your_token_here"

    try:
        r = requests.post(
            "https://api-inference.huggingface.co/models/microsoft/Phi-3-mini-4k-instruct",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": context, "parameters": {"max_new_tokens": 500, "temperature": 0.7}},
            timeout=60,
        )
        if r.status_code == 200:
            return r.json()[0]["generated_text"].split("Assistant:")[-1].strip()
        return f"[API error: {r.status_code}]"
    except Exception as e:
        return f"[Error: {e}]"

def main():
    print("\n" + "=" * 50)
    print("  Paumkim's Personal Agent")
    print("  Type 'quit' to exit, 'save' to save, 'forget' to clear")
    print("=" * 50 + "\n")

    memory = load_memory()
    if not memory.get("facts"):
        memory["facts"] = ["Paumkim created the Zomi dataset"]
        save_memory(memory)

    while True:
        try:
            prompt = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not prompt:
            continue
        if prompt.lower() in ("quit", "exit", "q"):
            save_memory(memory)
            print("Saved. See you later!")
            break
        if prompt.lower() == "save":
            save_memory(memory)
            print("Saved.")
            continue
        if prompt.lower() == "forget":
            memory["conversations"] = []
            save_memory(memory)
            print("Memory cleared.")
            continue

        print("\nAgent thinking...")
        response = chat(prompt, memory)

        memory["conversations"].append({"role": "user", "content": prompt, "time": datetime.datetime.now().isoformat()})
        memory["conversations"].append({"role": "assistant", "content": response, "time": datetime.datetime.now().isoformat()})

        print(f"\n{response}")

    save_memory(memory)

if __name__ == "__main__":
    main()
