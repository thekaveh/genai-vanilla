"""FastAPI router for /api/ray/* — wraps the RayClient.

When Ray is disabled (RAY_ADDRESS empty), every endpoint returns 503
with a clear error message rather than 500.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .ray_client import RayClient, RayDisabledError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ray", tags=["ray"])


class SubmitJobRequest(BaseModel):
    """Request model for submitting a Ray job."""
    entrypoint: str = Field(..., description="Shell command to run on the Ray cluster.")
    runtime_env: Optional[dict[str, Any]] = Field(
        default=None,
        description="Ray runtime_env dict (working_dir, pip, env_vars).",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Arbitrary metadata attached to the job.",
    )


class SubmitJobResponse(BaseModel):
    """Response model for job submission."""
    job_id: str


@router.post("/jobs/submit", response_model=SubmitJobResponse)
async def submit_job(payload: SubmitJobRequest) -> SubmitJobResponse:
    """Submit a job to the Ray cluster."""
    try:
        client = RayClient.get()
        job_id = client.submit_job(
            entrypoint=payload.entrypoint,
            runtime_env=payload.runtime_env,
            metadata=payload.metadata,
        )
        return SubmitJobResponse(job_id=job_id)
    except RayDisabledError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("ray submit_job failed")
        raise HTTPException(status_code=500, detail="Ray job submission failed")


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> dict:
    """Get the status of a Ray job."""
    try:
        return RayClient.get().get_job_status(job_id)
    except RayDisabledError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("ray get_job_status failed")
        raise HTTPException(status_code=500, detail="Ray job status fetch failed")


@router.delete("/jobs/{job_id}")
async def stop_job(job_id: str) -> dict:
    """Stop a running Ray job."""
    try:
        stopped = RayClient.get().stop_job(job_id)
        return {"stopped": stopped}
    except RayDisabledError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("ray stop_job failed")
        raise HTTPException(status_code=500, detail="Ray job stop failed")


@router.get("/cluster/status")
async def cluster_status() -> dict:
    """Get Ray cluster status from the dashboard API."""
    try:
        return RayClient.get().cluster_status()
    except RayDisabledError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("ray cluster_status failed")
        raise HTTPException(status_code=500, detail="Ray cluster status fetch failed")
