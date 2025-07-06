"""
title: Deep Researcher Tool
author: GenAI Vanilla Stack
author_url: https://github.com/vanilla-genai
description: AI-powered web research tool that integrates with Local Deep Researcher service
required_open_webui_version: 0.4.4
requirements: pydantic, requests
version: 1.0.0
license: MIT
"""

import json
import sys
import time
from pathlib import Path
from typing import List, Union, Generator, Iterator, Dict, Any, Optional
from pydantic import BaseModel, Field

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.research_client import ResearchClient, ResearchConfig, format_research_results


class Tools:
    def __init__(self):
        pass

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
        default_max_loops: int = Field(
            default=3,
            description="Default maximum research loops"
        )
        default_search_api: str = Field(
            default="duckduckgo",
            description="Default search API to use (duckduckgo, bing, etc.)"
        )
        enable_tool: bool = Field(
            default=True,
            description="Enable this tool for the AI assistant"
        )

    def __init__(self):
        self.valves = self.Valves()

    def research_web(
        self, 
        query: str, 
        max_loops: Optional[int] = None,
        search_api: Optional[str] = None,
        __event_emitter__: Optional[Any] = None
    ) -> str:
        """
        Perform comprehensive web research on a given topic or question.
        
        This tool uses an advanced AI-powered research service to search the web,
        analyze multiple sources, and provide a comprehensive answer with citations.
        
        :param query: The research question or topic to investigate
        :param max_loops: Number of research iterations (default: 3, more loops = deeper research)
        :param search_api: Search engine to use (default: duckduckgo, options: bing, google)
        :param __event_emitter__: Event emitter for status updates
        :return: Comprehensive research results with summary, detailed findings, and sources
        """
        
        if not self.valves.enable_tool:
            return "Deep Researcher tool is currently disabled."
        
        # Use defaults if not specified
        max_loops = max_loops or self.valves.default_max_loops
        search_api = search_api or self.valves.default_search_api
        
        # Initialize client with custom config
        config = ResearchConfig(
            backend_url=self.valves.backend_url,
            timeout=self.valves.timeout,
            poll_interval=self.valves.poll_interval,
            max_loops=self.valves.default_max_loops,
            search_api=self.valves.default_search_api
        )
        client = ResearchClient(config)
        
        # Define progress callback for event emitter
        last_status_update = [0]  # Use list to allow modification in closure
        
        def progress_callback(progress: Dict[str, Any]):
            if __event_emitter__ and time.time() - last_status_update[0] > 2:
                current_loop = progress.get("current_loop", 0)
                total_loops = progress.get("total_loops", max_loops)
                sources_found = progress.get("sources_found", 0)
                
                __event_emitter__({
                    "type": "status",
                    "data": {
                        "description": f"🔍 Researching... Loop {current_loop}/{total_loops} | Sources: {sources_found}",
                        "done": False
                    }
                })
                last_status_update[0] = time.time()
        
        def status_callback(status: str, progress: Dict[str, Any]):
            if __event_emitter__:
                if status == "pending":
                    __event_emitter__({
                        "type": "status",
                        "data": {
                            "description": f"🚀 Starting web research: {query[:50]}...",
                            "done": False
                        }
                    })
        
        # Perform research
        result = client.research_with_polling(
            query=query,
            max_loops=max_loops,
            search_api=search_api,
            user_id="open-webui-tool-user",
            progress_callback=progress_callback,
            status_callback=status_callback
        )
        
        # Clear status on completion
        if __event_emitter__:
            __event_emitter__({
                "type": "status",
                "data": {
                    "description": "",
                    "done": True
                }
            })
        
        # Process and format results
        if result["success"]:
            return format_research_results(result["data"], query)
        else:
            return result["error"]
    
    def get_research_history(
        self,
        limit: int = 10,
        include_results: bool = False
    ) -> str:
        """
        Get recent research history.
        
        :param limit: Maximum number of sessions to return (default: 10)
        :param include_results: Include full results in response (default: False)
        :return: List of recent research sessions
        """
        
        if not self.valves.enable_tool:
            return "Deep Researcher tool is currently disabled."
        
        # Initialize client with custom config
        config = ResearchConfig(backend_url=self.valves.backend_url)
        client = ResearchClient(config)
        
        try:
            sessions = client.get_sessions(limit=limit, include_results=include_results)
            
            if not sessions:
                return "No research history found."
            
            # Format sessions
            output = ["# Research History\n"]
            
            for session in sessions:
                output.append(f"## {session.get('query', 'Unknown Query')}")
                output.append(f"- **Session ID**: {session.get('session_id', 'N/A')}")
                output.append(f"- **Status**: {session.get('status', 'Unknown')}")
                output.append(f"- **Created**: {session.get('created_at', 'Unknown')}")
                
                if include_results and session.get('status') == 'completed':
                    result = session.get('result', {})
                    if result:
                        output.append(f"- **Summary**: {result.get('summary', 'N/A')[:200]}...")
                        sources = result.get('sources', [])
                        output.append(f"- **Sources Found**: {len(sources)}")
                
                output.append("")
            
            return "\n".join(output)
            
        except Exception as e:
            return f"Failed to get research history: {str(e)}"
    
