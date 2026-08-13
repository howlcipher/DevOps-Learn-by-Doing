# Reference pattern for environment-variable configuration, shown by hints in
# module_01_understand_workload. Mirrors projects/api_platform/app/config.py.

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    service_name: str
    port: int


def get_settings() -> Settings:
    # os.environ.get(name, default) never raises if the variable is unset,
    # which is why every setting here has an explicit default.
    return Settings(
        service_name=os.environ.get("SERVICE_NAME", "api-platform"),
        port=int(os.environ.get("PORT", "8000")),
    )
