"""
Configuration settings for the Production Platform API service.
"""

import os
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Self-Healing & Auto-Scaling Production API"
    environment: str = os.getenv("ENV", "production")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    pod_name: str = os.getenv("POD_NAME", os.getenv("HOSTNAME", "pod-default"))
    node_name: str = os.getenv("NODE_NAME", "node-default")
    version: str = os.getenv("APP_VERSION", "1.0.0")
    
    # Chaos / Testing Settings
    enable_chaos_endpoints: bool = os.getenv("ENABLE_CHAOS", "true").lower() == "true"
    base_cpu_work_cycles: int = int(os.getenv("BASE_CPU_WORK_CYCLES", "150000"))


settings = Settings()
