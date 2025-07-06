"""
title: Simple Research
author: GenAI Vanilla Stack  
description: Perform web research using the backend research service
requirements: requests
version: 1.0.0
"""

import requests
import time
import json
from typing import Dict, Any

def main(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform research using the backend service
    
    Args:
        body: Dictionary with 'query' key containing the research question
    
    Returns:
        Dictionary with research results
    """
    
    # Extract query from input
    query = body.get("query", "").strip()
    max_loops = body.get("max_loops", 3)
    
    if not query:
        return {
            "success": False,
            "error": "Please provide a 'query' parameter with your research question",
            "usage": 'Example: {"query": "latest AI developments"}'
        }
    
    try:
        # Start research via backend API
        start_response = requests.post(
            "http://backend:8000/research/start",
            json={
                "query": query,
                "max_loops": max_loops,
                "search_api": "duckduckgo",
                "user_id": "openwebui-user"
            },
            timeout=30
        )
        start_response.raise_for_status()
        start_data = start_response.json()
        
        session_id = start_data.get("session_id")
        if not session_id:
            return {"success": False, "error": "Failed to start research session"}
        
        # Poll for completion (max 5 minutes)
        timeout = 300
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check status
            status_response = requests.get(
                f"http://backend:8000/research/{session_id}/status",
                timeout=10
            )
            status_response.raise_for_status()
            status_data = status_response.json()
            
            if status_data.get("status") == "completed":
                # Get results
                result_response = requests.get(
                    f"http://backend:8000/research/{session_id}/result",
                    timeout=30
                )
                result_response.raise_for_status()
                result_data = result_response.json()
                
                return {
                    "success": True,
                    "query": query,
                    "session_id": session_id,
                    "title": result_data.get("title", "Research Results"),
                    "summary": result_data.get("summary", ""),
                    "content": result_data.get("content", ""),
                    "sources": result_data.get("sources", []),
                    "metadata": result_data.get("metadata", {})
                }
            
            elif status_data.get("status") in ["failed", "cancelled"]:
                error_msg = status_data.get("error_message", "Research failed")
                return {"success": False, "error": f"Research {status_data.get('status')}: {error_msg}"}
            
            # Still running, wait
            time.sleep(5)
        
        return {"success": False, "error": f"Research timed out after {timeout} seconds"}
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API request failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}