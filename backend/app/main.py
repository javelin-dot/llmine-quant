"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import handle_generic_exception, handle_llmine_exception, LLMineException
from app.core.logging import configure_logging, get_logger
from app.core.tracing import tracing_middleware
from app.api.v1.router import api_router
from app.api.v1.ws import router as ws_router

configure_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("startup", app_name=settings.app_name, version=settings.app_version, env=settings.env)
    yield
    logger.info("shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.middleware("http")(tracing_middleware)

# Exception handlers
app.add_exception_handler(LLMineException, handle_llmine_exception)
app.add_exception_handler(Exception, handle_generic_exception)

# Routes
app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(ws_router, prefix="/ws")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": settings.app_version}
