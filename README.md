# 📜 lelestory.scripting

**Component 2 of 4: Scripting, Image Prompts & Gatekeeper 2** for LeLe Storybook Video Engine (`@lelehoctiengtrung`).

## Overview
- Generates line-by-line bilingual dialogues, Pinyin tone annotations, and vocabulary breakdowns.
- Generates platform-tailored visual prompts formatted with prefix `[PLATFORM-POSTID-SLIDE-RATIO-STYLE]`.
- Generates multi-platform SEO metadata (YouTube Shorts, TikTok, Facebook Reels).
- Enforces **Gatekeeper 2 (GK2)**:
  - Dialogue structure & 1:1 Pinyin verification.
  - Image prompt prefix syntax validation.
  - Metadata schema compliance.
- Runs 100% on **GitHub Actions Cloud Runners** (`ubuntu-22.04`) - strictly enforcing the **Zero-VPS Ban**.

## Local Development & Testing
```bash
pip install -r requirements.txt
pytest tests/
python src/gatekeeper2.py --idea path/to/idea_gk1.json --output artifacts/script_gk2.json
```
