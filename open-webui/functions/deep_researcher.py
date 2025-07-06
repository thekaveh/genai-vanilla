"""
title: Deep Researcher
author: GenAI Vanilla Stack
description: Advanced web research using Local Deep Researcher with real-time progress tracking
requirements: requests
version: 1.0.0
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.research_client import ResearchClient, ResearchConfig, format_research_results


def main(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform comprehensive web research using the Deep Researcher service
    
    Args:
        body: Dictionary with parameters:
            - query: Research question (required)
            - max_loops: Research depth (optional, default: 3)
            - search_api: Search engine (optional, default: duckduckgo)
    
    Returns:
        Dictionary with research results or error information
    """
    
    # Extract parameters
    query = body.get("query", "").strip()
    max_loops = body.get("max_loops", 3)
    search_api = body.get("search_api", "duckduckgo")
    
    # Validate input
    if not query:
        return {
            "success": False,
            "error": "Query parameter is required",
            "usage": "Provide a 'query' parameter with your research question",
            "example": '{"query": "latest AI developments in 2024"}'
        }
    
    # Initialize client
    client = ResearchClient()
    
    # Define callbacks for progress updates
    def status_callback(status: str, progress: Dict[str, Any]):
        if status == "running":
            current_loop = progress.get("current_loop", 0)
            total_loops = progress.get("total_loops", max_loops)
            sources_found = progress.get("sources_found", 0)
            print(f"🔍 Researching... Loop {current_loop}/{total_loops} | Sources found: {sources_found}")
        elif status == "pending":
            print("⏳ Research queued...")
        elif status == "completed":
            print("✅ Research completed! Getting results...")
    
    print(f"🔍 Starting research: {query}")
    
    # Perform research with polling
    result = client.research_with_polling(
        query=query,
        max_loops=max_loops,
        search_api=search_api,
        status_callback=status_callback
    )
    
    # Process result
    if result["success"]:
        result_data = result["data"]
        session_id = result["session_id"]
        
        return {
            "success": True,
            "query": query,
            "session_id": session_id,
            "title": result_data.get("title", "Research Results"),
            "summary": result_data.get("summary", ""),
            "content": result_data.get("content", ""),
            "sources": result_data.get("sources", []),
            "metadata": result_data.get("metadata", {}),
            "stats": {
                "source_count": len(result_data.get("sources", [])),
                "content_length": len(result_data.get("content", "")),
                "max_loops_used": max_loops,
                "search_api_used": search_api
            }
        }
    else:
        return result


# Example usage for testing
if __name__ == "__main__":
    test_body = {
        "query": "Latest developments in artificial intelligence",
        "max_loops": 2,
        "search_api": "duckduckgo"
    }
    
    result = main(test_body)
    print(json.dumps(result, indent=2))