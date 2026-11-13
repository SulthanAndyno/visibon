import pytest

from visibon.money import format_rupiah, parse_rupiah


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Rp 12.500", 12500),
        ("12,500", 12500),
        ("12.500,00", 12500),
        ("IDR 1.250.000", 1250000),
        ("-2.000", -2000),
        ("(2.000)", -2000),
        ("500,00", 500),
        ("Rp5000", 5000),
        (12500, 12500),
        (12500.0, 12500),
        (10.5, 10500),
        (4.0, 4000),
        ("", None),
        ("abc", None),
        (None, None),
    ],
)
def test_parse_rupiah(raw, expected):
    assert parse_rupiah(raw) == expected


def test_format_rupiah():
    assert format_rupiah(1250000) == "Rp 1.250.000"
    assert format_rupiah(-500) == "-Rp 500"
