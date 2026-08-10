"""The demo workload the curriculum teaches against. Deliberately small.

This exists to teach DevOps, not to be a large application-development
project: two endpoints, environment-variable configuration, structured logs.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from app.config import get_settings
from app.logging_config import configure_logging

configure_logging()
logger = logging.getLogger("api_platform")

settings = get_settings()
app = FastAPI(title=settings.service_name, version=settings.service_version)


@app.get("/health")
def health() -> dict[str, str]:
    logger.info("health check requested")
    return {"status": "ok"}


@app.get("/info")
def info() -> dict[str, str]:
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "environment": settings.environment,
    }
