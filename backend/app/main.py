from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from storage3 import SyncStorageClient as StorageClient
from typing import Optional, cast, Dict, Any, List
import os
import httpx

from n8n_client import N8nClient

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
