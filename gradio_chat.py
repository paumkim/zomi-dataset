"""
Gradio chat interface for Zomi QLoRA model.

Usage:
    pip install gradio
    python gradio_chat.py
"""

import gradio as gr
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = "paumkim/zomi-qlora-v1"

def load_model():
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    return model, tokenizer

print("Loading model...")
model, tokenizer = load_model()

def chat(message, history):
    inputs = tokenizer(message, return_tensors="pt").to(model.device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=200,
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # Remove the input prompt from response
    response = response[len(message):].strip()
    return response

gr.ChatInterface(
    fn=chat,
    title="Zomi Chat",
    description="Chat with the Zomi language model (paumkim/zomi-qlora-v1)",
).launch(share=True)
