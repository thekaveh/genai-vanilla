import httpx
import os
from typing import Dict, Any, List, Optional


class N8nClient:
    """Client for interacting with n8n API"""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or os.getenv("N8N_BASE_URL", "http://n8n:5678")
        self.api_key = api_key or os.getenv("N8N_API_KEY", "")
        self.headers = {"X-N8N-API-KEY": self.api_key} if self.api_key else {}

    async def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/workflows", headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def execute_workflow(
        self, workflow_id: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a workflow by ID"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/workflows/{workflow_id}/execute",
                headers=self.headers,
                json=data or {},
            )
            response.raise_for_status()
            return response.json()

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get a workflow by ID"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/workflows/{workflow_id}", headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """Get an execution by ID"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/executions/{execution_id}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
