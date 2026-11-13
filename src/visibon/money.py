"""Parsing angka rupiah ala struk Indonesia.

Contoh yang ditangani:
    "Rp 12.500"   -> 12500
    "12,500"      -> 12500
    "12.500,00"   -> 12500
    "-2.000"      -> -2000
    "(2.000)"     -> -2000
    "IDR 1.250.000" -> 1250000
"""

from __future__ import annotations

import re

_CENTS = re.compile(r"^(?P<body>.*?)[.,](?P<cents>\d{2})$")


def parse_rupiah(value: object) -> int | None:
    """Ubah teks/angka rupiah jadi integer. Return None kalau tidak ada digit."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError("bool bukan nilai uang")
    if isinstance(value, int):
        # Di struk Indonesia, hampir tidak ada barang berharga < 100 rupiah.
        # Jika model mengembalikan integer kecil (misal 21 dari 21.000), anggap ribuan.
        return value * 1000 if 0 < value < 100 else value
    if isinstance(value, float):
        # Format "10.500" sering ter-parse jadi float 10.5 oleh JSON parser.
        # Konversi 10.5 -> 10500 rupiah.
        if 0 < value < 1000:
            return round(value * 1000)
        return round(value)

    raw = str(value).strip()
    negative = raw.startswith("-") or (raw.startswith("(") and raw.endswith(")"))
    cleaned = re.sub(r"[^\d.,]", "", raw)
    if not re.search(r"\d", cleaned):
        return None

    # Buang sen: "12.500,00" / "12,500.00" / "500,00". Rupiah praktis tanpa sen.
    m = _CENTS.match(cleaned)
    if m and (m.group("cents") == "00" or re.search(r"[.,]", m.group("body"))):
        cleaned = m.group("body")

    digits = re.sub(r"\D", "", cleaned)
    if not digits:
        return None
    amount = int(digits)
    return -amount if negative else amount


def format_rupiah(amount: int) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}Rp {abs(amount):,}".replace(",", ".")
