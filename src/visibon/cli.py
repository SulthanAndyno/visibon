"""CLI VisiBon.

visibon doctor                       # cek Ollama/Gemini siap
visibon preprocess struk.jpg -o out/ # lihat hasil preprocessing
visibon scan struk.jpg               # ekstraksi penuh
visibon scan struk.jpg -e gemini --debug out/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
from rich.console import Console
from rich.table import Table

from visibon.config import get_settings
from visibon.extractors import ExtractionError, get_extractor
from visibon.money import format_rupiah
from visibon.pipeline import scan
from visibon.preprocess import load_image, preprocess

console = Console()


def cmd_doctor(_: argparse.Namespace) -> int:
    settings = get_settings()
    console.print(f"[bold]Extractor default:[/] {settings.extractor}")
    all_ok = True
    for name in ("ollama", "gemini"):
        ok, msg = get_extractor(name, settings).health()
        all_ok &= ok or name != settings.extractor
        console.print(f"  {'✅' if ok else '❌'} {name}: {msg}")

    tg_ok = bool(settings.telegram_bot_token)
    console.print(
        f"  {'✅' if tg_ok else '⚠️ '} telegram: "
        f"{'Token siap' if tg_ok else 'TELEGRAM_BOT_TOKEN belum di-set di .env (opsional untuk bot)'}"
    )
    console.print(f"  ✅ database: SQLite ({settings.database_path})")
    return 0 if all_ok else 1


def cmd_preprocess(args: argparse.Namespace) -> int:
    settings = get_settings()
    result = preprocess(load_image(args.image), settings.max_image_side, keep_debug=True)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, img in result.debug.items():
        cv2.imwrite(str(out_dir / f"{name}.jpg"), img)
    console.print(
        f"blur_score={result.blur_score:.1f} ({'BURAM ⚠️' if result.is_blurry else 'tajam ✅'}), "
        f"warped={result.warped} -> disimpan di {out_dir}/"
    )
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    settings = get_settings()
    try:
        result = scan(
            load_image(args.image),
            extractor=get_extractor(args.extractor, settings),
            settings=settings,
            debug_dir=Path(args.debug) if args.debug else None,
        )
    except (ExtractionError, ValueError) as exc:
        console.print(f"[red]Gagal:[/] {exc}")
        return 1

    if args.json:
        print(result.model_dump_json(indent=2))
        return 0

    r = result.receipt
    table = Table(title=f"🧾 {r.merchant or '?'} — {r.date or '?'} {r.time or ''}")
    table.add_column("Item")
    table.add_column("Qty", justify="right")
    table.add_column("Harga", justify="right")
    table.add_column("Subtotal", justify="right")
    for item in r.items:
        price = format_rupiah(item.unit_price) if item.unit_price is not None else "-"
        table.add_row(item.name, f"{item.qty:g}", price, format_rupiah(item.subtotal))
    console.print(table)
    for label, value in (("Diskon", r.discount), ("Pajak", r.tax), ("Service", r.service)):
        if value:
            console.print(f"  {label:<8}: {format_rupiah(value)}")
    total = format_rupiah(r.total) if r.total is not None else "?"
    console.print(f"  [bold]TOTAL   : {total}[/]  ({r.payment_method or '-'}, {r.category or '-'})")

    v = result.validation
    if v.is_valid:
        console.print("[green]✅ Validasi aritmetika lolos[/]")
    else:
        console.print("[yellow]⚠️  Perlu dicek:[/]")
        for issue in v.issues:
            console.print(f"   - {issue}")
    if result.is_blurry:
        console.print(f"[yellow]⚠️  Foto agak buram (score {result.blur_score}).[/]")
    console.print(f"[dim]{result.extractor}/{result.model} · {result.latency_ms:.0f} ms[/]")
    return 0


def cmd_bot(_: argparse.Namespace) -> int:
    from visibon.bot.app import start_bot

    start_bot()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="visibon", description="Scan struk jadi data.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Cek kesiapan extractor").set_defaults(func=cmd_doctor)
    sub.add_parser("bot", help="Jalankan Telegram Bot").set_defaults(func=cmd_bot)

    p = sub.add_parser("preprocess", help="Simpan hasil preprocessing untuk dicek")
    p.add_argument("image")
    p.add_argument("-o", "--output", default="outputs/preprocess")
    p.set_defaults(func=cmd_preprocess)

    s = sub.add_parser("scan", help="Ekstraksi struk")
    s.add_argument("image")
    s.add_argument("-e", "--extractor", choices=["ollama", "gemini"], default=None)
    s.add_argument("--debug", help="Folder untuk menyimpan gambar debug")
    s.add_argument("--json", action="store_true", help="Output JSON mentah")
    s.set_defaults(func=cmd_scan)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
