# Cloud Training Guide — Zomi LLM

A complete step-by-step guide to fine-tuning a language model on the Zomi corpus using cloud GPUs.

**Why cloud training?** The Zomi dataset has 3M+ lines (211M+ characters). Training on a laptop would take days or weeks. Cloud GPUs like RunPod give you access to professional hardware at ~$1.50/hour — a full training run costs **$5-10**.

---

## What You'll Get

| Output | Location |
|--------|----------|
| Trained model (Hugging Face) | `https://huggingface.co/paumkim/zomi-qlora-v1` |
| LoRA adapter weights | Merged into base model automatically |
| Training script | `cloud_train.py` |
| Corpus files | `data/zomi_clean_p1-4.txt` |

---

## Prerequisites

1. **Hugging Face account** — Free at [huggingface.co](https://huggingface.co)
   - Create a **User Access Token** at: `huggingface.co/settings/tokens`
   - Copy it — you'll need to paste it during setup
2. **RunPod account** — Free at [runpod.io](https://runpod.io)
   - Add **$10-15 credit** (debit/credit card)
3. **Zomi dataset** — Clone or download from [github.com/paumkim/zomi-dataset](https://github.com/paumkim/zomi-dataset)
   - You need the 4 files: `zomi_clean_p1.txt` through `p4.txt`
4. **Basic terminal knowledge** — Copy-pasting commands is all you need

---

## Step 1: Deploy a GPU on RunPod

1. Go to [console.runpod.io](https://console.runpod.io)
2. Click **Pods** → **Deploy**
3. Under **Community Cloud**, find **A100 SXM** (80GB, $1.49/hr)
   - A100 PCIe ($1.39/hr) works fine too
4. Template: Select **RunPod PyTorch 2.1**
5. Container Disk: **20 GB**
6. Click **Deploy Now**

Your pod will start in ~1-2 minutes. Wait for the status to show **"Ready"**.

### GPU Options Explained

| GPU | VRAM | Price/hr | Best For |
|-----|------|----------|----------|
| A100 SXM | 80 GB | $1.49 | QLoRA on 7B-13B models (recommended) |
| A100 PCIe | 80 GB | $1.39 | Same performance, slightly slower memory |
| RTX 6000 Ada | 48 GB | $0.77 | Budget option, fits 7B QLoRA |
| A40 | 48 GB | $0.44 | Cheapest option, enough for 7B QLoRA |

For Qwen 2.5 7B with QLoRA, any 48GB+ GPU works. A100 is recommended for speed.

---

## Step 2: Connect and Upload Files

Click **Connect** on your pod row. You have two options:

- **Web Terminal** (easiest) — opens in your browser, no passwords
- **SSH** — for advanced users, use `ssh -p <port> root@<ip>`

### Upload using File Browser

In the Web Terminal, look for the **File Browser** tab (next to Terminal):

1. Navigate to `/workspace/data/`
2. Click **Upload** and select your 4 corpus files:
   - `zomi_clean_p1.txt`
   - `zomi_clean_p2.txt`
   - `zomi_clean_p3.txt`
   - `zomi_clean_p4.txt`
3. Navigate to `/workspace/`
4. Upload `cloud_train.py`

OR use the terminal (if your files are on your local machine):

```bash
scp -P <PORT> /path/to/zomi_clean_p*.txt root@<IP>:/workspace/data/
scp -P <PORT> /path/to/cloud_train.py root@<IP>:/workspace/
```

You'll need the password from RunPod's Connect dialog.

---

## Step 3: Install Dependencies

In the Web Terminal, paste:

```bash
pip install transformers accelerate peft bitsandbytes datasets huggingface_hub
```

Wait for installation to finish (~1 minute).

---

## Step 4: Login to Hugging Face

```bash
hf auth login
```

Paste your Hugging Face token when prompted. This allows the script to upload the trained model to your Hugging Face account.

---

## Step 5: Run Training

```bash
cd /workspace && python cloud_train.py
```

### What the Script Does (In Order)

1. **Loads corpus** — Reads all 4 clean text files (~3M lines)
2. **Splits data** — 95% training, 5% evaluation
3. **Downloads Qwen 2.5 7B** — A multilingual 7-billion-parameter model
4. **Applies 4-bit QLoRA** — Quantizes the model to save memory, adds LoRA adapters (rank 128)
5. **Trains for 5 epochs** — The model learns Zomi through next-token prediction
6. **Merges adapter** — Combines LoRA weights into the base model
7. **Uploads to Hugging Face Hub** — Saved as `paumkim/zomi-qlora-v1`

---

## Step 6: Monitor Training

While training, you'll see output like:

```
Step | Training Loss | Eval Loss
  10 |     2.450000  |
  20 |     2.120000  |
 200 |     1.890000  |    1.9500
 400 |     1.720000  |    1.8100
```

| Metric | Target | Meaning |
|--------|--------|---------|
| Training loss | Decreasing | Model is learning |
| Eval loss | Decreasing (target: <2.0) | Model generalizes to new data |
| Perplexity | Lower is better (<10 is good) | How "surprised" the model is |

If eval loss stops decreasing for 500+ steps, the model has converged. You can press **Ctrl+C** safely — the best checkpoint is saved automatically.

### Training Duration & Cost

| Epochs | Approx Time | Cost (A100 SXM) |
|--------|-------------|-----------------|
| 1 | ~40 min | ~$1 |
| 3 | ~2 hours | ~$3 |
| 5 (default) | ~3-4 hours | ~$5-7 |

---

## Step 7: After Training — Test Your Model

The model is automatically uploaded to Hugging Face. To test it:

Create a file `test_zomi.py`:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "paumkim/zomi-qlora-v1"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype="auto",
    device_map="auto",
)

prompt = "Pasian in vantung le leitung a"
inputs = tokenizer(prompt, return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=100)
print(tokenizer.decode(outputs[0]))
```

This works on any computer (even without GPU, just slower).

---

## Configuration Options

Edit `cloud_train.py` to customize:

```python
BASE_MODEL = "Qwen/Qwen2.5-7B"          # Change to any model on HF
NUM_EPOCHS = 5                           # More = better learning, slower
LORA_R = 128                             # Higher = more capacity, more memory
LEARNING_RATE = 3e-4                     # Lower = slower but more stable
MAX_SEQ_LENGTH = 2048                    # Longer = captures more context
BATCH_SIZE = 4                           # Reduce if OOM errors
```

### Alternative Base Models

| Model | Size | Tokenizer | Best For |
|-------|------|-----------|----------|
| Qwen 2.5 7B | 7B | 152k vocab | **Non-English languages** (recommended) |
| Llama 3 8B | 8B | 128k vocab | General purpose, most popular |
| Gemma 2 9B | 9B | 256k vocab | Efficient, good for small data |
| Mistral 7B | 7B | 32k vocab | Fast inference, less multilingual |

**Qwen 2.5 is recommended** because it has the best tokenizer for non-English languages — it won't waste tokens breaking Zomi words into small fragments.

---

## Troubleshooting

### "Subprocess died during map operation"

**Cause**: Ran out of memory during tokenization.

**Fix**: In `cloud_train.py`, change:
```python
num_proc=4,
```
to:
```python
num_proc=1,
```

### CUDA Out of Memory

**Cause**: GPU ran out of VRAM.

**Fix**: Reduce batch size or sequence length:
```python
BATCH_SIZE = 2           # instead of 4
MAX_SEQ_LENGTH = 1024    # instead of 2048
```

### "SFTTrainer got unexpected keyword argument"

**Cause**: New version of TRL library changed API.

**Fix**: We use standard `Trainer` instead — already handled in `cloud_train.py`.

### Can't find RunPod password

Click **Connect** on your pod — the password is in the popup. Or use **Web Terminal** (no password needed).

---

## How It Works — Technical Summary

### Continued Pre-Training vs Fine-Tuning

- **Continued pre-training** (what we're doing): Feed the model raw Zomi text. It learns to predict the next word. This teaches the model *language* — grammar, vocabulary, style.
- **Supervised fine-tuning (SFT)**: Feed the model question-answer pairs. This teaches the model *conversation* — how to answer questions.

This guide covers continued pre-training. To make a chatbot, you'd need a second step with instruction data.

### QLoRA Explained

QLoRA (Quantized Low-Rank Adaptation):
1. **Quantize** the base model to 4-bit (saves 4x memory)
2. **Add small adapter matrices** (LoRA) that learn the new language
3. **Train only the adapters** (~4% of total parameters)
4. **Merge** adapters back into the base model for deployment

This means:
- You can train a 7B model on a single GPU (normally needs 4x more VRAM)
- You keep all the base model's general knowledge
- The adapter "specializes" it to Zomi

### Why Rank 128?

Standard LoRA uses rank 8-64. We use **rank 128** to give the adapter more capacity to learn Zomi from scratch. Think of it as giving the model more "new memory" for the language.

---

## Files in This Guide

| File | Purpose |
|------|---------|
| `cloud_train.py` | The training script — upload to RunPod and run |
| `docs/cloud_training_guide.md` | This guide |
| `data/zomi_clean_p1.txt` | Clean Zomi corpus (part 1 of 4) |
| `data/zomi_clean_p2.txt` | Clean Zomi corpus (part 2 of 4) |
| `data/zomi_clean_p3.txt` | Clean Zomi corpus (part 3 of 4) |
| `data/zomi_clean_p4.txt` | Clean Zomi corpus (part 4 of 4) |

---

## Next Steps After Training

Once you have a model that speaks Zomi:

1. **Build instruction data** — Create JSONL files with Zomi questions and answers
2. **Supervised fine-tuning** — Train the model to follow instructions (same process, different dataset)
3. **Deploy a chatbot** — Use Gradio or a simple web app
4. **Build a Zomi tokenizer** — For more efficient tokenization of Zomi text

See `docs/llm_training_guide.md` for more on evaluating the model's understanding of Zomi.
