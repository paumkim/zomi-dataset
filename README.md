# Zomi Dataset 🔥

**The largest Zomi (Tedim/Zo) language dataset ever assembled — 3M+ sentences, 211M+ characters, 36K+ unique words.**

A comprehensive collection for NLP, AI training, and language preservation.

👉 **Website:** https://paumkim.github.io/zomi-website/
👈 **Dataset Repo:** https://github.com/paumkim/zomi-dataset
👉 **Size:** 3.6 GB · 1,060 files · 211,000,000+ characters

---

## 📊 At a Glance

| Metric | Value |
|--------|-------|
| Total sentences | **3,000,000+** |
| Total characters | **211,000,000+** |
| Unique words | **36,000+** |
| Dictionary entries | **130,000+** |
| Worship songs | **1,000+** (with keys/BPM) |
| Bible verses | **30,000+** (Tedim 1932) |
| Textbooks | **Kindergarten → Grade 4** |
| News articles | **100+** (Tedim Post) |
| Blog posts | **50+** (Zomi Angvaan, Tongdam, Galhiam) |
| YouTube comments | **1,400+** (SEA diaspora) |
| Repository size | **3.6 GB · 1,060 files** |

## 📖 Clean Corpus

The corpus is split into 4 parts (each under 100MB for GitHub):

| File | Size | Content |
|------|------|---------|
| `data/zomi_clean_p1.txt` | 37 MB | Tedim Bible (Genesis–Psalms) + grammar |
| `data/zomi_clean_p2.txt` | 32 MB | Tedim Bible (Proverbs–Malachi) + hymns |
| `data/zomi_clean_p3.txt` | 58 MB | NT + textbooks + dictionary entries |
| `data/zomi_clean_p4.txt` | 76 MB | YouTube + news + blogs + worship songs |
| **Total** | **203 MB** | **3,000,000+ lines · 211,000,000+ chars** |

## 📚 All Sources

| Source | Type | Volume |
|--------|------|--------|
| **Tedim Bible (1932)** | Full OT + NT | 30,000+ verses (JSON + XML merged) |
| **Kaggle LLM Training Dataset** | Sentences | 2,600,000+ entries |
| **Tatoeba (Gemini-translated)** | English-Zomi parallel | 1,750,000 sentences |
| **Kaggle TongDot Dictionary** | Zomi-English | 75,000 entries |
| **Zomi Worship Songs** | Lyrics + keys/BPM | 1,000+ songs |
| **Danish-Zomi Ordbog** | Danish-Zomi dictionary | 210 pages OCR'd |
| **Hauhna leh Khansauna** | Book (Do Khup) | 4,400+ lines |
| **Zomipedia** | News articles | 847 articles |
| **Tedim Post** | News articles | 109 articles |
| **YouTube (SEA diaspora)** | Comments + descriptions | 1,400+ lines |
| **Zomi Angvaan / Tongdam** | Blog posts | 50+ posts |
| **Zomi Ordbog (Yumpu)** | Danish-Zomi dictionary | 210 pages OCR'd |
| **Paite Grammar (DLI)** | Grammar reference | 115 pages OCR'd |
| **Your Google Drive** | Personal vocabulary | 7+ sheets |
| **Pau Cin Hau Script** | Traditional writing system | Documented reference |
| **Praise & Worship + Galhiam blogs** | Song lyrics | 50+ songs |

## 🔧 Normalizer

**`normalize/normalizer.py`** — 400+ lines of Zomi spelling rules:

| Rule | Example |
|------|---------|
| Prefix `ki` (merge right) | `ki` + `cing` → `kicing` |
| Future `ding` (merge left) | `paai` + `ding` → `paaiding` |
| Perfective `ta` (merge left) | `om` + `ta` → `omta` |
| Locative `ah` (merge left) | `khawm` + `ah` → `khawmah` |
| Plural `te` (merge left) | `mi` + `te` → `mite` |
| Agentive `'n` (keep apostrophe) | `Zeisu` + `'n` → `Zeisu'n` |
| Reduplication | `sem` + `sem` → `semsem` |
| Berry suffix `gah` (merge left) | `sing` + `gah` → `singgah` |
| Mizoram spelling fix | `Toupa` → `Topa` |
| Privacy cleaner | Removes emails, handles, IDs |

## 📖 Documentation

| File | What it covers |
|------|---------------|
| `docs/ZOMI_SPELLING_GUIDE.md` | Complete spelling rules, vowel length, grammar |
| `docs/ZOMI_SPELLING_EXPLAINED.md` | Quick guide for sharing with Zomi speakers |
| `Sinna/ZOMI_GOLDEN_LESSONS.md` | 13 lessons from the golden textbooks |
| `docs/CINGNO_AI_VISION.md` | The original vision for Cingno AI |
| `docs/PAU_CIN_HAU_SCRIPT.md` | Traditional Zomi writing system |
| `docs/llm_training_guide.md` | How to train an AI on Zomi |

## 🗂 Repo Structure

```
zomi-dataset/                    (3.6 GB · 1,060 files)
├── data/                        ← Clean corpus + all source texts
│   ├── zomi_clean_p1-4.txt      ← Main corpus (203 MB total)
│   └── source files             ← Raw extraction from each source
├── Sinna/                       ← Golden textbooks (PDFs + text)
│   ├── pdf/                     ← Organized K-4, grammar, history
│   └── text/                    ← Raw OCR + normalized versions
├── normalize/                   ← Spelling normalizer
│   └── normalizer.py            ← 15+ merge rules
├── crawl/                       ← Web scrapers
├── docs/                        ← Spelling guides + references
├── detect/                      ← Zomi language detection profile
└── config.py                    ← Dataset configuration
```

## 🌐 Website

The Zomi Spelling Guide is also available as a website:
**https://paumkim.github.io/zomi-website/**

Covers: spelling rules, grammar essentials, particles & word structure,
numbers, example texts, golden textbooks, and the Tedim Bible downloads.

## 🤖 AI Training

This dataset is ready for:
- **LLM fine-tuning** — train any model (Llama, Qwen, Gemma) to speak Zomi
- **Tokenizers** — build a Zomi-specific tokenizer
- **Translation models** — paired English-Zomi data included
- **Text-to-speech** — the clean corpus is pronunciation-ready
- **Spell-checking** — the normalizer shows how Zomi spelling works
- **Music AI** — 1,000+ songs with key, BPM, and time signature metadata

### 🤖 Zomi AI Model

The first Zomi-speaking AI is live on Hugging Face:
- **Model:** [paumkim/zomi-qlora-v1](https://huggingface.co/paumkim/zomi-qlora-v1)
- **Chat:** `python chat_zomi.py` or `python gradio_chat.py`

See the **[Zomi Language Guide](https://paumkim.github.io/zomi-website/)** for spelling rules, grammar, and AI training docs.

## 🙏 Acknowledgments

Built by **Paumkim** with the dream of **Cingno AI** — a Zomi language AI assistant.
All sources are publicly available, collected from the open web for the
preservation and advancement of the Zomi (Tedim) language.

**"Your language deserves a digital backbone. Now it has one."**

---

Dammaw! 🔥
