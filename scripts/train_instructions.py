"""
Phase 2: Instruction Fine-Tuning
Takes the Zomi-speaking model (Phase 1 checkpoint) and teaches it to translate on command.
Uses the 500K instruction pairs from data/zomi_instructions.jsonl

Usage:
    python3 scripts/train_instructions.py
    
    # Or on the pod:
    ssh -p <port> root@<ip> "cd /workspace && python3 train_instructions.py"
"""

import os, json, sys, glob
from pathlib import Path

BASE = Path(__file__).parent.parent

# ─── CONFIG ──────────────────────────────────────────────────────────────────

# Use the best checkpoint from Phase 1
CHECKPOINT_DIR = BASE / "zomi-qlora-v1"
CKPTS = sorted(glob.glob(str(CHECKPOINT_DIR / "checkpoint-*")), 
               key=lambda x: int(x.split("-")[-1]))
BASE_MODEL = CKPTS[-1] if CKPTS else str(CHECKPOINT_DIR)
OUTPUT_DIR = BASE / "zomi-instruct-v1"
INSTRUCTION_DATA = BASE / "data" / "zomi_instructions.jsonl"

MAX_LENGTH = 1024
BATCH_SIZE = 4
GRADIENT_ACCUMULATION_STEPS = 8
LEARNING_RATE = 1e-4
NUM_EPOCHS = 2

def main():
    import torch
    from transformers import (
        AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer,
        BitsAndBytesConfig, DataCollatorForLanguageModeling
    )
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    print("=" * 60)
    print("Phase 2: Instruction Fine-Tuning")
    print("=" * 60)

    # ─── 1. Load checkpoint from Phase 1 ───
    print(f"\nLoading base model from: {BASE_MODEL}")
    
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    model = prepare_model_for_kbit_training(model)

    # New LoRA adapter for instruction-following
    lora_config = LoraConfig(
        r=64,  # Smaller rank — less learning needed for instruction format
        lora_alpha=128,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # ─── 2. Load instruction data ───
    print(f"\nLoading instruction data: {INSTRUCTION_DATA}")
    if not INSTRUCTION_DATA.exists():
        print(f"ERROR: {INSTRUCTION_DATA} not found.")
        print("Run scripts/prepare_instructions.py first.")
        return

    with open(INSTRUCTION_DATA, "r", encoding="utf-8") as f:
        raw_data = [json.loads(line) for line in f if line.strip()]

    # Format as chat-style prompts
    def format_instruction(example):
        return {
            "text": f"### Instruction:\n{example['instruction']}\n\n### Input:\n{example['input']}\n\n### Response:\n{example['output']}{tokenizer.eos_token}"
        }

    formatted = [format_instruction(ex) for ex in raw_data]
    split = int(len(formatted) * 0.95)
    train_data = formatted[:split]
    eval_data = formatted[split:]
    print(f"Train: {len(train_data):,} | Eval: {len(eval_data):,}")

    train_dataset = Dataset.from_list(train_data)
    eval_dataset = Dataset.from_list(eval_data)

    # ─── 3. Tokenize ───
    def tokenize(examples):
        outputs = tokenizer(
            examples["text"],
            truncation=True,
            max_length=MAX_LENGTH,
            padding="max_length",
        )
        outputs["labels"] = [ids[:] for ids in outputs["input_ids"]]
        return outputs

    print("Tokenizing...")
    train_dataset = train_dataset.map(tokenize, batched=True, remove_columns=["text"])
    eval_dataset = eval_dataset.map(tokenize, batched=True, remove_columns=["text"])

    # ─── 4. Training ───
    total_steps = len(train_dataset) // (BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS) * NUM_EPOCHS
    warmup_steps = int(total_steps * 0.03)

    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
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
        save_steps=500,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        remove_unused_columns=False,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )

    print(f"\nStarting Phase 2 training...")
    print(f"  Total steps: {total_steps:,}")
    print(f"  Warmup steps: {warmup_steps}")

    trainer.train()

    # ─── 5. Save ───
    print(f"\nSaving instruction-tuned model to {OUTPUT_DIR}")
    model.save_pretrained(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))
    print(f"\n✓ Phase 2 complete! Model saved to {OUTPUT_DIR}")
    print(f"  Test with: python3 scripts/chat_zomi.py --model {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
