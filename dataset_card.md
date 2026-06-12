---
license: cc0-1.0
language:
- zom (Zomi/Tedim)
size_categories:
- 100M-1B
pretty_name: Zomi Dataset
tags:
- zomi
- tedim
- zo
- low-resource language
- NLP
- language preservation
---

# Zomi Dataset

The largest Zomi (Tedim/Zo) language dataset ever assembled.

**3,000,000+ sentences · 211,000,000+ characters · 36,000+ unique words**

## Quick Start

```python
from datasets import load_dataset

ds = load_dataset("paumkim/zomi-dataset", split="train")
print(len(ds))  # 3,000,000+
print(ds[0]["text"])
```

## Sources

| Source | Volume |
|--------|--------|
| Tedim Bible (1932) | 30,000+ verses |
| YouTube comments | 1,400+ lines |
| News articles | 100+ |
| Blog posts | 50+ |
| Worship songs | 1,000+ |
| Dictionary entries | 130,000+ |
| Textbooks | K-4 |
| Web corpus | 2,600,000+ sentences |

## Use Cases

- LLM fine-tuning (continued pre-training)
- Tokenizer training
- Machine translation
- Text-to-speech
- Spell checking
- Language preservation

## License

CC0 1.0 Universal — Public Domain
