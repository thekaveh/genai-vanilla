import httpx
import os
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from pydantic import BaseModel
from enum import Enum


class ResearchStatus(str, Enum):
    """Research status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResearchRequest(BaseModel):
    """Request model for starting research"""
    query: str
    max_loops: int = 3
    search_api: str = "duckduckgo"
    user_id: Optional[str] = None


class ResearchResponse(BaseModel):
    """Response model for research operations"""
    session_id: str
    status: ResearchStatus
    message: str
    data: Optional[Dict[str, Any]] = None


class ResearchResult(BaseModel):
    """Model for completed research results"""
    session_id: str
    title: str
    summary: str
    content: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class ResearchClient:
    """Client for interacting with Local Deep Researcher service"""

    def __init__(self, base_url: Optional[str] = None, timeout: int = 300):
        self.base_url = base_url or os.getenv(
            "LOCAL_DEEP_RESEARCHER_URL", 
            "http://local-deep-researcher:2024"
        )
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check if the research service is healthy"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    return {"status": "healthy", "service": "local-deep-researcher"}
                else:
                    return {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
            except Exception as e:
                return {"status": "unhealthy", "error": str(e)}

    async def start_research(self, request: ResearchRequest) -> ResearchResponse:
        """Start a new research session"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Prepare payload for LangGraph API
                payload = {
                    "query": request.query,
                    "config": {
                        "max_loops": request.max_loops,
                        "search_api": request.search_api
                    },
                    "metadata": {
                        "user_id": request.user_id
                    }
                }

                response = await client.post(
                    f"{self.base_url}/research/start",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                
                data = response.json()
                return ResearchResponse(
                    session_id=data.get("session_id", ""),
                    status=ResearchStatus.RUNNING,
                    message="Research started successfully",
                    data=data
                )
            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
                return ResearchResponse(
                    session_id="",
                    status=ResearchStatus.FAILED,
                    message=f"Failed to start research: {error_msg}"
                )
            except Exception as e:
                return ResearchResponse(
                    session_id="",
                    status=ResearchStatus.FAILED,
                    message=f"Failed to start research: {str(e)}"
                )

    async def get_research_status(self, session_id: str) -> ResearchResponse:
        """Get the status of a research session"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/research/{session_id}/status",
                    headers=self.headers
                )
                response.raise_for_status()
                
                data = response.json()
                return ResearchResponse(
                    session_id=session_id,
                    status=ResearchStatus(data.get("status", "pending")),
                    message=data.get("message", ""),
                    data=data
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return ResearchResponse(
                        session_id=session_id,
                        status=ResearchStatus.FAILED,
                        message="Research session not found"
                    )
                error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
                return ResearchResponse(
                    session_id=session_id,
                    status=ResearchStatus.FAILED,
                    message=f"Failed to get status: {error_msg}"
                )
            except Exception as e:
                return ResearchResponse(
                    session_id=session_id,
                    status=ResearchStatus.FAILED,
                    message=f"Failed to get status: {str(e)}"
                )

    async def get_research_result(self, session_id: str) -> Optional[ResearchResult]:
        """Get the final result of a completed research session"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/research/{session_id}/result",
                    headers=self.headers
                )
                response.raise_for_status()
                
                data = response.json()
                return ResearchResult(
                    session_id=session_id,
                    title=data.get("title", "Research Result"),
                    summary=data.get("summary", ""),
                    content=data.get("content", ""),
                    sources=data.get("sources", []),
                    metadata=data.get("metadata", {})
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise Exception(f"HTTP {e.response.status_code}: {e.response.text}")
            except Exception as e:
                raise Exception(f"Failed to get result: {str(e)}")

    async def cancel_research(self, session_id: str) -> ResearchResponse:
        """Cancel a running research session"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/research/{session_id}/cancel",
                    headers=self.headers
                )
                response.raise_for_status()
                
                data = response.json()
                return ResearchResponse(
                    session_id=session_id,
                    status=ResearchStatus.CANCELLED,
                    message="Research cancelled successfully",
                    data=data
                )
            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
                return ResearchResponse(
                    session_id=session_id,
                    status=ResearchStatus.FAILED,
                    message=f"Failed to cancel research: {error_msg}"
                )
            except Exception as e:
                return ResearchResponse(
                    session_id=session_id,
                    status=ResearchStatus.FAILED,
                    message=f"Failed to cancel research: {str(e)}"
                )

    async def stream_research_logs(self, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream real-time logs from a research session"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "GET",
                    f"{self.base_url}/research/{session_id}/logs/stream",
                    headers=self.headers
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                import json
                                data = json.loads(line[6:])  # Remove "data: " prefix
                                yield data
                            except json.JSONDecodeError:
                                continue
                        elif line == "event: close":
                            break
            except Exception as e:
                yield {"error": f"Stream error: {str(e)}"}

    async def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all currently active research sessions"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/research/sessions/active",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise Exception(f"Failed to list active sessions: {str(e)}")

    async def wait_for_completion(
        self, 
        session_id: str, 
        poll_interval: int = 5, 
        max_wait_time: int = 300
    ) -> ResearchResponse:
        """Wait for a research session to complete with polling"""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            status_response = await self.get_research_status(session_id)
            
            if status_response.status in [
                ResearchStatus.COMPLETED, 
                ResearchStatus.FAILED, 
                ResearchStatus.CANCELLED
            ]:
                return status_response
            
            elapsed_time = asyncio.get_event_loop().time() - start_time
            if elapsed_time >= max_wait_time:
                return ResearchResponse(
                    session_id=session_id,
                    status=ResearchStatus.FAILED,
                    message=f"Timeout waiting for completion after {max_wait_time} seconds"
                )
            
            await asyncio.sleep(poll_interval)