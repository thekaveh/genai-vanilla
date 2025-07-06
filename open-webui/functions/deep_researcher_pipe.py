"""
title: Deep Researcher Pipe
author: GenAI Vanilla Stack
author_url: https://github.com/vanilla-genai
description: Advanced web research using Local Deep Researcher service with real-time status updates
required_open_webui_version: 0.4.4
requirements: pydantic, requests, asyncio
version: 1.0.0
license: MIT
"""

import asyncio
import json
import requests
import time
from typing import List, Union, Generator, Iterator, Dict, Any, Optional
from pydantic import BaseModel, Field


class Pipe:
    class Valves(BaseModel):
        backend_url: str = Field(
            default="http://backend:8000",
            description="Backend service URL for research API"
        )
        timeout: int = Field(
            default=300,
            description="Maximum time to wait for research completion (seconds)"
        )
        poll_interval: int = Field(
            default=5,
            description="Interval between status checks (seconds)"
        )
        max_loops: int = Field(
            default=3,
            description="Maximum research loops"
        )
        search_api: str = Field(
            default="duckduckgo",
            description="Search API to use (duckduckgo, bing, etc.)"
        )
        emit_interval: int = Field(
            default=2,
            description="Interval between status emissions (seconds)"
        )
        show_status: bool = Field(
            default=True,
            description="Show research progress status"
        )

    def __init__(self):
        self.type = "pipe"
        self.id = "deep_researcher"
        self.name = "Deep Researcher 🔍"
        self.valves = self.Valves()
        self.session_id = None
        self.last_status = None

    def get_last_user_message(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """Extract the last user message from the conversation"""
        for message in reversed(messages):
            if message.get("role") == "user":
                content = message.get("content", "")
                if isinstance(content, str) and content.strip():
                    return content.strip()
        return None

    def start_research(self, query: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Start a research session"""
        try:
            response = requests.post(
                f"{self.valves.backend_url}/research/start",
                json={
                    "query": query,
                    "max_loops": self.valves.max_loops,
                    "search_api": self.valves.search_api,
                    "user_id": user_id or "open-webui-pipe-user"
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": f"Failed to start research: {str(e)}"}

    def get_research_status(self, session_id: str) -> Dict[str, Any]:
        """Get research session status"""
        try:
            response = requests.get(
                f"{self.valves.backend_url}/research/{session_id}/status",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": f"Failed to get status: {str(e)}"}

    def get_research_result(self, session_id: str) -> Dict[str, Any]:
        """Get research results"""
        try:
            response = requests.get(
                f"{self.valves.backend_url}/research/{session_id}/result",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": f"Failed to get results: {str(e)}"}

    async def emit_status(self, __event_emitter__: Any, status_message: str) -> None:
        """Emit status update if emitter is available"""
        if __event_emitter__ and self.valves.show_status:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": status_message,
                        "done": False
                    }
                }
            )

    async def emit_research_progress(self, __event_emitter__: Any, session_id: str) -> None:
        """Emit research progress updates"""
        while True:
            status_response = self.get_research_status(session_id)
            
            if "error" in status_response:
                await self.emit_status(__event_emitter__, f"⚠️ Error checking status: {status_response['error']}")
                break
            
            status = status_response.get("status", "unknown")
            progress = status_response.get("progress", {})
            
            # Create progress message
            if status == "running":
                current_loop = progress.get("current_loop", 0)
                total_loops = progress.get("total_loops", self.valves.max_loops)
                sources_found = progress.get("sources_found", 0)
                
                status_msg = f"🔍 Researching... Loop {current_loop}/{total_loops} | Sources found: {sources_found}"
                
                if current_loop > 0:
                    status_msg += f" | Processing search results..."
                
                await self.emit_status(__event_emitter__, status_msg)
            
            elif status == "completed":
                await self.emit_status(__event_emitter__, "✅ Research completed!")
                break
            
            elif status == "failed":
                error_msg = status_response.get("error_message", "Unknown error")
                await self.emit_status(__event_emitter__, f"❌ Research failed: {error_msg}")
                break
            
            elif status == "cancelled":
                await self.emit_status(__event_emitter__, "🚫 Research cancelled")
                break
            
            await asyncio.sleep(self.valves.emit_interval)

    def format_research_results(self, result: Dict[str, Any]) -> str:
        """Format research results for display"""
        output = []
        
        # Title
        title = result.get("title", "Research Results")
        output.append(f"# {title}\n")
        
        # Summary
        summary = result.get("summary", "")
        if summary:
            output.append(f"## Summary\n{summary}\n")
        
        # Main content
        content = result.get("content", "")
        if content:
            output.append(f"## Detailed Findings\n{content}\n")
        
        # Sources
        sources = result.get("sources", [])
        if sources:
            output.append("## Sources")
            for i, source in enumerate(sources, 1):
                url = source.get("url", "")
                title = source.get("title", "Untitled")
                output.append(f"{i}. [{title}]({url})")
            output.append("")
        
        # Metadata
        metadata = result.get("metadata", {})
        if metadata:
            output.append("## Research Metadata")
            output.append(f"- Duration: {metadata.get('duration', 'N/A')} seconds")
            output.append(f"- Sources analyzed: {metadata.get('total_sources', 0)}")
            output.append(f"- Search queries: {metadata.get('search_queries', 0)}")
            output.append(f"- Content size: {metadata.get('total_content_length', 0)} characters")
        
        return "\n".join(output)

    async def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[Dict[str, Any]],
        body: Dict[str, Any],
        __event_emitter__: Optional[Any] = None,
        __event_call__: Optional[Any] = None
    ) -> Union[str, Generator, Iterator]:
        """
        Process research requests through the pipe
        """
        
        # Extract the research query
        query = self.get_last_user_message(messages)
        if not query:
            return "❌ No research query found. Please provide a question or topic to research."
        
        try:
            # Start the research
            await self.emit_status(__event_emitter__, "🚀 Starting research...")
            
            start_response = self.start_research(query)
            
            if "error" in start_response:
                return f"❌ Failed to start research: {start_response['error']}"
            
            session_id = start_response.get("session_id")
            if not session_id:
                return "❌ No session ID received from research service"
            
            self.session_id = session_id
            
            # Start progress monitoring
            if __event_emitter__:
                progress_task = asyncio.create_task(
                    self.emit_research_progress(__event_emitter__, session_id)
                )
            
            # Wait for completion
            start_time = time.time()
            result = None
            
            while time.time() - start_time < self.valves.timeout:
                status_response = self.get_research_status(session_id)
                
                if "error" in status_response:
                    if __event_emitter__:
                        progress_task.cancel()
                    return f"❌ Error checking research status: {status_response['error']}"
                
                status = status_response.get("status", "unknown")
                
                if status == "completed":
                    result = self.get_research_result(session_id)
                    break
                elif status in ["failed", "cancelled"]:
                    if __event_emitter__:
                        progress_task.cancel()
                    error_msg = status_response.get("error_message", f"Research {status}")
                    return f"❌ Research {status}: {error_msg}"
                
                await asyncio.sleep(self.valves.poll_interval)
            
            # Cancel progress task
            if __event_emitter__:
                progress_task.cancel()
            
            if not result:
                return f"❌ Research timed out after {self.valves.timeout} seconds"
            
            if "error" in result:
                return f"❌ Failed to get research results: {result['error']}"
            
            # Clear final status
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "",
                            "done": True
                        }
                    }
                )
            
            # Format and return results
            return self.format_research_results(result)
            
        except Exception as e:
            return f"❌ Unexpected error during research: {str(e)}"