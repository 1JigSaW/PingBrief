from fastapi import FastAPI
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import structlog

from .config import get_settings
from .logging_config import configure_logging
from .api.v1.routers import routers
from .admin import init_app

configure_logging()
log = structlog.get_logger()
settings = get_settings()

app = FastAPI(
    title="PingBrief",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_hosts,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ],
)

log.info("app_startup", msg="Starting application", host="0.0.0.0", port=8000)

for router in routers:
    app.include_router(router, prefix=settings.api_v1_str)

@app.get("/health", tags=["health"])
def health():
    log.info("health_check", status="ok")
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    await init_app(app)
