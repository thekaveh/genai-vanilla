"""
title: Research Query
author: GenAI Vanilla Stack
description: Perform comprehensive web research on any topic using the Local Deep Researcher service
requirements: requests, asyncio
version: 1.0.0
"""

import requests
import time
import json
from typing import Dict, Any, Optional
import asyncio
import threading


class ResearchFunction:
    def __init__(self):
        self.backend_url = "http://backend:8000"
        self.timeout = 300  # 5 minutes
        self.poll_interval = 5  # 5 seconds

    def start_research(self, query: str, max_loops: int = 3, search_api: str = "duckduckgo", user_id: Optional[str] = None) -> Dict[str, Any]:
        """Start a research session"""
        try:
            response = requests.post(
                f"{self.backend_url}/research/start",
                json={
                    "query": query,
                    "max_loops": max_loops,
                    "search_api": search_api,
                    "user_id": user_id or "open-webui-user"
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
                f"{self.backend_url}/research/{session_id}/status",
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
                f"{self.backend_url}/research/{session_id}/result",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": f"Failed to get results: {str(e)}"}

    def wait_for_completion(self, session_id: str) -> Dict[str, Any]:
        """Wait for research to complete with status updates"""
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            status_response = self.get_research_status(session_id)
            
            if "error" in status_response:
                return status_response
            
            status = status_response.get("status", "unknown")
            
            if status == "completed":
                return self.get_research_result(session_id)
            elif status == "failed":
                error_msg = status_response.get("error_message", "Research failed")
                return {"error": f"Research failed: {error_msg}"}
            elif status == "cancelled":
                return {"error": "Research was cancelled"}
            
            # Still running, wait and check again
            time.sleep(self.poll_interval)
        
        return {"error": f"Research timed out after {self.timeout} seconds"}


def main(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function for performing research queries
    
    Expected body format:
    {
        "query": "Your research question",
        "max_loops": 3,  # optional
        "search_api": "duckduckgo",  # optional
        "user_id": "optional-user-id"  # optional
    }
    """
    
    # Extract parameters
    query = body.get("query", "").strip()
    max_loops = body.get("max_loops", 3)
    search_api = body.get("search_api", "duckduckgo")
    user_id = body.get("user_id")
    
    # Validate input
    if not query:
        return {
            "success": False,
            "error": "Query parameter is required",
            "usage": "Provide a 'query' parameter with your research question"
        }
    
    # Initialize research function
    research = ResearchFunction()
    
    try:
        # Start research
        start_response = research.start_research(query, max_loops, search_api, user_id)
        
        if "error" in start_response:
            return {
                "success": False,
                "error": start_response["error"],
                "query": query
            }
        
        session_id = start_response.get("session_id")
        if not session_id:
            return {
                "success": False,
                "error": "No session ID returned from research service",
                "query": query
            }
        
        # Wait for completion and get results
        result = research.wait_for_completion(session_id)
        
        if "error" in result:
            return {
                "success": False,
                "error": result["error"],
                "query": query,
                "session_id": session_id
            }
        
        # Format successful response
        return {
            "success": True,
            "query": query,
            "session_id": session_id,
            "title": result.get("title", "Research Results"),
            "summary": result.get("summary", ""),
            "content": result.get("content", ""),
            "sources": result.get("sources", []),
            "metadata": result.get("metadata", {}),
            "stats": {
                "source_count": len(result.get("sources", [])),
                "content_length": len(result.get("content", "")),
                "max_loops_used": max_loops,
                "search_api_used": search_api
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error during research: {str(e)}",
            "query": query
        }


# Example usage for testing
if __name__ == "__main__":
    test_body = {
        "query": "Latest developments in artificial intelligence",
        "max_loops": 2,
        "search_api": "duckduckgo"
    }
    
    result = main(test_body)
    print(json.dumps(result, indent=2))