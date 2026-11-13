"""Skema data struk. Semua nilai uang disimpan sebagai integer rupiah."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from visibon.money import parse_rupiah

CATEGORIES = [
    "Makanan & Minuman",
    "Kebutuhan Harian",
    "Transportasi",
    "Belanja",
    "Kesehatan",
    "Hiburan",
    "Tagihan",
    "Lainnya",
]


class ReceiptItem(BaseModel):
    name: str
    qty: float = 1
    unit_price: int | None = None
    subtotal: int

    @field_validator("unit_price", "subtotal", mode="before")
    @classmethod
    def _money(cls, v: object) -> int | None:
        return parse_rupiah(v)

    @field_validator("qty", mode="before")
    @classmethod
    def _qty(cls, v: object) -> float:
        if v in (None, ""):
            return 1
        if isinstance(v, str):
            v = v.lower().replace("x", "").replace(",", ".").strip() or "1"
        return float(v)


class Receipt(BaseModel):
    merchant: str | None = None
    date: str | None = Field(default=None, description="Format YYYY-MM-DD")
    time: str | None = Field(default=None, description="Format HH:MM")
    items: list[ReceiptItem] = Field(default_factory=list)
    subtotal: int | None = None
    discount: int = 0
    tax: int = 0
    service: int = 0
    total: int | None = None
    payment_method: str | None = None
    category: str | None = None

    @field_validator("subtotal", "total", mode="before")
    @classmethod
    def _money_opt(cls, v: object) -> int | None:
        return parse_rupiah(v)

    @field_validator("discount", "tax", "service", mode="before")
    @classmethod
    def _money_zero(cls, v: object) -> int:
        amount = parse_rupiah(v)
        return abs(amount) if amount is not None else 0

    @field_validator("category", mode="before")
    @classmethod
    def _category(cls, v: object) -> str | None:
        if not v:
            return None
        text = str(v).strip()
        for cat in CATEGORIES:
            if cat.lower() == text.lower():
                return cat
        return "Lainnya"


def receipt_json_schema() -> dict:
    """JSON schema yang dikirim ke VLM (structured output)."""
    return Receipt.model_json_schema()
