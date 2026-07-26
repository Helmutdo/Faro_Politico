from fastapi import FastAPI

app = FastAPI(
    title="Trama Pública API",
    description="API de transparencia basada en datos oficiales verificables.",
    version="0.1.0",
)


@app.get("/health", tags=["operational"])
def health() -> dict[str, str]:
    """Confirm that the API process is available."""
    return {"status": "ok"}
