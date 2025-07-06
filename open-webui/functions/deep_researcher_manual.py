"""
title: Deep Researcher
author: GenAI Vanilla Stack
description: Advanced web research using Local Deep Researcher with real-time progress tracking
required_open_webui_version: 0.4.0
version: 1.0.0
license: MIT
"""

from typing import Optional, Callable, Awaitable
from pydantic import BaseModel, Field
import time
import requests
import asyncio


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
        max_loops: int = Field(
            default=3,
            description="Maximum research loops"
        )
        search_api: str = Field(
            default="duckduckgo",
            description="Search API to use"
        )
        emit_interval: float = Field(
            default=2.0,
            description="Interval in seconds between status emissions"
        )
        enable_status_indicator: bool = Field(
            default=True,
            description="Enable or disable status indicator emissions"
        )

    def __init__(self):
        self.type = "pipe"
        self.id = "deep_researcher"
        self.name = "Deep Researcher 🔍"
        self.valves = self.Valves()
        self.last_emit_time = 0

    async def emit_status(
        self,
        __event_emitter__: Callable[[dict], Awaitable[None]],
        level: str,
        message: str,
        done: bool,
    ):
        current_time = time.time()
        if (
            __event_emitter__
            and self.valves.enable_status_indicator
            and (current_time - self.last_emit_time >= self.valves.emit_interval or done)
        ):
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": message,
                        "done": done,
                    },
                }
            )
            self.last_emit_time = current_time

    def get_last_user_message(self, messages):
        """Extract the last user message from the conversation"""
        for message in reversed(messages):
            if message.get("role") == "user":
                content = message.get("content", "")
                if isinstance(content, str) and content.strip():
                    return content.strip()
        return None

    async def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: list,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[dict], Awaitable[None]]] = None,
        __task__: Optional[str] = None,
        __event_call__: Optional[Callable] = None,
    ) -> str:
        
        # Extract the research query
        query = self.get_last_user_message(messages)
        if not query:
            return "❌ No research query found. Please provide a question or topic to research."

        try:
            # Start research
            await self.emit_status(__event_emitter__, "info", "🚀 Starting research...", False)
            
            start_response = requests.post(
                f"{self.valves.backend_url}/research/start",
                json={
                    "query": query,
                    "max_loops": self.valves.max_loops,
                    "search_api": self.valves.search_api,
                    "user_id": "open-webui-pipe-user"
                },
                timeout=30
            )
            start_response.raise_for_status()
            start_data = start_response.json()
            
            session_id = start_data.get("session_id")
            if not session_id:
                return "❌ No session ID received from research service"

            await self.emit_status(__event_emitter__, "info", f"📋 Research session started: {session_id}", False)

            # Poll for completion with progress updates
            start_time = time.time()
            last_status = None

            while time.time() - start_time < self.valves.timeout:
                # Check status
                status_response = requests.get(
                    f"{self.valves.backend_url}/research/{session_id}/status",
                    timeout=10
                )
                status_response.raise_for_status()
                status_data = status_response.json()

                current_status = status_data.get("status", "unknown")
                
                # Show progress updates
                if current_status != last_status:
                    if current_status == "running":
                        await self.emit_status(__event_emitter__, "info", "🔍 Research in progress...", False)
                    elif current_status == "pending":
                        await self.emit_status(__event_emitter__, "info", "⏳ Research queued...", False)
                    last_status = current_status

                if current_status == "completed":
                    await self.emit_status(__event_emitter__, "info", "✅ Research completed! Formatting results...", False)
                    
                    # Get results
                    result_response = requests.get(
                        f"{self.valves.backend_url}/research/{session_id}/result",
                        timeout=30
                    )
                    result_response.raise_for_status()
                    result_data = result_response.json()

                    # Format response
                    await self.emit_status(__event_emitter__, "info", "", True)
                    
                    return self.format_research_results(result_data, query, session_id)

                elif current_status in ["failed", "cancelled"]:
                    error_msg = status_data.get("error_message", f"Research {current_status}")
                    return f"❌ Research {current_status}: {error_msg}"

                # Wait before next check
                await asyncio.sleep(5)

            return f"❌ Research timed out after {self.valves.timeout} seconds"

        except requests.RequestException as e:
            return f"❌ API request failed: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected error during research: {str(e)}"

    def format_research_results(self, result_data, query, session_id):
        """Format research results for display"""
        try:
            # Handle the result_data format
            title = result_data.get("title", "Research Results")
            summary = result_data.get("summary", "")
            content = result_data.get("content", "")
            
            # Try to parse sources if they're in string format
            sources = result_data.get("sources", [])
            if isinstance(sources, str):
                try:
                    import json
                    sources = json.loads(sources)
                except:
                    sources = []
            
            output = []
            output.append(f"# {title}\n")
            
            if summary:
                output.append(f"## Summary\n{summary}\n")
            
            if content:
                output.append(f"## Detailed Findings\n{content}\n")
            
            if sources and len(sources) > 0:
                output.append("## Sources")
                for i, source in enumerate(sources, 1):
                    if isinstance(source, dict):
                        url = source.get("url", "")
                        title = source.get("title", "Untitled")
                        output.append(f"{i}. [{title}]({url})")
                output.append("")
            
            output.append(f"**Session ID**: `{session_id}`")
            output.append(f"**Query**: {query}")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"Research completed successfully, but formatting failed: {str(e)}\n\nSession ID: {session_id}"