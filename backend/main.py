from fastapi import FastAPI
from backend.routes import (
    auth_router,
    users_router,
)


app = FastAPI(
    title="Usanex",
)


# =========================================================
# ROUTERS
# =========================================================

app.include_router(auth_router)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
async def health():
    return {
        "ok": True,
        "app": "Usanex",
        "status": "online",
    }
