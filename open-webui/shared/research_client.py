"""
Shared research client module for Open-WebUI functions and tools.
Provides a common interface to the Deep Researcher backend service.
"""

import requests
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class ResearchConfig:
    """Configuration for research requests"""
    backend_url: str = "http://backend:8000"
    timeout: int = 300  # 5 minutes
    poll_interval: int = 5  # 5 seconds
    max_loops: int = 3
    search_api: str = "duckduckgo"


class ResearchClient:
    """Client for interacting with the Deep Researcher backend service"""
    
    def __init__(self, config: Optional[ResearchConfig] = None):
        self.config = config or ResearchConfig()
    
    def start_research(
        self, 
        query: str,
        max_loops: Optional[int] = None,
        search_api: Optional[str] = None,
        user_id: str = "open-webui-user"
    ) -> Dict[str, Any]:
        """Start a new research session"""
        response = requests.post(
            f"{self.config.backend_url}/research/start",
            json={
                "query": query,
                "max_loops": max_loops or self.config.max_loops,
                "search_api": search_api or self.config.search_api,
                "user_id": user_id
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def get_status(self, session_id: str) -> Dict[str, Any]:
        """Get the status of a research session"""
        response = requests.get(
            f"{self.config.backend_url}/research/{session_id}/status",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def get_result(self, session_id: str) -> Dict[str, Any]:
        """Get the results of a completed research session"""
        response = requests.get(
            f"{self.config.backend_url}/research/{session_id}/result",
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def get_sessions(
        self, 
        limit: int = 10, 
        include_results: bool = False
    ) -> list:
        """Get recent research sessions"""
        response = requests.get(
            f"{self.config.backend_url}/research/sessions",
            params={"limit": limit, "include_results": include_results},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def research_with_polling(
        self,
        query: str,
        max_loops: Optional[int] = None,
        search_api: Optional[str] = None,
        user_id: str = "open-webui-user",
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        status_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Perform research with automatic polling for completion.
        
        Args:
            query: Research question
            max_loops: Number of research iterations
            search_api: Search engine to use
            user_id: User identifier
            progress_callback: Called with progress updates during research
            status_callback: Called with status changes
            
        Returns:
            Research results or error information
        """
        try:
            # Start research
            start_data = self.start_research(query, max_loops, search_api, user_id)
            session_id = start_data.get("session_id")
            
            if not session_id:
                return {
                    "success": False,
                    "error": "No session ID returned from research service",
                    "query": query
                }
            
            # Poll for completion
            start_time = time.time()
            last_status = None
            
            while time.time() - start_time < self.config.timeout:
                status_data = self.get_status(session_id)
                current_status = status_data.get("status", "unknown")
                progress = status_data.get("progress", {})
                
                # Notify status change
                if current_status != last_status:
                    if status_callback:
                        status_callback(current_status, progress)
                    last_status = current_status
                
                # Notify progress
                if progress_callback and current_status == "running":
                    progress_callback(progress)
                
                # Check completion
                if current_status == "completed":
                    result_data = self.get_result(session_id)
                    return {
                        "success": True,
                        "query": query,
                        "session_id": session_id,
                        "data": result_data
                    }
                
                elif current_status in ["failed", "cancelled"]:
                    error_msg = status_data.get("error_message", f"Research {current_status}")
                    return {
                        "success": False,
                        "error": f"Research {current_status}: {error_msg}",
                        "query": query,
                        "session_id": session_id
                    }
                
                time.sleep(self.config.poll_interval)
            
            # Timeout
            return {
                "success": False,
                "error": f"Research timed out after {self.config.timeout} seconds",
                "query": query,
                "session_id": session_id
            }
            
        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"API request failed: {str(e)}",
                "query": query
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "query": query
            }


def format_research_results(result: Dict[str, Any], query: str) -> str:
    """Format research results for display"""
    output = []
    
    # Title
    title = result.get("title", f"Research Results: {query}")
    output.append(f"# {title}\n")
    
    # Summary
    summary = result.get("summary", "")
    if summary:
        output.append(f"## Summary\n{summary}\n")
    
    # Main content
    content = result.get("content", "")
    if content:
        # Limit content length for readability
        if len(content) > 3000:
            content = content[:3000] + "\n\n[Content truncated for brevity...]"
        output.append(f"## Detailed Findings\n{content}\n")
    
    # Sources
    sources = result.get("sources", [])
    if sources:
        output.append("## Sources")
        for i, source in enumerate(sources[:10], 1):
            url = source.get("url", "")
            title = source.get("title", "Untitled")
            output.append(f"{i}. [{title}]({url})")
        
        if len(sources) > 10:
            output.append(f"\n*Plus {len(sources) - 10} more sources...*")
        output.append("")
    
    # Metadata
    metadata = result.get("metadata", {})
    if metadata:
        output.append("## Research Statistics")
        output.append(f"- Research Duration: {metadata.get('duration', 'N/A')} seconds")
        output.append(f"- Sources Analyzed: {metadata.get('total_sources', 0)}")
        output.append(f"- Search Queries: {metadata.get('search_queries', 0)}")
        output.append(f"- Total Content: {metadata.get('total_content_length', 0):,} characters")
    
    return "\n".join(output)