from fastapi import FastAPI
from fastapi.responses import FileResponse
import os

app = FastAPI(title="Usanex AI")


@app.get("/")
async def home():
    return FileResponse("index.html")


@app.get("/health")
async def health():
    return {
        "ok": True,
        "status": "online",
        "app": "Usanex AI"
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
