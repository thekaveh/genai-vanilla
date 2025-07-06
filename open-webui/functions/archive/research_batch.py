"""
title: Batch Research
author: GenAI Vanilla Stack
description: Perform multiple research queries simultaneously and get consolidated results
requirements: requests, asyncio
version: 1.0.0
"""

import requests
import time
import json
from typing import Dict, Any, List, Optional
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


class BatchResearchFunction:
    def __init__(self):
        self.backend_url = "http://backend:8000"
        self.timeout = 600  # 10 minutes for batch
        self.poll_interval = 10  # 10 seconds

    def start_single_research(self, query_data: Dict[str, Any], batch_id: str) -> Dict[str, Any]:
        """Start a single research session"""
        try:
            payload = {
                "query": query_data["query"],
                "max_loops": query_data.get("max_loops", 3),
                "search_api": query_data.get("search_api", "duckduckgo"),
                "user_id": query_data.get("user_id", f"batch-{batch_id}")
            }
            
            response = requests.post(
                f"{self.backend_url}/research/start",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "query": query_data["query"],
                "session_id": result.get("session_id"),
                "status": "started",
                "index": query_data.get("index", 0)
            }
        except requests.RequestException as e:
            return {
                "query": query_data["query"],
                "error": f"Failed to start research: {str(e)}",
                "status": "failed",
                "index": query_data.get("index", 0)
            }

    def get_research_result(self, session_id: str, query: str, index: int) -> Dict[str, Any]:
        """Get research result for a session"""
        try:
            response = requests.get(
                f"{self.backend_url}/research/{session_id}/result",
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "index": index,
                "query": query,
                "session_id": session_id,
                "status": "completed",
                "title": result.get("title", ""),
                "summary": result.get("summary", ""),
                "content": result.get("content", ""),
                "sources": result.get("sources", []),
                "metadata": result.get("metadata", {}),
                "source_count": len(result.get("sources", [])),
                "content_length": len(result.get("content", ""))
            }
        except requests.RequestException as e:
            return {
                "index": index,
                "query": query,
                "session_id": session_id,
                "status": "failed",
                "error": f"Failed to get results: {str(e)}"
            }

    def check_session_status(self, session_id: str) -> str:
        """Check if a research session is completed"""
        try:
            response = requests.get(
                f"{self.backend_url}/research/{session_id}/status",
                timeout=10
            )
            response.raise_for_status()
            status_data = response.json()
            return status_data.get("status", "unknown")
        except requests.RequestException:
            return "error"

    def wait_for_all_completion(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Wait for all research sessions to complete"""
        start_time = time.time()
        completed_results = []
        
        # Filter out failed starts
        valid_sessions = [s for s in sessions if "session_id" in s and s["session_id"]]
        
        while time.time() - start_time < self.timeout and valid_sessions:
            # Check status of all sessions
            remaining_sessions = []
            
            for session in valid_sessions:
                session_id = session["session_id"]
                status = self.check_session_status(session_id)
                
                if status == "completed":
                    result = self.get_research_result(
                        session_id, 
                        session["query"], 
                        session["index"]
                    )
                    completed_results.append(result)
                elif status in ["failed", "cancelled"]:
                    completed_results.append({
                        "index": session["index"],
                        "query": session["query"],
                        "session_id": session_id,
                        "status": status,
                        "error": f"Research {status}"
                    })
                else:
                    # Still running or pending
                    remaining_sessions.append(session)
            
            valid_sessions = remaining_sessions
            
            if not valid_sessions:
                break  # All completed
            
            time.sleep(self.poll_interval)
        
        # Handle any remaining incomplete sessions
        for session in valid_sessions:
            completed_results.append({
                "index": session["index"],
                "query": session["query"],
                "session_id": session["session_id"],
                "status": "timeout",
                "error": f"Research timed out after {self.timeout} seconds"
            })
        
        # Add failed starts
        for session in sessions:
            if "error" in session:
                completed_results.append({
                    "index": session["index"],
                    "query": session["query"],
                    "session_id": session.get("session_id", "none"),
                    "status": "failed",
                    "error": session["error"]
                })
        
        # Sort by index to maintain order
        completed_results.sort(key=lambda x: x["index"])
        return completed_results

    def process_batch_queries(self, queries: List[Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process multiple queries in parallel"""
        batch_id = str(int(time.time()))
        
        # Normalize queries
        normalized_queries = []
        for i, query in enumerate(queries):
            if isinstance(query, str):
                normalized_queries.append({
                    "query": query,
                    "max_loops": config.get("max_loops", 3),
                    "search_api": config.get("search_api", "duckduckgo"),
                    "user_id": config.get("user_id"),
                    "index": i
                })
            elif isinstance(query, dict):
                normalized_queries.append({
                    "query": query.get("query", ""),
                    "max_loops": query.get("max_loops", config.get("max_loops", 3)),
                    "search_api": query.get("search_api", config.get("search_api", "duckduckgo")),
                    "user_id": query.get("user_id", config.get("user_id")),
                    "index": i
                })
            else:
                normalized_queries.append({
                    "query": str(query),
                    "max_loops": config.get("max_loops", 3),
                    "search_api": config.get("search_api", "duckduckgo"),
                    "user_id": config.get("user_id"),
                    "index": i
                })
        
        # Start all research sessions in parallel
        sessions = []
        with ThreadPoolExecutor(max_workers=min(10, len(normalized_queries))) as executor:
            future_to_query = {
                executor.submit(self.start_single_research, query, batch_id): query
                for query in normalized_queries
            }
            
            for future in as_completed(future_to_query):
                result = future.result()
                sessions.append(result)
        
        # Wait for all to complete
        results = self.wait_for_all_completion(sessions)
        
        return results


def main(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function for batch research operations
    
    Expected body format:
    {
        "queries": [
            "First research question",
            "Second research question",
            {
                "query": "Third question with custom settings",
                "max_loops": 5,
                "search_api": "duckduckgo"
            }
        ],
        "config": {
            "max_loops": 3,          # default for all queries
            "search_api": "duckduckgo", # default for all queries
            "user_id": "optional-user-id"
        }
    }
    """
    
    # Extract parameters
    queries = body.get("queries", [])
    config = body.get("config", {})
    
    # Validate input
    if not queries or not isinstance(queries, list) or len(queries) == 0:
        return {
            "success": False,
            "error": "queries parameter is required and must be a non-empty list",
            "usage": "Provide a 'queries' list with your research questions"
        }
    
    if len(queries) > 20:
        return {
            "success": False,
            "error": "Maximum 20 queries allowed per batch",
            "provided_count": len(queries)
        }
    
    # Initialize batch research function
    batch_research = BatchResearchFunction()
    
    try:
        start_time = time.time()
        
        # Process all queries
        results = batch_research.process_batch_queries(queries, config)
        
        processing_time = time.time() - start_time
        
        # Calculate statistics
        completed_count = len([r for r in results if r.get("status") == "completed"])
        failed_count = len([r for r in results if r.get("status") in ["failed", "timeout"]])
        total_sources = sum(r.get("source_count", 0) for r in results if r.get("status") == "completed")
        total_content_length = sum(r.get("content_length", 0) for r in results if r.get("status") == "completed")
        
        return {
            "success": True,
            "batch_summary": {
                "total_queries": len(queries),
                "completed_successfully": completed_count,
                "failed": failed_count,
                "success_rate": completed_count / len(queries) if queries else 0,
                "total_sources_found": total_sources,
                "total_content_length": total_content_length,
                "processing_time_seconds": round(processing_time, 2)
            },
            "results": results,
            "config_used": config
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error during batch research: {str(e)}",
            "queries_attempted": len(queries)
        }


# Example usage for testing
if __name__ == "__main__":
    test_body = {
        "queries": [
            "Latest AI developments",
            "Blockchain technology trends",
            {
                "query": "Climate change research",
                "max_loops": 4
            }
        ],
        "config": {
            "max_loops": 3,
            "search_api": "duckduckgo",
            "user_id": "test-user"
        }
    }
    
    result = main(test_body)
    print(json.dumps(result, indent=2))