"""Validasi aritmetika struk — penangkal halusinasi angka dari VLM."""

from __future__ import annotations

from pydantic import BaseModel, Field

from visibon.schemas import Receipt


class ValidationReport(BaseModel):
    is_valid: bool
    items_sum: int
    expected_total: int
    reported_total: int | None
    difference: int | None
    tax_inclusive: bool = False
    issues: list[str] = Field(default_factory=list)


def validate_receipt(receipt: Receipt, tolerance: int = 100) -> ValidationReport:
    """Cek konsistensi: Σ item − diskon + pajak + service ≈ total.

    Struk minimarket (Indomaret/Alfamart) biasanya PPN sudah *termasuk* harga,
    jadi total == Σ item − diskon juga dianggap valid (tax_inclusive=True).
    """
    issues: list[str] = []

    if not receipt.items:
        issues.append("Tidak ada item terbaca.")

    for i, item in enumerate(receipt.items, start=1):
        if item.unit_price is not None:
            expected = round(item.qty * item.unit_price)
            if abs(expected - item.subtotal) > tolerance:
                issues.append(
                    f"Item #{i} '{item.name}': {item.qty:g} x {item.unit_price} "
                    f"= {expected}, tapi subtotal tertulis {item.subtotal}."
                )

    items_sum = sum(item.subtotal for item in receipt.items)

    if receipt.subtotal is not None and abs(receipt.subtotal - items_sum) > tolerance:
        issues.append(f"Jumlah item {items_sum} ≠ subtotal tertulis {receipt.subtotal}.")

    base = receipt.subtotal if receipt.subtotal is not None else items_sum
    expected_total = base - receipt.discount + receipt.tax + receipt.service
    tax_inclusive = False
    difference: int | None = None

    if receipt.total is None:
        issues.append("Total tidak terbaca.")
    else:
        difference = receipt.total - expected_total
        if abs(difference) > tolerance:
            inclusive_total = base - receipt.discount + receipt.service
            if receipt.tax and abs(receipt.total - inclusive_total) <= tolerance:
                tax_inclusive = True
                difference = receipt.total - inclusive_total
            else:
                issues.append(
                    f"Total tertulis {receipt.total} ≠ hitungan {expected_total} "
                    f"(selisih {difference})."
                )

    return ValidationReport(
        is_valid=not issues,
        items_sum=items_sum,
        expected_total=expected_total,
        reported_total=receipt.total,
        difference=difference,
        tax_inclusive=tax_inclusive,
        issues=issues,
    )
