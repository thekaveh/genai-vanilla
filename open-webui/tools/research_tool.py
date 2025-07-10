"""
title: Research Assistant
author: GenAI Vanilla Stack
author_url: https://github.com/vanilla-genai
description: Web research tool for comprehensive information gathering
required_open_webui_version: 0.4.4
requirements: requests
version: 1.4.0
license: MIT
"""

import time
import requests
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        researcher_url: str = Field(
            default="http://local-deep-researcher:2024",
            description="Deep Researcher service URL"
        )
        timeout: int = Field(
            default=300,
            description="Max wait time in seconds"
        )
        enable_tool: bool = Field(
            default=True,
            description="Enable this research tool"
        )
    
    def __init__(self):
        self.valves = self.Valves()
    
    def research(self, query: str) -> str:
        """
        Research a topic using web search and AI analysis.
        
        :param query: The topic or question to research
        :return: Research findings with sources
        """
        
        if not self.valves.enable_tool:
            return "Research tool is currently disabled."
        
        if not query:
            return "Please provide a research query."
        
        try:
            # Create a new thread with unique metadata
            import time
            timestamp = int(time.time() * 1000)  # millisecond timestamp for uniqueness
            
            thread_resp = requests.post(
                f"{self.valves.researcher_url}/threads",
                json={
                    "metadata": {
                        "query": query,
                        "timestamp": timestamp,
                        "source": "open_webui_research_tool"
                    }
                },
                timeout=30
            )
            
            if thread_resp.status_code != 200:
                return f"❌ Failed to create thread: HTTP {thread_resp.status_code}"
            
            thread_data = thread_resp.json()
            thread_id = thread_data.get("thread_id")
            
            if not thread_id:
                return "❌ Failed to create research thread."
            
            # Start research run with correct input format
            resp = requests.post(
                f"{self.valves.researcher_url}/threads/{thread_id}/runs/wait",
                json={
                    "assistant_id": "a6ab75b8-fb3d-5c2c-a436-2fee55e33a06",
                    "input": {
                        "research_topic": query  # Deep Researcher expects 'research_topic' not 'query'
                    },
                    "config": {
                        "max_loops": 3, 
                        "search_api": "duckduckgo"
                    }
                },
                timeout=300
            )
            
            if resp.status_code != 200:
                try:
                    error_data = resp.json()
                    return f"❌ Research failed: {error_data.get('detail', 'Unknown error')}"
                except:
                    return f"❌ Research failed: HTTP {resp.status_code}"
            
            # For LangGraph API, the response is the final result
            result_data = resp.json()
            
            # Try to extract research results from the LangGraph response
            if isinstance(result_data, dict):
                # Look for common result fields
                research_result = result_data.get("research_result", result_data)
                
                # Format the result
                return self._format_langgraph_result(research_result, query, thread_id)
            
            return f"✅ Research completed. Result: {str(result_data)}"
            
        except requests.exceptions.ConnectionError:
            return "❌ Cannot connect to research service. Please check if the backend is running."
        except requests.exceptions.Timeout:
            return "❌ Research service timed out. Please try again."
        except Exception as e:
            return f"❌ Unexpected error: {str(e)}"
    
    def _format_langgraph_result(self, result: dict, query: str, thread_id: str) -> str:
        """Format LangGraph research results"""
        output = []
        
        title = result.get('title', f'Research Results: {query}')
        output.append(f"# {title}")
        
        # Handle different possible response structures
        if 'final_report' in result:
            output.append(f"\n## Research Report\n{result['final_report']}")
        elif 'report' in result:
            output.append(f"\n## Research Report\n{result['report']}")
        elif 'content' in result:
            content = result['content']
            if len(content) > 2000:
                content = content[:2000] + "\n\n[Content truncated for brevity...]"
            output.append(f"\n## Details\n{content}")
        
        # Extract sources if available
        sources = result.get('sources', [])
        if sources:
            output.append("\n## Sources")
            for i, src in enumerate(sources[:5], 1):
                if isinstance(src, dict):
                    title = src.get('title', 'Untitled')
                    url = src.get('url', '#')
                    output.append(f"{i}. [{title}]({url})")
                else:
                    output.append(f"{i}. {str(src)}")
        
        output.append(f"\n## Research Info")
        output.append(f"- Thread ID: {thread_id}")
        output.append(f"- Query: {query}")
        output.append(f"- Status: ✅ Completed")
        
        return "\n".join(output)
    
    def _format_result(self, result: dict, query: str) -> str:
        """Format successful research results"""
        output = []
        
        title = result.get('title', f'Research Results: {query}')
        output.append(f"# {title}")
        
        summary = result.get('summary', '')
        if summary:
            output.append(f"\n## Summary\n{summary}")
        
        content = result.get('content', '')
        if content:
            # Limit content length
            if len(content) > 2000:
                content = content[:2000] + "\n\n[Content truncated for brevity...]"
            output.append(f"\n## Details\n{content}")
        
        sources = result.get('sources', [])
        if sources:
            output.append("\n## Sources")
            for i, src in enumerate(sources[:5], 1):
                title = src.get('title', 'Untitled')
                url = src.get('url', '#')
                output.append(f"{i}. [{title}]({url})")
        
        metadata = result.get('metadata', {})
        if metadata:
            output.append(f"\n## Research Stats")
            output.append(f"- Search API: {metadata.get('search_api', 'N/A')}")
            output.append(f"- Research loops: {metadata.get('max_loops', 'N/A')}")
            output.append(f"- Sources analyzed: {metadata.get('sources_analyzed', 'N/A')}")
        
        return "\n".join(output)
    
    def _create_fallback_result(self, query: str, session_id: str) -> str:
        """Create a fallback result when the API result endpoint fails"""
        return f"""# Research Results: {query}

## Summary
Research session completed successfully (Session: {session_id}).

## Status
✅ The research has been completed, but detailed results are currently unavailable due to a temporary API issue.

## Recommendation
The research service processed your query "{query}" successfully. You can try running the research again, or contact support if the issue persists.

## Technical Details
- Session ID: {session_id}
- Status: Completed
- Issue: Result retrieval temporarily unavailable

*Note: This is a simplified response due to a backend API issue. The research was completed successfully.*"""