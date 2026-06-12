"""
Zomi Continued Pre-Training — RunPod / Cloud GPU Script.

Usage:
    python cloud_train.py

What it does:
    - Loads Qwen 2.5 7B with 4-bit QLoRA (high rank r=128)
    - Trains on your Zomi raw corpus (next-token prediction)
    - Saves adapter + merged model to Hugging Face Hub
"""

import os
import math
import glob
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig,
    DataCollatorForLanguageModeling,
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

def load_texts(data_dir, filenames):
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
    return texts

print("Loading Zomi corpus...")
all_lines = load_texts(DATA_DIR, TEXT_FILES)
print(f"Total lines: {len(all_lines):,}")

split_idx = int(len(all_lines) * TRAIN_SPLIT)
train_lines = all_lines[:split_idx]
eval_lines = all_lines[split_idx:]
print(f"Train: {len(train_lines):,} | Eval: {len(eval_lines):,}")

train_dataset = Dataset.from_dict({"text": train_lines})
eval_dataset = Dataset.from_dict({"text": eval_lines})

# ─── 2. TOKENIZE ─────────────────────────────────────────────────────────────

print(f"\nLoading tokenizer: {BASE_MODEL}")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

def tokenize_function(examples):
    outputs = tokenizer(
        examples["text"],
        truncation=True,
        max_length=MAX_SEQ_LENGTH,
        padding="max_length",
    )
    outputs["labels"] = [ids[:] for ids in outputs["input_ids"]]
    return outputs

print("Tokenizing train dataset...")
train_dataset = train_dataset.map(
    tokenize_function,
    batched=True,
    remove_columns=["text"],
    num_proc=4,
)
print("Tokenizing eval dataset...")
eval_dataset = eval_dataset.map(
    tokenize_function,
    batched=True,
    remove_columns=["text"],
    num_proc=4,
)

# ─── 3. LOAD MODEL (4-bit QLoRA) ─────────────────────────────────────────────

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
    torch_dtype=torch.bfloat16,
)
model = prepare_model_for_kbit_training(model)

# ─── 4. CONFIGURE LORA ───────────────────────────────────────────────────────

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

# ─── 5. TRAINING ─────────────────────────────────────────────────────────────

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
    fp16=False,
    logging_steps=10,
    eval_strategy="steps",
    eval_steps=200,
    save_strategy="steps",
    save_steps=200,
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
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
    data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
)

print(f"\nStarting training...")
print(f"  Total train samples: {len(train_dataset):,}")
print(f"  Total eval samples:  {len(eval_dataset):,}")
print(f"  Warmup steps: {warmup_steps}")

trainer.train()

# ─── 6. SAVE & UPLOAD ────────────────────────────────────────────────────────

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
print(f"  Perplexity: {math.exp(trainer.state.best_metric):.2f}")
