from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from storage3 import SyncStorageClient as StorageClient
from typing import Optional, cast, Dict, Any, List
import os
import httpx

from n8n_client import N8nClient
from research_service import ResearchService

app = FastAPI(
    title="GenAI Vanilla Stack Backend",
    description="Backend API for GenAI Vanilla Stack",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get environment variables
KONG_URL = os.getenv("KONG_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not KONG_URL:
    raise ValueError("KONG_URL environment variable is required")
if not SERVICE_KEY:
    raise ValueError("SUPABASE_SERVICE_KEY environment variable is required")

# Construct Supabase Storage URL via Kong
# The standard path for storage via the gateway is /storage/v1
storage_url = f"{KONG_URL}/storage/v1"

# Initialize Supabase Storage client
storage_client = StorageClient(
    url=storage_url,
    headers={
        "Authorization": f"Bearer {SERVICE_KEY}",
        "apikey": SERVICE_KEY,  # Supabase storage requires the service key as apikey header
    },
)


class HealthResponse(BaseModel):
    status: str
    version: str


class StorageResponse(BaseModel):
    bucket: str
    path: str
    url: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for the API"""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
    )


@app.get("/")
async def root():
    """Root endpoint that returns a welcome message"""
    return {
        "message": "Welcome to the GenAI Vanilla Stack Backend API",
        "docs_url": "/docs",
    }


# Initialize n8n client
n8n_client = N8nClient()

# Initialize research service
research_service = ResearchService()


class WorkflowExecuteRequest(BaseModel):
    """Request model for executing a workflow"""

    data: Optional[Dict[str, Any]] = None


class WorkflowResponse(BaseModel):
    """Response model for workflow operations"""

    id: str
    name: str
    active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WorkflowExecutionResponse(BaseModel):
    """Response model for workflow execution"""

    id: str
    finished: bool
    mode: str
    status: str
    started_at: str
    workflow_id: str
    data: Optional[Dict[str, Any]] = None


@app.get("/workflows", response_model=List[WorkflowResponse])
async def list_workflows():
    """List all n8n workflows"""
    try:
        workflows = await n8n_client.list_workflows()
        return workflows
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflows: {str(e)}",
        )


@app.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str):
    """Get a specific n8n workflow by ID"""
    try:
        workflow = await n8n_client.get_workflow(workflow_id)
        return workflow
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow: {str(e)}",
        )


@app.post("/workflows/{workflow_id}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(workflow_id: str, request: WorkflowExecuteRequest):
    """Execute a specific n8n workflow by ID"""
    try:
        execution = await n8n_client.execute_workflow(workflow_id, request.data)
        return execution
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute workflow: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute workflow: {str(e)}",
        )


@app.post("/storage/upload", response_model=StorageResponse)
async def upload_file(file: UploadFile = File(...), bucket: str = "default"):
    """Upload a file to Supabase Storage"""
    try:
        # Ensure filename exists and cast to str to satisfy type checker
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must have a filename",
            )
        filename = cast(str, file.filename)

        # Read file content
        content = await file.read()

        # Upload to storage
        result = storage_client.upload(
            bucket=bucket,
            path=filename,
            file=content,
            file_options={"content-type": file.content_type}
            if file.content_type
            else None,
        )

        # Get public URL
        url = storage_client.get_public_url(bucket, filename)

        return StorageResponse(bucket=bucket, path=filename, url=url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Research API Models
class ResearchStartRequest(BaseModel):
    """Request model for starting research"""
    query: str
    max_loops: Optional[int] = 3
    search_api: Optional[str] = "duckduckgo"
    user_id: Optional[str] = None


class ResearchResponse(BaseModel):
    """Response model for research operations"""
    session_id: str
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


class ResearchSessionResponse(BaseModel):
    """Response model for research session details"""
    session_id: str
    query: str
    status: str
    max_loops: int
    search_api: str
    user_id: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class ResearchResultResponse(BaseModel):
    """Response model for research results"""
    session_id: str
    result_id: str
    title: str
    summary: str
    content: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: str
    status: str


class ResearchLogResponse(BaseModel):
    """Response model for research logs"""
    step_number: int
    step_type: str
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str


# Research API Endpoints
@app.post("/research/start", response_model=ResearchResponse)
async def start_research(request: ResearchStartRequest):
    """Start a new research session"""
    try:
        result = await research_service.start_research(
            query=request.query,
            max_loops=request.max_loops or 3,
            search_api=request.search_api or "duckduckgo",
            user_id=request.user_id
        )
        return ResearchResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start research: {str(e)}"
        )


@app.get("/research/{session_id}/status", response_model=ResearchSessionResponse)
async def get_research_status(session_id: str):
    """Get the status of a research session"""
    try:
        result = await research_service.get_research_status(session_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Research session {session_id} not found"
            )
        return ResearchSessionResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get research status: {str(e)}"
        )


@app.get("/research/{session_id}/result", response_model=ResearchResultResponse)
async def get_research_result(session_id: str):
    """Get the result of a completed research session"""
    try:
        result = await research_service.get_research_result(session_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Research result for session {session_id} not found"
            )
        return ResearchResultResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get research result: {str(e)}"
        )


@app.post("/research/{session_id}/cancel", response_model=ResearchResponse)
async def cancel_research(session_id: str):
    """Cancel a running research session"""
    try:
        success = await research_service.cancel_research(session_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel research session {session_id} - session not found or not running"
            )
        return ResearchResponse(
            session_id=session_id,
            status="cancelled",
            message="Research session cancelled successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel research: {str(e)}"
        )


@app.get("/research/{session_id}/logs", response_model=List[ResearchLogResponse])
async def get_research_logs(session_id: str):
    """Get logs for a research session"""
    try:
        logs = await research_service.get_research_logs(session_id)
        return [ResearchLogResponse(**log) for log in logs]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get research logs: {str(e)}"
        )


@app.get("/research/sessions", response_model=List[ResearchSessionResponse])
async def list_research_sessions(
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List research sessions"""
    try:
        sessions = await research_service.list_user_sessions(
            user_id=user_id,
            limit=min(limit, 100),  # Cap at 100
            offset=max(offset, 0)   # Ensure non-negative
        )
        return [ResearchSessionResponse(**session) for session in sessions]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list research sessions: {str(e)}"
        )


@app.get("/research/health")
async def research_health_check():
    """Health check for research service"""
    try:
        health = await research_service.health_check()
        return {
            "service": "research",
            "status": "healthy" if health["database"] == "healthy" else "degraded",
            "details": health
        }
    except Exception as e:
        return {
            "service": "research", 
            "status": "unhealthy",
            "error": str(e)
        }
