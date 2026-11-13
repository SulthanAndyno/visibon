"""Aplikasi Telegram Bot VisiBon."""

from __future__ import annotations

import asyncio
import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from visibon.bot.handlers import (
    cmd_bantuan,
    cmd_rekap,
    cmd_riwayat,
    cmd_start,
    handle_callback,
    handle_photo,
)
from visibon.config import get_settings
from visibon.db.session import init_db

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("visibon.bot")


def build_bot_app(token: str) -> Application:
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("rekap", cmd_rekap))
    app.add_handler(CommandHandler("riwayat", cmd_riwayat))
    app.add_handler(CommandHandler("bantuan", cmd_bantuan))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))

    return app


async def run_bot_async() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        print("❌ TELEGRAM_BOT_TOKEN belum diatur di .env!")
        print("   Dapatkan token dari @BotFather di Telegram, lalu tambahkan ke .env:")
        print("   TELEGRAM_BOT_TOKEN=123456:ABC-DEF...")
        return

    # Inisialisasi DB jika belum ada
    await init_db()
    logger.info("Database SQLite siap.")

    app = build_bot_app(settings.telegram_bot_token)
    logger.info("Bot VisiBon mulai mendengarkan pesan (polling)...")

    # Inisialisasi dan jalankan polling
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    try:
        # Biarkan bot berjalan sampai dihentikan
        while True:
            await asyncio.sleep(1)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Menghentikan bot...")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


def start_bot() -> None:
    try:
        asyncio.run(run_bot_async())
    except KeyboardInterrupt:
        print("\nBot dihentikan.")
