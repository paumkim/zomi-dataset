"""
Zomi Continued Pre-Training — RunPod / Cloud GPU Script.

Usage:
    python cloud_train.py
"""

import os
import math
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
import torch
import huggingface_hub

# ─── CONFIG ──────────────────────────────────────────────────────────────────

BASE_MODEL = "Qwen/Qwen2.5-7B"
HF_USERNAME = "paumkim"
RUN_NAME = "zomi-qlora-v1"

DATA_DIR = "/workspace/data"
TEXT_FILES = [
    "zomi_clean_p1.txt",
    "zomi_clean_p2.txt",
    "zomi_clean_p3.txt",
    "zomi_clean_p4.txt",
]

TRAIN_SPLIT = 0.95
MAX_SEQ_LENGTH = 2048
BATCH_SIZE = 4
GRADIENT_ACCUMULATION_STEPS = 8
LEARNING_RATE = 3e-4
NUM_EPOCHS = 5

LORA_R = 128
LORA_ALPHA = 256
LORA_DROPOUT = 0.05
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

# ─── 1. LOAD DATA ────────────────────────────────────────────────────────────

def load_and_pack(data_dir, filenames, max_chars=4000):
    """Load text and pack short lines into chunks of ~max_chars characters.
    Using character count is ~100x faster than tokenizing each line individually."""
    texts = []
    for fn in filenames:
        path = os.path.join(data_dir, fn)
        if not os.path.exists(path):
            print(f"  WARNING: {path} not found, skipping")
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        texts.extend(lines)
        print(f"  Loaded {fn}: {len(lines)} lines")
    print(f"Total lines: {len(texts):,}")

    # Pack by character count (roughly ~2048 tokens ≈ ~4000 chars for Zomi)
    chunks = []
    buf = []
    buf_len = 0
    for line in texts:
        line_len = len(line) + 1  # +1 for space/newline
        if buf_len + line_len > max_chars:
            if buf:
                chunks.append(" ".join(buf))
            buf = [line]
            buf_len = line_len
        else:
            buf.append(line)
            buf_len += line_len
    if buf:
        chunks.append(" ".join(buf))

    print(f"Packed into {len(chunks):,} chunks (~{max_chars} chars each)")
    return chunks


print("Loading Zomi corpus...")
packed_lines = load_and_pack(DATA_DIR, TEXT_FILES, max_chars=4000)

split_idx = int(len(packed_lines) * TRAIN_SPLIT)
train_lines = packed_lines[:split_idx]
eval_lines = packed_lines[split_idx:]
print(f"Train: {len(train_lines):,} chunks | Eval: {len(eval_lines):,} chunks")

train_dataset = Dataset.from_dict({"text": train_lines})
eval_dataset = Dataset.from_dict({"text": eval_lines})
del packed_lines, train_lines, eval_lines

# ─── 4. LOAD TOKENIZER ───────────────────────────────────────────────────────

print(f"\nLoading tokenizer: {BASE_MODEL}")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

# ─── 5. COLLATOR — Tokenizes on-the-fly per batch ────────────────────────────

class ZomiDataCollator:
    def __init__(self, tokenizer, max_length):
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __call__(self, features):
        texts = [f["text"] for f in features]
        batch = self.tokenizer(
            texts,
            truncation=True,
            padding="longest",
            max_length=self.max_length,
            return_tensors="pt",
        )
        batch["labels"] = batch["input_ids"].clone()
        return batch

# ─── 6. LOAD MODEL (4-bit QLoRA) ─────────────────────────────────────────────

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

print(f"\nLoading model: {BASE_MODEL}")
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
    dtype=torch.bfloat16,
)
model = prepare_model_for_kbit_training(model)

# ─── 7. CONFIGURE LORA ───────────────────────────────────────────────────────

lora_config = LoraConfig(
    r=LORA_R,
    lora_alpha=LORA_ALPHA,
    target_modules=TARGET_MODULES,
    lora_dropout=LORA_DROPOUT,
    bias="none",
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

total_steps = (len(train_dataset) // (BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS)) * NUM_EPOCHS
warmup_steps = int(total_steps * 0.05)

# ─── 8. TRAINING ─────────────────────────────────────────────────────────────

training_args = TrainingArguments(
    output_dir=f"./{RUN_NAME}",
    num_train_epochs=NUM_EPOCHS,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
    gradient_checkpointing=True,
    learning_rate=LEARNING_RATE,
    weight_decay=0.01,
    warmup_steps=warmup_steps,
    lr_scheduler_type="cosine",
    bf16=True,
    logging_steps=10,
    eval_strategy="steps",
    eval_steps=200,
    save_strategy="steps",
    save_steps=200,
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    remove_unused_columns=False,
    report_to="none",
    push_to_hub=False,
    hub_model_id=f"{HF_USERNAME}/{RUN_NAME}",
    dataloader_num_workers=2,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    data_collator=ZomiDataCollator(tokenizer, MAX_SEQ_LENGTH),
)

print(f"\nStarting training...")
print(f"  Total train samples: {len(train_dataset):,}")
print(f"  Total eval samples:  {len(eval_dataset):,}")
print(f"  Warmup steps: {warmup_steps}")

trainer.train()

# ─── 10. SAVE & UPLOAD ────────────────────────────────────────────────────────

print("\nSaving LoRA adapter...")
adapter_path = f"./{RUN_NAME}-adapter"
model.save_pretrained(adapter_path)
tokenizer.save_pretrained(adapter_path)

print("\nMerging adapter into base model...")
from peft import PeftModel

model.eval()
del model
torch.cuda.empty_cache()

base = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
merged = PeftModel.from_pretrained(base, adapter_path).merge_and_unload()
merged_path = f"./{RUN_NAME}-merged"
merged.save_pretrained(merged_path)
tokenizer.save_pretrained(merged_path)

print(f"\nUploading to Hugging Face Hub: {HF_USERNAME}/{RUN_NAME}")
huggingface_hub.HfApi().create_repo(
    repo_id=f"{HF_USERNAME}/{RUN_NAME}",
    repo_type="model",
    exist_ok=True,
)
merged.push_to_hub(f"{HF_USERNAME}/{RUN_NAME}")
tokenizer.push_to_hub(f"{HF_USERNAME}/{RUN_NAME}")

print(f"\n✓ Done! Model uploaded to: https://huggingface.co/{HF_USERNAME}/{RUN_NAME}")
print(f"  Final eval loss: {trainer.state.best_metric:.4f}")
print(f"  Perplexity: {math.exp(trainer.state.best_metric):.4f}")
