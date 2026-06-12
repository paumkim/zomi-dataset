# Zomi AI — Project Roadmap

## Core Strategy: Belonging First, AI Second

- 📖 **Laisiangtho (Bible)** → the door. Every Zomi speaker wants this.
- 🎵 **La (Lyrics)** → the hook. Worship songs with chords. Church, youth, family.
- 🤖 **AI Kammal (AI)** → the treasure. Discovered when they're ready.

People come for the Bible and songs. They stay for the AI. Belonging is the feature.

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
