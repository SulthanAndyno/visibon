"""Handler pesan dan perintah untuk Telegram Bot VisiBon."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from visibon.db.repository import (
    get_monthly_summary,
    get_or_create_user,
    get_recent_receipts,
    save_receipt,
)
from visibon.db.session import get_sessionmaker
from visibon.money import format_rupiah
from visibon.pipeline import ScanResult, scan
from visibon.preprocess import load_image


def _month_name(m: int) -> str:
    names = [
        "",
        "Januari",
        "Februari",
        "Maret",
        "April",
        "Mei",
        "Juni",
        "Juli",
        "Agustus",
        "September",
        "Oktober",
        "November",
        "Desember",
    ]
    return names[m] if 1 <= m <= 12 else str(m)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    name = update.effective_user.first_name or "Teman"
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        await get_or_create_user(
            session,
            telegram_id=update.effective_user.id,
            username=update.effective_user.username,
            first_name=name,
        )

    text = (
        f"Halo *{name}*! 👋\n\n"
        "Aku *VisiBon Bot* 🧾\n"
        "_Biar receh pun ketahuan larinya ke mana!_\n\n"
        "📸 *Cara pakai:* Cukup kirimkan foto struk belanjaanmu ke chat ini. "
        "Aku bakal langsung baca item, harga, dan totalnya secara otomatis pakai GPU lokal kamu!\n\n"
        "Perintah yang tersedia:\n"
        "📊 /rekap — Rekap pengeluaran bulan ini\n"
        "📜 /riwayat — 5 struk belanja terakhir\n"
        "💡 /bantuan — Tips foto struk biar akurat"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_bantuan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    text = (
        "💡 *Tips Foto Struk Biar Hasil Maksimal:*\n\n"
        "1. *Pencahayaan cukup*: Jangan terlalu gelap atau silau.\n"
        "2. *Kontras*: Letakkan struk di atas meja gelap/berwarna.\n"
        "3. *Fokus*: Pastikan teks struk tidak buram (bot otomatis mendeteksi blur).\n"
        "4. *Bagian penting*: Pastikan baris tanggal, daftar barang, dan angka Total terlihat lengkap."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_rekap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    now = datetime.now()
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        user = await get_or_create_user(session, telegram_id=update.effective_user.id)
        summary = await get_monthly_summary(session, user.id, now.year, now.month)

    total_spent = format_rupiah(summary["total_spent"])
    count = summary["total_receipts"]
    month_str = f"{_month_name(now.month)} {now.year}"

    if count == 0:
        await update.message.reply_text(
            f"📊 *Rekap Pengeluaran ({month_str})*\n\n"
            "Belum ada struk yang dicatat bulan ini. Yuk mulai kirim foto struk belanjaanmu!",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    lines = [
        f"📊 *Rekap Pengeluaran ({month_str})*\n",
        f"💰 *Total Pengeluaran:* `{total_spent}`",
        f"🧾 *Total Transaksi:* {count} struk\n",
        "*Rincian per Kategori:*",
    ]
    for cat, info in summary["by_category"].items():
        cat_total = format_rupiah(info["total"])
        lines.append(f"• *{cat}*: `{cat_total}` ({info['count']} struk)")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_riwayat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    session_factory = get_sessionmaker()
    async with session_factory() as session:
        user = await get_or_create_user(session, telegram_id=update.effective_user.id)
        receipts = await get_recent_receipts(session, user.id, limit=5)

    if not receipts:
        await update.message.reply_text(
            "Belum ada riwayat struk belanja. Kirim foto struk pertamamu sekarang! 📸"
        )
        return

    lines = ["📜 *5 Struk Belanja Terakhir:*\n"]
    for i, r in enumerate(receipts, start=1):
        merchant = r.merchant or "Toko Tidak Dikenal"
        date = r.date or "-"
        total = format_rupiah(r.total) if r.total is not None else "Rp 0"
        lines.append(f"{i}. *{merchant}* ({date})\n   💰 `{total}` · _{r.category}_")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message or not update.message.photo:
        return

    # Ambil resolusi foto tertinggi
    photo = update.message.photo[-1]
    status_msg = await update.message.reply_text(
        "🧾 *Struk diterima!* Lagi diproses sama AI lokal di GPU kamu... ⏳",
        parse_mode=ParseMode.MARKDOWN,
    )
    await update.effective_chat.send_action(ChatAction.TYPING)

    # Simpan file foto sementara
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    file_path = raw_dir / f"tg_{update.effective_user.id}_{now_str}.jpg"

    tg_file = await photo.get_file()
    await tg_file.download_to_drive(custom_path=file_path)

    # Jalankan pipeline scan di worker thread (biar tidak memblok loop async bot)
    try:
        image = load_image(file_path)
        scan_res: ScanResult = await asyncio.to_thread(scan, image)
    except Exception as exc:  # noqa: BLE001
        await status_msg.edit_text(f"❌ *Gagal memproses struk:* {exc}")
        return

    # Simpan ke SQLite
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        user = await get_or_create_user(
            session,
            telegram_id=update.effective_user.id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name,
        )
        record = await save_receipt(
            session,
            user_id=user.id,
            receipt=scan_res.receipt,
            is_valid=scan_res.validation.is_valid,
            image_path=str(file_path),
        )

    # Format hasil balasan ke Telegram
    r = scan_res.receipt
    merchant = r.merchant or "Struk Belanja"
    date_str = f"{r.date or '-'} {r.time or ''}".strip()
    pay_str = f"💳 {r.payment_method}" if r.payment_method else ""
    cat_str = f"🏷️ *{r.category or 'Lainnya'}*"

    lines = [
        f"🧾 *{merchant}*",
        f"📅 {date_str} {pay_str}",
        f"{cat_str}\n",
        "*Daftar Belanja:*",
    ]

    for item in r.items:
        subtotal_str = format_rupiah(item.subtotal)
        lines.append(f"• {item.qty:g}x {item.name}: `{subtotal_str}`")

    lines.append("──────────────────────")
    if r.subtotal:
        lines.append(f"Subtotal : `{format_rupiah(r.subtotal)}`")
    if r.discount:
        lines.append(f"Diskon   : `- {format_rupiah(r.discount)}`")
    if r.tax:
        lines.append(f"Pajak    : `{format_rupiah(r.tax)}`")
    if r.service:
        lines.append(f"Service  : `{format_rupiah(r.service)}`")

    total_str = format_rupiah(r.total) if r.total is not None else "Rp 0"
    lines.append(f"*TOTAL    : {total_str}*")

    # Status validasi aritmetika
    if scan_res.validation.is_valid:
        lines.append("\n✅ _Hitungan struk terverifikasi valid._")
    else:
        lines.append("\n⚠️ _Ada selisih hitungan / diskon di struk._")

    latency_s = scan_res.latency_ms / 1000
    lines.append(f"\n_⚡ {latency_s:.1f}s via {scan_res.extractor}/{scan_res.model}_")

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🍕 Split Bill", callback_data=f"split_{record.id}"),
                InlineKeyboardButton("📊 Rekap Bulan Ini", callback_data="rekap"),
            ]
        ]
    )

    await status_msg.edit_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    if query.data == "rekap":
        now = datetime.now()
        session_factory = get_sessionmaker()
        async with session_factory() as session:
            user = await get_or_create_user(session, telegram_id=query.from_user.id)
            summary = await get_monthly_summary(session, user.id, now.year, now.month)

        total_spent = format_rupiah(summary["total_spent"])
        count = summary["total_receipts"]
        await query.message.reply_text(
            f"📊 *Rekap Pengeluaran ({_month_name(now.month)} {now.year})*\n\n"
            f"💰 *Total:* `{total_spent}` ({count} struk)",
            parse_mode=ParseMode.MARKDOWN,
        )
    elif query.data.startswith("split_"):
        receipt_id = query.data.split("_")[1]
        await query.message.reply_text(
            f"🍕 *Fitur Split Bill untuk Struk #{receipt_id}*\n"
            "Fitur ini siap diintegrasikan di Milestone berikutnya! Siapa saja yang mau patungan?",
            parse_mode=ParseMode.MARKDOWN,
        )
