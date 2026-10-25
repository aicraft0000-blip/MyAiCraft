from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import actions, auth, briefs, digests, public, qa, webhook
from app import scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pipeline crons run inside this service when RUN_SCHEDULER=1 (Railway).
    tasks = scheduler.start()
    yield
    for t in tasks or []:
        t.cancel()


app = FastAPI(title="RadarWindow API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,    prefix="/auth",    tags=["auth"])
app.include_router(briefs.router,  prefix="/briefs",  tags=["briefs"])
app.include_router(digests.router, prefix="/digests", tags=["digests"])
app.include_router(public.router,  prefix="/public",  tags=["public"])
app.include_router(webhook.router,                    tags=["webhook"])
app.include_router(actions.router, prefix="/actions", tags=["actions"])
app.include_router(qa.router,      prefix="/qa",      tags=["qa"])


@app.get("/health")
def health():
    return {"status": "ok"}
