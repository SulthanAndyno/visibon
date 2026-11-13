"""REST API minimal. Jalankan: uv run uvicorn visibon.api:app --reload"""

from typing import Annotated

from fastapi import FastAPI, File, HTTPException, Query, UploadFile

from visibon import __version__
from visibon.config import get_settings
from visibon.extractors import ExtractionError, get_extractor
from visibon.pipeline import ScanResult, scan
from visibon.preprocess import load_image

app = FastAPI(title="VisiBon API", version=__version__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    ok, msg = get_extractor(settings=settings).health()
    return {"status": "ok" if ok else "degraded", "extractor": settings.extractor, "detail": msg}


@app.post("/extract", response_model=ScanResult)
def extract(  # sync def -> FastAPI jalankan di threadpool, inference tidak memblok event loop
    file: Annotated[UploadFile, File()],
    extractor: Annotated[str | None, Query(pattern="^(ollama|gemini)$")] = None,
) -> ScanResult:
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Ukuran gambar maksimal 10 MB.")
    try:
        image = load_image(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    try:
        return scan(image, extractor=get_extractor(extractor))
    except ExtractionError as exc:
        raise HTTPException(502, str(exc)) from exc
