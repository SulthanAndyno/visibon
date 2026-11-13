from visibon.schemas import Receipt
from visibon.validator import validate_receipt


def _receipt(**kwargs) -> Receipt:
    base = {
        "merchant": "Kopi Kita",
        "items": [
            {"name": "Es Kopi Susu", "qty": 2, "unit_price": "18.000", "subtotal": "36.000"},
            {"name": "Croissant", "qty": 1, "unit_price": 22000, "subtotal": 22000},
        ],
    }
    base.update(kwargs)
    return Receipt.model_validate(base)


def test_valid_with_tax_and_service():
    r = _receipt(tax="5.800", service="2.900", total="66.700")
    report = validate_receipt(r)
    assert report.is_valid, report.issues
    assert report.items_sum == 58000


def test_tax_inclusive_minimarket():
    r = _receipt(tax=5748, total=58000)
    report = validate_receipt(r)
    assert report.is_valid
    assert report.tax_inclusive


def test_wrong_total_flagged():
    report = validate_receipt(_receipt(total=99000))
    assert not report.is_valid
    assert any("Total" in issue for issue in report.issues)


def test_wrong_item_math_flagged():
    r = Receipt.model_validate(
        {
            "items": [{"name": "Teh", "qty": 3, "unit_price": 5000, "subtotal": 10000}],
            "total": 10000,
        }
    )
    report = validate_receipt(r)
    assert not report.is_valid
    assert any("Teh" in issue for issue in report.issues)


def test_missing_total():
    report = validate_receipt(_receipt())
    assert not report.is_valid


def test_category_normalized():
    assert _receipt(category="makanan & minuman").category == "Makanan & Minuman"
    assert _receipt(category="Random").category == "Lainnya"
