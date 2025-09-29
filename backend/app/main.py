from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from storage3 import SyncStorageClient as StorageClient
from typing import Optional, cast, Dict, Any, List
import os
import httpx

from n8n_client import N8nClient
from research_service import ResearchService
from comfyui_client import ComfyUIClient

# Get project name from environment
PROJECT_NAME = os.getenv("PROJECT_NAME", "GenAI Vanilla Stack")

app = FastAPI(
    title=f"{PROJECT_NAME} Backend",
    description=f"Backend API for {PROJECT_NAME}",
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
        "message": f"Welcome to the {PROJECT_NAME} Backend API",
        "docs_url": "/docs",
    }


# Initialize n8n client
n8n_client = N8nClient()

# Initialize research service
research_service = ResearchService()

# Initialize ComfyUI client
comfyui_client = ComfyUIClient()


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


# ComfyUI API Models
class ComfyUIGenerateRequest(BaseModel):
    """Request model for ComfyUI image generation"""
    prompt: str
    negative_prompt: Optional[str] = ""
    width: int = 512
    height: int = 512
    steps: int = 20
    cfg: float = 7.0
    seed: Optional[int] = None
    checkpoint: Optional[str] = "sd_v1-5_pruned_emaonly.safetensors"
    wait_for_completion: bool = True


class ComfyUIWorkflowRequest(BaseModel):
    """Request model for custom ComfyUI workflow"""
    workflow: Dict[str, Any]
    wait_for_completion: bool = True


class ComfyUIResponse(BaseModel):
    """Response model for ComfyUI operations"""
    success: bool
    prompt_id: Optional[str] = None
    client_id: Optional[str] = None
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ComfyUI API Endpoints
@app.get("/comfyui/health")
async def comfyui_health_check():
    """Health check for ComfyUI service"""
    try:
        async with ComfyUIClient() as client:
            health = await client.health_check()
            return {
                "service": "comfyui",
                "status": health.get("status", "unknown"),
                "details": health
            }
    except Exception as e:
        return {
            "service": "comfyui",
            "status": "unhealthy", 
            "error": str(e)
        }


@app.get("/comfyui/models")
async def get_comfyui_models():
    """Get available ComfyUI models"""
    try:
        async with ComfyUIClient() as client:
            models = await client.get_models()
            return {
                "success": True,
                "models": models
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ComfyUI models: {str(e)}"
        )


@app.post("/comfyui/generate", response_model=ComfyUIResponse)
async def generate_image(request: ComfyUIGenerateRequest):
    """Generate an image using ComfyUI"""
    try:
        async with ComfyUIClient() as client:
            # Generate the image
            result = await client.generate_simple_image(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                width=request.width,
                height=request.height,
                steps=request.steps,
                cfg=request.cfg,
                seed=request.seed,
                checkpoint=request.checkpoint
            )
            
            if not result.get("success"):
                return ComfyUIResponse(
                    success=False,
                    error=result.get("error", "Unknown error")
                )
            
            prompt_id = result["prompt_id"]
            
            # If wait_for_completion is True, wait for the image to be generated
            if request.wait_for_completion:
                completion_result = await client.wait_for_completion(prompt_id)
                
                if completion_result.get("success"):
                    return ComfyUIResponse(
                        success=True,
                        prompt_id=prompt_id,
                        client_id=result["client_id"],
                        message="Image generated successfully",
                        data={
                            "outputs": completion_result["outputs"],
                            "parameters": result["parameters"]
                        }
                    )
                else:
                    return ComfyUIResponse(
                        success=False,
                        prompt_id=prompt_id,
                        error=completion_result.get("error", "Generation failed")
                    )
            else:
                # Return immediately with prompt ID
                return ComfyUIResponse(
                    success=True,
                    prompt_id=prompt_id,
                    client_id=result["client_id"],
                    message="Image generation queued",
                    data={"parameters": result["parameters"]}
                )
                
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate image: {str(e)}"
        )


@app.post("/comfyui/workflow", response_model=ComfyUIResponse)
async def execute_workflow(request: ComfyUIWorkflowRequest):
    """Execute a custom ComfyUI workflow"""
    try:
        async with ComfyUIClient() as client:
            # Queue the workflow
            result = await client.queue_prompt(request.workflow)
            
            if not result.get("success"):
                return ComfyUIResponse(
                    success=False,
                    error=result.get("error", "Unknown error")
                )
            
            prompt_id = result["prompt_id"]
            
            # If wait_for_completion is True, wait for the workflow to complete
            if request.wait_for_completion:
                completion_result = await client.wait_for_completion(prompt_id)
                
                if completion_result.get("success"):
                    return ComfyUIResponse(
                        success=True,
                        prompt_id=prompt_id,
                        client_id=result["client_id"],
                        message="Workflow executed successfully",
                        data={"outputs": completion_result["outputs"]}
                    )
                else:
                    return ComfyUIResponse(
                        success=False,
                        prompt_id=prompt_id,
                        error=completion_result.get("error", "Workflow execution failed")
                    )
            else:
                # Return immediately with prompt ID
                return ComfyUIResponse(
                    success=True,
                    prompt_id=prompt_id,
                    client_id=result["client_id"],
                    message="Workflow queued"
                )
                
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute workflow: {str(e)}"
        )


@app.get("/comfyui/history/{prompt_id}")
async def get_generation_history(prompt_id: str):
    """Get ComfyUI generation history for a specific prompt"""
    try:
        async with ComfyUIClient() as client:
            history = await client.get_history(prompt_id)
            return {
                "success": True,
                "history": history
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get history: {str(e)}"
        )


