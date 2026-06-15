import httpx
import os
from typing import Dict, Any, List, Optional


class N8nClient:
    """Client for interacting with n8n API"""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or os.getenv("N8N_BASE_URL", "http://n8n:5678")
        self.api_key = api_key or os.getenv("N8N_API_KEY", "")
        self.headers = {"X-N8N-API-KEY": self.api_key} if self.api_key else {}
        # httpx's single ``timeout=60.0`` applies the same budget to
        # every phase (connect, read, write, pool). A half-open TCP
        # socket then waits the full 60s on connect before failing —
        # which holds a uvicorn worker through every n8n-down call.
        # connect=5 fails fast; read=30 covers n8n's slowest workflow
        # list endpoint.
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "N8nClient":
        return self

    async def __aexit__(self, *a) -> None:
        await self.aclose()

    async def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows.

        n8n's public API wraps the list in a ``{"data": [...],
        "nextCursor": ...}`` envelope — return the inner list (the raw
        dict failed the route's List[WorkflowResponse] validation).
        """
        response = await self._client.get(
            f"{self.base_url}/api/v1/workflows", headers=self.headers
        )
        response.raise_for_status()
        return response.json().get("data", [])

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get a workflow by ID"""
        response = await self._client.get(
            f"{self.base_url}/api/v1/workflows/{workflow_id}", headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    async def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """Get an execution by ID"""
        response = await self._client.get(
            f"{self.base_url}/api/v1/executions/{execution_id}",
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json()
