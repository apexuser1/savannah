"""API models for optimisation endpoints."""
from typing import Any, Dict, Optional

from pydantic import BaseModel


class OptimisationRequest(BaseModel):
    job_id: int
    optimisation: Dict[str, Any]
    candidate_count: Optional[int] = None
    top_k: Optional[int] = None