@app.get("/comfyui/queue")
async def get_queue_status():
    """Get ComfyUI queue status"""
    try:
        async with ComfyUIClient() as client:
            queue = await client.get_queue_status()
            return {
                "success": True,
                "queue": queue
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue status: {str(e)}"
        )


@app.post("/comfyui/cancel/{prompt_id}")
async def cancel_generation(prompt_id: str):
    """Cancel a ComfyUI generation"""
    try:
        async with ComfyUIClient() as client:
            success = await client.cancel_prompt(prompt_id)
            return {
                "success": success,
                "message": "Generation cancelled" if success else "Failed to cancel generation"
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel generation: {str(e)}"
        )


@app.get("/comfyui/image/{filename}")
async def get_generated_image(filename: str, subfolder: str = "", folder_type: str = "output"):
    """Get a generated image from ComfyUI"""
    try:
        async with ComfyUIClient() as client:
            image_data = await client.get_image_data(filename, subfolder, folder_type)
            
            # Determine content type based on file extension
            content_type = "image/png"
            if filename.lower().endswith(('.jpg', '.jpeg')):
                content_type = "image/jpeg"
            elif filename.lower().endswith('.webp'):
                content_type = "image/webp"
            
            from fastapi.responses import Response
            return Response(
                content=image_data,
                media_type=content_type,
                headers={"Content-Disposition": f"inline; filename={filename}"}
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get image: {str(e)}"
        )


# ComfyUI Model Management Endpoints
@app.get("/comfyui/db/models")
async def get_comfyui_db_models(active_only: bool = True, essential_only: bool = False):
    """Get ComfyUI models from database"""
    try:
        import asyncpg
        
        # Get database connection string
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise HTTPException(status_code=500, detail="Database URL not configured")
        
        # Connect to database
        conn = await asyncpg.connect(database_url)
        
        try:
            # Build query based on filters
            query = "SELECT * FROM public.comfyui_models WHERE 1=1"
            params = []
            
            if active_only:
                query += " AND active = $1"
                params.append(True)
                
            if essential_only:
                param_num = len(params) + 1
                query += f" AND essential = ${param_num}"
                params.append(True)
            
            query += " ORDER BY type, name"
            
            # Execute query
            rows = await conn.fetch(query, *params)
            
            # Convert to list of dicts
            models = []
            for row in rows:
                models.append(dict(row))
            
            return {
                "success": True,
                "models": models
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get models from database: {str(e)}"
        )


class ComfyUIModelRequest(BaseModel):
    """Request model for adding ComfyUI models"""
    name: str
    type: str  # 'checkpoint', 'vae', 'lora', 'controlnet', 'upscaler', 'embeddings'
    filename: str
    download_url: str
    file_size_gb: Optional[float] = None
    description: Optional[str] = None
    active: bool = True
    essential: bool = False


@app.post("/comfyui/db/models")
async def add_comfyui_model(request: ComfyUIModelRequest):
    """Add a new ComfyUI model to database"""
    try:
        import asyncpg
        
        # Get database connection string
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise HTTPException(status_code=500, detail="Database URL not configured")
        
        # Connect to database
        conn = await asyncpg.connect(database_url)
        
        try:
            # Insert model
            query = """
                INSERT INTO public.comfyui_models 
                (name, type, filename, download_url, file_size_gb, description, active, essential)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """
            
            model_id = await conn.fetchval(
                query,
                request.name,
                request.type,
                request.filename,
                request.download_url,
                request.file_size_gb,
                request.description,
                request.active,
                request.essential
            )
            
            return {
                "success": True,
                "model_id": str(model_id),
                "message": "Model added successfully"
            }
            
        finally:
            await conn.close()
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add model: {str(e)}"
        )


@app.put("/comfyui/db/models/{model_id}")
async def update_comfyui_model(model_id: str, request: ComfyUIModelRequest):
    """Update a ComfyUI model in database"""
    try:
        import asyncpg
        
        # Get database connection string
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise HTTPException(status_code=500, detail="Database URL not configured")
        
        # Connect to database
        conn = await asyncpg.connect(database_url)
        
        try:
            # Update model
            query = """
                UPDATE public.comfyui_models 
                SET name = $1, type = $2, filename = $3, download_url = $4, 
                    file_size_gb = $5, description = $6, active = $7, essential = $8,
                    updated_at = NOW()
                WHERE id = $9
                RETURNING id
            """
            
            updated_id = await conn.fetchval(
                query,
                request.name,
                request.type,
                request.filename,
                request.download_url,
                request.file_size_gb,
                request.description,
                request.active,
                request.essential,
                model_id
            )
            
            if not updated_id:
                raise HTTPException(status_code=404, detail="Model not found")
            
            return {
                "success": True,
                "model_id": str(updated_id),
                "message": "Model updated successfully"
            }
            
        finally:
            await conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update model: {str(e)}"
        )


@app.delete("/comfyui/db/models/{model_id}")
async def delete_comfyui_model(model_id: str):
    """Delete a ComfyUI model from database"""
    try:
        import asyncpg
        
        # Get database connection string
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise HTTPException(status_code=500, detail="Database URL not configured")
        
        # Connect to database
        conn = await asyncpg.connect(database_url)
        
        try:
            # Delete model
            query = "DELETE FROM public.comfyui_models WHERE id = $1 RETURNING id"
            deleted_id = await conn.fetchval(query, model_id)
            
            if not deleted_id:
                raise HTTPException(status_code=404, detail="Model not found")
            
            return {
                "success": True,
                "message": "Model deleted successfully"
            }
            
        finally:
            await conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete model: {str(e)}"
        )
