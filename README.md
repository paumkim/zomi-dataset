# Zomi Dataset

A comprehensive collection of Zomi (Tedim/Zo) language materials for NLP,
AI training, and language preservation.

👉 **Website:** https://paumkim.github.io/zomi-website/
👉 **Dataset:** https://github.com/paumkim/zomi-dataset

---

## 📊 Clean Corpus

**`data/zomi_clean.txt`** — 65,008 lines · 8.7M characters
- Tedim Bible (1932) — 30K+ verses
- Zomipedia — 847 articles (biographies, history, traditional laws)
- Worship lyrics — Zomi worship songs
- Zolai textbooks — sentences from grades K-4
- All personal info removed
- Modern merge rules applied (particles attached, consistent spelling)

## 📚 Textbooks

**`Sinna/`** — Golden Zolai educational textbooks (1980s)
- Kindergarten through Grade 4
- Grammar Volume I
- Zomi History (1899-2013)
- Standard Format style guide
- PDFs + extracted text (both raw and normalized)

## 🔧 Normalizer

**`normalize/normalizer.py`** — Zomi spelling normalizer
- 15+ merge rules (te, ding, ta, ah, ki, cing, gah, la, 'n, reduplication, etc.)
- Privacy cleaner (email, social handles, IDs)
- Hyphen/apostrophe expander

## 📖 Documentation

| File | Description |
|------|-------------|
| `docs/ZOMI_SPELLING_GUIDE.md` | Complete spelling reference |
| `docs/ZOMI_SPELLING_EXPLAINED.md` | Quick guide for Zomi speakers |
| `Sinna/ZOMI_GOLDEN_LESSONS.md` | 13 lessons from the textbooks |

## 🗂 Repo Structure

```
zomi-dataset/
├── data/           ← Clean corpus and source texts
├── Sinna/          ← Golden textbooks (PDFs + text)
├── normalize/      ← Spelling normalizer
├── crawl/          ← Web scrapers
├── docs/           ← Spelling guides
├── detect/         ← Language detection profile
└── config.py       ← Dataset configuration
```

## 🤖 AI Training

The clean corpus (`data/zomi_clean.txt`) is ready for:
- Language model training (LLM fine-tuning)
- Tokenizer training
- Spell-checking models
- Text-to-speech training
- Machine translation (paired with English texts)

## License

Text content is extracted from publicly available sources for linguistic
and educational purposes. The Zomi language itself is the living heritage
of the Zomi people.

---

Built for the Zomi community by the Zomi community.
