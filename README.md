# 👁️ VisiBon

> **Vision Intelligence for Indonesian Receipts & Smart Split Bill**  
> *Foto struk belanja, AI baca dan catat otomatis ke database.*

VisiBon mengubah **foto struk belanja Indonesia** jadi **data pengeluaran terstruktur** secara otomatis, plus fitur **split bill** yang adil untuk nongkrong bareng teman.

Dibangun dengan Computer Vision klasik (OpenCV) + Vision Language Model (VLM) yang bisa jalan **100% offline di GPU 4 GB** (RTX 3050 Laptop via Ollama).

---

## ✨ Fitur (Roadmap)

- [x] Preprocessing OpenCV: deteksi struk, koreksi perspektif, CLAHE, deteksi blur
- [x] Extractor pluggable: **Ollama (Qwen3-VL lokal)** & **Gemini (cloud)**
- [x] Validasi aritmetika (anti-halusinasi angka), dukung PPN termasuk harga
- [x] CLI + REST API (FastAPI)
- [x] SQLite Database (async SQLAlchemy): pencatatan user, struk, dan item belanja
- [x] Telegram Bot (`python-telegram-bot`): foto struk dari HP langsung tercatat + command `/rekap`, `/riwayat`
- [ ] Fitur Split Bill interaktif (minggu 4)
- [ ] Baseline PaddleOCR + benchmark (minggu 5)
- [ ] Fine-tune Donut (bonus)

## 🏗️ Arsitektur

```
Foto ─▶ Preprocess (OpenCV) ─▶ Extractor ─▶ Validator ─▶ JSON / DB
                                  ├─ ollama  (qwen3-vl:2b, lokal)
                                  ├─ gemini  (gemini-3.8-flash, cloud)
                                  └─ ocr     (PaddleOCR + rules, soon)
```

## 🚀 Quick Start

```bash
# 1. Install dependency
uv sync                      # tambah --extra gemini kalau mau pakai Gemini
cp .env.example .env

# 2. Siapkan VLM lokal
ollama serve                 # terminal terpisah
ollama pull qwen3-vl:2b

# 3. Cek kesiapan
uv run visibon doctor

# 4. Coba!
uv run python scripts/make_synthetic_receipt.py      # struk sintetis buat tes
uv run visibon preprocess data/raw/synthetic_01.jpg  # lihat hasil di outputs/preprocess/
uv run visibon scan data/raw/struk_kamu.jpg --debug outputs/debug
uv run visibon scan data/raw/struk_kamu.jpg --json

# 5. API & Bot
uv run uvicorn visibon.api:app --reload
curl -F file=@data/raw/struk_kamu.jpg localhost:8000/extract

# Jalankan Telegram Bot (set TELEGRAM_BOT_TOKEN di .env dulu)
uv run visibon bot
```

## 🧠 Pilihan VLM untuk GPU 4 GB

| Model | VRAM (Q4) | Kecepatan | Akurasi | Catatan |
|---|---|---|---|---|
| `qwen3-vl:2b` | ~2 GB | ⚡⚡⚡ | ⭐⭐⭐ | **Default** — muat penuh di GPU |
| `qwen3-vl:4b` | ~3.5 GB | ⚡⚡ | ⭐⭐⭐⭐ | Mepet, sebagian offload ke CPU |
| `gemini-3.8-flash` | cloud | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | Free tier, butuh internet |

Tip hemat VRAM: turunkan `VISIBON_MAX_IMAGE_SIDE` (mis. 1024) supaya token gambar lebih sedikit.

## 🧪 Test

```bash
uv run pytest -q
```

## 📊 Benchmark

_Coming soon — perbandingan akurasi, latency, dan biaya antar extractor pada test set struk asli._

## 🔒 Privasi

Folder `data/raw` di-gitignore. Mode `ollama` memproses struk **100% lokal**; mode Gemini memakai `store=False`.
