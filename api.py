#!/usr/bin/env python3
"""API server entry point for the Resume Job Matcher."""

import uvicorn

from src.api.app import app
from src.config import Config

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=Config.api_port(),
        log_level="info"
    )
