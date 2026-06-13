#!/bin/bash
# Live evaluation of Zomi model during training
# Run on the pod to check progress

POD_CMD="ssh -p 11384 root@154.54.102.49"

# Zomi test prompts - from Bible, conversation, news
PROMPTS=(
    "Pasian in vantung le"
    "Ka unau te, note khempeuh"
    "Tuni nitaklam ah"
    "Zomi gam ah"
    "Khristmas ni ah"
)

CHECKPOINT_DIR="/workspace/zomi-qlora-v1"

echo "=== Zomi Model Evaluation ==="
echo ""

for CP in $($POD_CMD "ls -d $CHECKPOINT_DIR/checkpoint-* 2>/dev/null | sort -t'-' -k2 -n | tail -3"); do
    STEP=$(echo $CP | grep -oP '\d+$')
    echo "--- Step $STEP ---"
    
    for PROMPT in "${PROMPTS[@]}"; do
        echo "Prompt: $PROMPT"
        # Generate using the checkpoint
        $POD_CMD "cd /workspace && python3 -c '
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import sys

model_path = \"$CP\"
tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16,
    device_map=\"auto\",
)

prompt = \"$PROMPT\"
inputs = tokenizer(prompt, return_tensors=\"pt\").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=50, temperature=0.7, do_sample=True)
text = tokenizer.decode(outputs[0], skip_special_tokens=True)
# Remove the prompt from output
if text.startswith(prompt):
    text = text[len(prompt):]
print(f\"  -> {text[:100].strip()}\n\")
' 2>/dev/null" || echo "  -> (model not ready yet)"
    done
done

echo "=== Done ==="
