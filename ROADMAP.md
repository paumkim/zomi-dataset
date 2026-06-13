# Zomi AI — Project Roadmap

## Core Strategy: Belonging First, AI Second

- 📖 **Laisiangtho (Bible)** → the door. Every Zomi speaker wants this.
- 🎵 **La (Lyrics)** → the hook. Worship songs with chords. Church, youth, family.
- 🤖 **AI Kammal (AI)** → the treasure. Discovered when they're ready.

People come for the Bible and songs. They stay for the AI. Belonging is the feature.

## AI Strategy: Hybrid by Default

- **Cloud AI:** Works on first launch, ~30 MB app size, needs internet
- **Optional offline model:** Download ~1.8 GB from Settings (on WiFi)
- **Bible + Lyrics + Textbooks:** Work offline from day one, no download needed
- **Philosophy:** Every Pau user gets a great experience regardless of phone or internet

## Two-Phase Training Plan

| Phase | What | Status | Data | Cost |
|-------|------|--------|------|------|
| **Phase 1** | Continued pre-training — model learns to **speak** Zomi | 🏃 Running on A100 | 3M+ lines raw Zomi text | ~$60 |
| **Phase 2** | Instruction fine-tuning — model learns to **translate** on command | ✅ Ready to launch | 500K EN↔ZOMI instruction pairs | ~$15-20 |
| **Final** | Zomi conversational model that speaks AND translates | ⏳ After Phase 1 finishes | Both datasets combined | ~$80 total |

### Phase 2 Launch Command
```bash
python3 scripts/train_instructions.py
```

## Disaster Recovery — Self-Healing Training Pipeline

The training pod has a watchdog system that auto-recovers from crashes:

| Component | What it does |
|-----------|-------------|
| `scripts/watchdog.sh` | Checks every 60s if training is alive. If not, restarts from latest checkpoint. |
| `cloud_train.py` (auto-resume) | Detects existing checkpoints and resumes from the latest step automatically. |
| Checkpoints every 200 steps | Saved to `/workspace/zomi-qlora-v1/checkpoint-N/`. Max 2 kept at a time. |
| Hugging Face auto-upload | After training finishes, model merges and uploads to HF automatically. |

**What happens in a crash:**
1. Training dies (I/O error, OOM, pod restart)
2. Watchdog detects missing Python process within 60 seconds
3. Watchdog restarts `cloud_train.py`
4. Script finds latest checkpoint (e.g. `checkpoint-2000`)
5. Trainer resumes from that step — no progress lost
6. Training continues as if nothing happened

**To deploy watchdog on a new pod:**
```bash
scp scripts/watchdog.sh root@<pod>:/workspace/
ssh root@<pod> "chmod +x /workspace/watchdog.sh && nohup bash watchdog.sh &"
```

## Status (June 12, 2026)
- ✅ Zomi dataset collected (3M+ lines)
- ✅ Website built (spelling guide, Bible PDF, AI guides)
- ✅ Personal agent + Bridge server set up
- 🏃 **Training running** on A100 SXM (40 hrs, $60)
- 🔄 Hugging Face upload will auto-complete after training

## Next Steps

### Phase 1: Model Release (Week 1)
- [ ] Verify model on Hugging Face: `paumkim/zomi-qlora-v1`
- [ ] Test local inference: `python3 chat_zomi.py`
- [ ] Run evaluation prompts (save to `data/zomi_eval_results.json`)
- [ ] Share with Zomi community for feedback

### Phase 2: Android App (Week 2-3)
- [ ] Quantize model to GGUF format (4-bit) → ~1.8GB
- [ ] Build Android app using llama.cpp Android SDK
- [ ] Offline chat UI — type Zomi, get Zomi responses
- [ ] Package as standalone APK
- [ ] Publish (APK direct download or Google Play)

### Phase 3: Polish & Extend (Week 4+)
- [ ] Collect user feedback on model quality
- [ ] Train v2 with improvements
- [ ] Add translation adapter (Zomi ↔ English)
- [ ] Add voice input support
- [ ] Build web demo (Gradio)

## Android App Spec
- **Model format:** GGUF (4-bit quantized, ~1.8GB)
- **Engine:** llama.cpp
- **Download:** On first launch, stream from Hugging Face
- **UI:** Simple chat interface
- **Offline:** Yes — 100% on-device
- **Requirements:** Android 10+, 4GB+ RAM, 3GB free storage

## Key Contacts
- Dataset: `github.com/paumkim/zomi-dataset`
- Website: `paumkim.github.io/zomi-website/`
- Model: `huggingface.co/paumkim/zomi-qlora-v1`
- Local agent: `python3 ~/.paumkim_agent.py`

## Bridge Server
- Runs on laptop at `127.0.0.1:9876`
- Auth: `paumkim_bridge_2026`
- Auto-starts: `~/.config/autostart/bridge.desktop`
