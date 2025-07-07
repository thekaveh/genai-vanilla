"""
title: Research Assistant (Enhanced)
author: GenAI Vanilla Stack
author_url: https://github.com/vanilla-genai
description: Enhanced research tool with progress tracking and detailed results
required_open_webui_version: 0.4.4
requirements: requests
version: 1.0.0
license: MIT
"""

import time
import requests
from typing import Dict, Any
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
        poll_interval: float = Field(
            default=3.0,
            description="Status check interval in seconds"
        )
        show_progress: bool = Field(
            default=True,
            description="Show research progress updates"
        )

    def __init__(self):
        self.valves = self.Valves()

    def research_with_progress(
        self, query: str, __user__: Dict[str, Any] = None
    ) -> str:
        """
        Enhanced research with progress tracking and detailed results
        """
        if not query.strip():
            return "❌ Please provide a research query"

        if not self.valves.show_progress:
            return "❌ Research tool is currently disabled"

        # Start research session
        try:
            result_parts = []
            result_parts.append(f"🚀 **Starting research:** {query}\n")
            
            session_id = self._start_research_session(query)
            if not session_id:
                return "❌ Failed to start research session"

            result_parts.append(f"📋 **Research session created:** `{session_id}`\n")

            # Track progress and get final results
            final_result = self._track_research_progress(session_id, query)
            result_parts.append(final_result)
            
            return "\n".join(result_parts)

        except Exception as e:
            return f"❌ **Research failed:** {str(e)}"

    def _start_research_session(self, query: str) -> str:
        """Start a research session and return session ID"""
        try:
            response = requests.post(
                f"{self.valves.backend_url}/research/start",
                json={
                    "query": query,
                    "max_loops": 3,
                    "search_api": "duckduckgo"
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return None
                
            data = response.json()
            return data.get("session_id")
            
        except Exception:
            return None

    def _track_research_progress(self, session_id: str, query: str) -> str:
        """Track research progress and return final results"""
        start_time = time.time()
        last_status = None
        progress_log = []
        
        step_messages = {
            "pending": "⏳ **Queuing research...**",
            "running": "🔍 **Research in progress...**", 
            "completed": "✅ **Research completed!**",
            "failed": "❌ **Research failed**",
            "cancelled": "🛑 **Research cancelled**"
        }
        
        try:
            while time.time() - start_time < self.valves.timeout:
                # Get current status
                status_response = requests.get(
                    f"{self.valves.backend_url}/research/{session_id}/status",
                    timeout=10
                )
                
                if status_response.status_code != 200:
                    return f"❌ **Status check failed:** HTTP {status_response.status_code}"

                status_data = status_response.json()
                current_status = status_data.get("status", "unknown")
                
                # Log status changes
                if current_status != last_status:
                    message = step_messages.get(current_status, f"📊 **Status:** {current_status}")
                    progress_log.append(message)
                    last_status = current_status

                # Check if completed
                if current_status == "completed":
                    progress_log.append("📄 **Retrieving research results...**")
                    
                    # Get final results
                    final_result = self._get_final_results(session_id, query)
                    progress_log.append(final_result)
                    
                    return "\n\n".join(progress_log)
                    
                elif current_status in ["failed", "cancelled"]:
                    error_msg = status_data.get("error_message", "Unknown error")
                    progress_log.append(f"**Error:** {error_msg}")
                    return "\n\n".join(progress_log)

                # Wait before next status check
                time.sleep(self.valves.poll_interval)

            # Timeout
            progress_log.append(f"⏱️ **Research timed out** after {self.valves.timeout} seconds")
            return "\n\n".join(progress_log)
            
        except Exception as e:
            return f"❌ **Progress tracking failed:** {str(e)}"

    def _get_final_results(self, session_id: str, query: str) -> str:
        """Get the final research results"""
        try:
            result_response = requests.get(
                f"{self.valves.backend_url}/research/{session_id}/result",
                timeout=30
            )
            
            if result_response.status_code == 200:
                result = result_response.json()
                
                # Format results nicely
                result_parts = []
                result_parts.append(f"# {result.get('title', f'Research Results: {query}')}")
                
                summary = result.get('summary', '')
                if summary:
                    result_parts.append(f"## Summary\n{summary}")
                
                content = result.get('content', '')
                if content:
                    result_parts.append(f"## Detailed Findings\n{content}")
                
                sources = result.get('sources', [])
                if sources:
                    result_parts.append("## Sources")
                    source_list = []
                    for i, source in enumerate(sources[:10], 1):
                        title = source.get('title', 'Untitled')
                        url = source.get('url', '#')
                        source_list.append(f"{i}. [{title}]({url})")
                    
                    result_parts.append("\n".join(source_list))
                    
                    if len(sources) > 10:
                        result_parts.append(f"*Plus {len(sources) - 10} more sources...*")
                
                metadata = result.get('metadata', {})
                if metadata:
                    stats = []
                    stats.append("## Research Statistics")
                    stats.append(f"- **Search API:** {metadata.get('search_api', 'N/A')}")
                    stats.append(f"- **Research loops:** {metadata.get('max_loops', 'N/A')}")
                    stats.append(f"- **Sources analyzed:** {metadata.get('sources_analyzed', 'N/A')}")
                    stats.append(f"- **Processing time:** {metadata.get('processing_time_seconds', 'N/A')}s")
                    result_parts.append("\n".join(stats))
                
                result_parts.append(f"✅ **Research completed successfully!**")
                result_parts.append(f"🔗 **Session ID:** `{session_id}`")
                
                return "\n\n".join(result_parts)
                
            else:
                # Fallback when result endpoint fails
                return self._create_fallback_result(query, session_id)
                
        except Exception as e:
            return f"❌ **Failed to retrieve results:** {str(e)}\n\n{self._create_fallback_result(query, session_id)}"

    def _create_fallback_result(self, query: str, session_id: str) -> str:
        """Create a fallback result when API fails"""
        return f"""## Research Completed

✅ Research session for "{query}" completed successfully.

**Session ID:** `{session_id}`

*Note: Full results are temporarily unavailable due to an API issue, but the research was completed successfully.*"""