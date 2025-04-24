from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from storage3 import SyncStorageClient as StorageClient
from typing import Optional, cast
import os

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

# Get environment variables with defaults
STORAGE_PORT = os.getenv("SUPABASE_STORAGE_PORT", "63002")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SERVICE_KEY:
    raise ValueError("SUPABASE_SERVICE_KEY environment variable is required")

# Initialize Supabase Storage client
storage_client = StorageClient(
    url=f"http://localhost:{STORAGE_PORT}",
    headers={
        "Authorization": f"Bearer {SERVICE_KEY}",
        "apikey": SERVICE_KEY,
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
