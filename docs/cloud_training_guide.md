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

This section walks you through every click and selection. Follow along on your screen.

### 1.1 Create a RunPod account

1. Go to [runpod.io](https://runpod.io)
2. Click **Sign Up** (top right)
3. Enter email, password — or sign in with Google/GitHub
4. Check your email for a verification link and click it
5. Log in to your account

### 1.2 Add credit

1. Go to **Billing** in the left sidebar
2. Click **Add Funds**
3. Enter **$10** (minimum) or **$15** (recommended — covers 10 hours of training)
4. Enter your card details and confirm

### 1.3 Deploy the pod

1. Go to **Pods** in the left sidebar
2. Click the blue **Deploy** button
3. Under **Community Cloud**, you'll see a list of GPUs with prices
4. Find **A100 SXM** (80GB, $1.49/hr) — it's usually near the top
   - Hover over it and click **Deploy**
   - If A100 SXM is unavailable, choose **A100 PCIe** ($1.39/hr) or **RTX 6000 Ada** ($0.77/hr, 48GB)
5. A configuration panel opens. Set these options:

| Setting | Value | Why |
|---------|-------|-----|
| **GPU Count** | **1** | Single GPU is enough for 7B QLoRA |
| **Template** | **RunPod PyTorch 2.1** | Has CUDA, torch, Python pre-installed |
| **Container Disk** | **20 GB** | Enough for your data + model weights |
| **Volume** | **None** (skip) | Not needed for single training run |

6. Click the blue **Deploy Now** button at the bottom

Your pod will show **"Status: Initializing"** for about 1-2 minutes. Wait until it changes to **"Ready"** and the power button turns green.

### 1.4 Check your pod is running

Once ready, you'll see:

```
┌─────────────────────────────────────────────┐
│  Pod Name           │  zomi-training-1       │
│  GPU                │  1× A100-SXM4-80GB    │
│  Status             │  ✅ Ready              │
│  Runtime            │  0:02:34               │
│  Cost               │  $0.06                 │
└─────────────────────────────────────────────┘
```

You are now being billed **$1.49 per hour**. Training takes 3-5 hours, so the total will be **$5-10**.

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

### 2.1 Open Web Terminal

1. In your RunPod dashboard, find your running pod
2. Click the **Connect** button (it's on the right side of your pod row)
3. A popup appears with connection options. Click **Web Terminal**
4. A new browser tab opens with a black terminal screen: `root@f5cb63ff210b:/#`

You are now inside your cloud pod — a Linux computer with an A100 GPU.

### 2.2 Upload your files

In the Web Terminal, look at the top of the page. You'll see two tabs:

```
┌─────────────┬──────────────┐
│  Terminal    │  File Browser │  ← Click this
└─────────────┴──────────────┘
```

1. Click **File Browser**
2. You'll see a file explorer. Navigate to `/workspace/data/` by clicking the folder path at the top and typing `/workspace/data/`
3. Click **Upload** (top bar) and select these 4 files from your computer:
   - `zomi_clean_p1.txt`
   - `zomi_clean_p2.txt`
   - `zomi_clean_p3.txt`
   - `zomi_clean_p4.txt`
4. Wait for upload to finish (shows 100% for each)
5. Navigate to `/workspace/` (click the up-arrow or path)
6. Upload `cloud_train.py`

**Verify files are there** — switch back to the **Terminal** tab and run:
```bash
ls /workspace/data/ && ls /workspace/cloud_train.py
```
You should see the 4 corpus files and `cloud_train.py` listed.

OR use the terminal (if your files are on your local machine):

```bash
scp -P <PORT> /path/to/zomi_clean_p*.txt root@<IP>:/workspace/data/
scp -P <PORT> /path/to/cloud_train.py root@<IP>:/workspace/
```

You'll need the password from RunPod's Connect dialog.

---

## Step 3: Install Dependencies

Make sure you're in the Web Terminal, then paste this exactly:

```bash
pip install transformers accelerate peft bitsandbytes datasets huggingface_hub
```

**What each package does:**

| Package | Purpose |
|---------|---------|
| `transformers` | Hugging Face's core library — loads models/tokenizers |
| `accelerate` | Distributes training across GPUs efficiently |
| `peft` | LoRA/QLoRA — the adapter method that saves memory |
| `bitsandbytes` | 4-bit quantization — shrinks model from 16GB to 4GB |
| `datasets` | Hugging Face dataset loading and processing |
| `huggingface_hub` | Upload your trained model to Hugging Face |

Wait for the installation to complete. You'll see progress bars for each package, then a message like:

```
Successfully installed transformers-4.52.0 peft-0.15.0 ...
```

**If pip throws an error**, try:
```bash
pip install --upgrade pip && pip install accelerate peft bitsandbytes datasets huggingface_hub
```

---

## Step 4: Login to Hugging Face

---

## Step 4: Login to Hugging Face

This step gives the script permission to upload your trained model to your Hugging Face account.

```bash
hf auth login
```

A prompt appears:

```
Token: 
```

Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) in your browser. If you don't have a token:

1. Click **New Token**
2. Name it something like "RunPod training"
3. Set permissions to **Write** (needed to upload models)
4. Click **Generate**
5. Copy the token (looks like `hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

Paste the token into the Web Terminal (right-click → Paste, or Ctrl+Shift+V). No asterisks will show — that's normal. Press **Enter**.

If successful, you'll see:
```
✓ Login successful
Your token has been saved to /root/.cache/huggingface/token
✓ Authenticated through git-credential store
```

**If `hf auth login` doesn't work**, try the old version:
```bash
huggingface-cli login
```

---

## Step 5: Run Training

### 5.1 Clear old processes (important!)

Before running training for the first time — or any time you restart a pod — **kill leftover Python processes** from previous failed runs. They eat GPU memory silently.

```bash
pkill -9 python 2>/dev/null; pkill -9 python3 2>/dev/null
```

Verify the GPU is clean:
```bash
nvidia-smi
```

Look for the **Memory-Usage** column. It should show **low numbers** like:

```
|   0  NVIDIA A100-SXM4-80GB          On  |   00000000:C1:00.0 Off |
| N/A   29C    P0             98W /  400W |    123MiB /  81920MiB  |
```

If it shows **>10,000 MiB** used, there are leftover processes. Check with `ps aux | grep python` and kill them manually, or just **Stop** and **Start** the pod from the RunPod dashboard.

### 5.2 Run the training

Now run this command:

```bash
cd /workspace && python cloud_train.py
```

**What you'll see** (step by step):

```
Loading Zomi corpus...
  Loaded zomi_clean_p1.txt: 763158 lines
  Loaded zomi_clean_p2.txt: 763158 lines
  Loaded zomi_clean_p3.txt: 763158 lines
  Loaded zomi_clean_p4.txt: 763157 lines
Total lines: 3,052,631
```

This loads your text data. Takes ~10 seconds.

```
Loading tokenizer: Qwen/Qwen2.5-7B
Loading model: Qwen/Qwen2.5-7B
Loading weights: 100% |████| 339/339 [00:26]
trainable params: 322,961,408 / 7,938,577,920 = 4.07%
```

This downloads the base model and applies LoRA. Takes ~1 minute. The 4.07% means only 4% of parameters will be trained — the rest are frozen in 4-bit.

```
Starting training...
  Total train samples: 2,899,999
  Warmup steps: 22656

Step | Training Loss
  10 |     2.4500
  20 |     2.1200
 200 |     1.8900    Eval loss: 1.9500
```

**Training has started.** This runs for 3-5 hours. Let it run — check back occasionally.

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

### Pod ran out of memory (OOM)

**Symptoms**: Container keeps restarting, `nvidia-smi` shows high GPU memory, or terminal shows OOM errors.

**Fix**: Clear old processes and verify GPU:
```bash
pkill -9 python 2>/dev/null; pkill -9 python3 2>/dev/null
nvidia-smi
```
If GPU memory is high (>10,000 MiB used), you likely have orphaned processes. Kill them or **Stop** and **Start** the pod from the RunPod dashboard. Always run `pkill -9 python` before starting a new training run.

### CUDA Out of Memory (OOM) during training

**Symptoms**: Training starts but crashes after a few steps with `torch.OutOfMemoryError`.

**Fix**: Reduce batch size — this halves GPU memory usage:
```bash
sed -i 's/BATCH_SIZE = 4/BATCH_SIZE = 2/' /workspace/cloud_train.py
```
Then re-run. Training will take ~2x longer but use half the memory.

### "Subprocess died during map operation"

**Cause**: Ran out of memory during tokenization (usually from `padding="max_length"`).

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

### "No columns in the dataset match the model's forward method"

**Cause**: The Trainer dropped the `text` column before the data collator could tokenize it.

**Fix**: Add this to `TrainingArguments` in the script:
```python
remove_unused_columns=False,
```
Already included in the latest `cloud_train.py`.

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

## The Scientist Workflow

The process we just went through is exactly how ML researchers work — at Google, Meta, or any AI lab. Here's the pattern:

```
1. Write script  ──→  Run it  ──→  Fails with error
                           ↓
2. Read error  ──→  Google/fix  ──→  Edit script  ──→  Re-run
                           ↓
3. Repeat step 2 until it works  (usually 5-20 cycles)
                           ↓
4. Training runs for hours  ──→  Monitor loss curves
                           ↓
5. Evaluate results  ──→  Tweak hyperparameters  ──→  Repeat from step 1
                           ↓
6. Document everything  ──→  Push to GitHub  ──→  Write the guide
```

### Real examples from this session

| Problem | Our Fix | Hours wasted |
|---------|---------|--------------|
| `overwrite_output_dir` removed | Just removed the line | 5 min |
| SFTTrainer API changed | Switched to standard Trainer | 10 min |
| Tokenizer argument renamed | Changed to `processing_class` | 5 min |
| DataCollator mismatch | Different args for TRL vs transformers | 10 min |
| Memory crash (padding) | Switched to on-the-fly tokenization | 30 min |
| Subprocess died (OOM) | Reduced `num_proc` or restarted pod | 15 min |
| `remove_unused_columns` | Added the flag to TrainingArguments | 5 min |
| GPU memory full from old runs | `pkill -9 python` + restart | 2 min |

**Total: ~1.5 hours of debugging for a 3-hour training run.** That's normal. In research labs, the ratio is often worse — weeks of debugging for days of training.

### Why this matters

Most people think science is: *have idea → run experiment → get result.*

Real science is: *have idea → try 50 ways to make it work → finally get result → realize the idea was wrong → start over.*

The documentation you're writing right now is what separates a one-time experiment from a reproducible process. Future you (or anyone else) can follow these steps and get the same result without repeating the 1.5 hours of debugging.

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
