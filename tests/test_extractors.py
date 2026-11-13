import numpy as np
import pytest

from visibon.config import Settings
from visibon.extractors import ExtractionError, get_extractor
from visibon.extractors.base import ExtractionResult, Extractor, parse_json_output
from visibon.pipeline import scan
from visibon.schemas import Receipt


def test_parse_json_with_fences():
    text = 'Berikut hasilnya:\n```json\n{"merchant": "Alfamart", "total": 15000}\n```'
    assert parse_json_output(text) == {"merchant": "Alfamart", "total": 15000}


def test_parse_json_invalid():
    with pytest.raises(ExtractionError):
        parse_json_output("maaf saya tidak bisa membaca struk ini")


def test_factory():
    s = Settings(_env_file=None)
    assert get_extractor("ollama", s).name == "ollama"
    assert get_extractor("gemini", s).name == "gemini"
    with pytest.raises(ValueError):
        get_extractor("tesseract", s)


class FakeExtractor(Extractor):
    name = "fake"

    def extract(self, image: np.ndarray) -> ExtractionResult:
        receipt = Receipt.model_validate(
            {
                "merchant": "Warung Bu Siti",
                "items": [{"name": "Nasi Rames", "qty": 1, "unit_price": 15000, "subtotal": 15000}],
                "total": "15.000",
            }
        )
        return ExtractionResult(receipt, self.name, "fake-1", 1.0, "{}")


def test_pipeline_with_fake_extractor():
    from make_synthetic_receipt import make_receipt

    result = scan(make_receipt(), extractor=FakeExtractor(), settings=Settings(_env_file=None))
    assert result.validation.is_valid
    assert result.warped
    assert result.receipt.total == 15000
