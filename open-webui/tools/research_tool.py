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
        backend_url: str = Field(
            default="http://backend:8000",
            description="Backend service URL"
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
            # Start research session
            resp = requests.post(
                f"{self.valves.backend_url}/research/start",
                json={
                    "query": query,
                    "max_loops": 3,
                    "search_api": "duckduckgo"
                },
                timeout=30
            )
            
            if resp.status_code != 200:
                try:
                    error_data = resp.json()
                    return f"❌ Research failed: {error_data.get('detail', 'Unknown error')}"
                except:
                    return f"❌ Research failed: HTTP {resp.status_code}"
            
            data = resp.json()
            session_id = data.get("session_id")
            
            if not session_id:
                return "❌ Failed to start research session."
            
            # Poll for completion
            start_time = time.time()
            while time.time() - start_time < self.valves.timeout:
                # Check status
                status_resp = requests.get(
                    f"{self.valves.backend_url}/research/{session_id}/status",
                    timeout=10
                )
                
                if status_resp.status_code != 200:
                    return f"❌ Failed to check research status: HTTP {status_resp.status_code}"
                
                status = status_resp.json()
                current_status = status.get("status", "unknown")
                
                if current_status == "completed":
                    # Try to get results, but handle the 500 error gracefully
                    try:
                        result_resp = requests.get(
                            f"{self.valves.backend_url}/research/{session_id}/result",
                            timeout=30
                        )
                        
                        if result_resp.status_code == 200:
                            result = result_resp.json()
                            return self._format_result(result, query)
                        else:
                            # Fallback to a simplified result when API fails
                            return self._create_fallback_result(query, session_id)
                            
                    except Exception as e:
                        # Fallback when result endpoint fails
                        return self._create_fallback_result(query, session_id)
                
                elif current_status in ["failed", "cancelled"]:
                    error_msg = status.get("error_message", "Unknown error")
                    return f"❌ Research {current_status}: {error_msg}"
                
                # Wait before next check
                time.sleep(5)
            
            return f"⏱️ Research timed out after {self.valves.timeout} seconds. Try a simpler query."
            
        except requests.exceptions.ConnectionError:
            return "❌ Cannot connect to research service. Please check if the backend is running."
        except requests.exceptions.Timeout:
            return "❌ Research service timed out. Please try again."
        except Exception as e:
            return f"❌ Unexpected error: {str(e)}"
    
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