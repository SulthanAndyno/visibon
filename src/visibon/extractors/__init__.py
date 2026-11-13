from visibon.config import Settings, get_settings
from visibon.extractors.base import ExtractionError, ExtractionResult, Extractor


def get_extractor(name: str | None = None, settings: Settings | None = None) -> Extractor:
    settings = settings or get_settings()
    name = (name or settings.extractor).lower()

    if name == "ollama":
        from visibon.extractors.ollama_vlm import OllamaVLMExtractor

        return OllamaVLMExtractor(
            settings.ollama_base_url, settings.ollama_model, settings.ollama_timeout
        )
    if name == "gemini":
        from visibon.extractors.gemini_vlm import GeminiVLMExtractor

        return GeminiVLMExtractor(settings.gemini_api_key, settings.gemini_model)

    raise ValueError(f"Extractor tidak dikenal: {name!r} (pilihan: ollama, gemini)")


__all__ = ["ExtractionError", "ExtractionResult", "Extractor", "get_extractor"]
