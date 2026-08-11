"""Environment-variable configuration. No secrets belong in /info's output."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    service_name: str
    service_version: str
    environment: str
    port: int
    weather_api_key: str | None


def get_settings() -> Settings:
    return Settings(
        service_name=os.environ.get("SERVICE_NAME", "api-platform"),
        service_version=os.environ.get("SERVICE_VERSION", "0.1.0"),
        environment=os.environ.get("ENVIRONMENT", "development"),
        port=int(os.environ.get("PORT", "8000")),
        # Example external API credential. Never logged or returned by any endpoint;
        # exists so the DevOps platform has one real secret to detect and recommend
        # managed storage for.
        weather_api_key=os.environ.get("WEATHER_API_KEY"),
    )
