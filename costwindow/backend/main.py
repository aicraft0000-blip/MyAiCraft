from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, ingest, processes, summary, manual, subscriptions, estimate, proxy
from app.routers.provider_balances import router as balances_router
from app.routers.webhook import router as webhook_router

settings = get_settings()

# Interactive API docs are useful in dev but expose the full API surface to
# anyone in prod — disable them unless COSTWINDOW_ENABLE_DOCS is set.
_docs = "/docs" if settings.enable_docs else None
_redoc = "/redoc" if settings.enable_docs else None
_openapi = "/openapi.json" if settings.enable_docs else None

app = FastAPI(
    title="CostWindow API", version="1.0.0",
    docs_url=_docs, redoc_url=_redoc, openapi_url=_openapi,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "https://costwindow.pages.dev",
        "https://costwindow.com",
        "https://www.costwindow.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,          prefix="/auth",              tags=["auth"])
app.include_router(ingest.router,                                     tags=["ingest"])
app.include_router(processes.router,                                  tags=["processes"])
app.include_router(summary.router,                                    tags=["summary"])
app.include_router(manual.router,                                     tags=["manual"])
app.include_router(subscriptions.router, prefix="/subscriptions",     tags=["subscriptions"])
app.include_router(balances_router,                                   tags=["provider-balances"])
app.include_router(estimate.router,                                    tags=["estimate"])
app.include_router(webhook_router,                                    tags=["webhook"])
app.include_router(proxy.router,                                      tags=["proxy"])


@app.get("/health")
def health():
    return {"status": "ok"}
