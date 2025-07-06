"""
title: Research Status Checker
author: GenAI Vanilla Stack
description: Check the status of research sessions and list user research history
requirements: requests
version: 1.0.0
"""

import requests
import json
from typing import Dict, Any, List, Optional
from datetime import datetime


class ResearchStatusFunction:
    def __init__(self):
        self.backend_url = "http://backend:8000"

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get detailed status of a specific research session"""
        try:
            response = requests.get(
                f"{self.backend_url}/research/{session_id}/status",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": f"Failed to get session status: {str(e)}"}

    def get_session_logs(self, session_id: str) -> List[Dict[str, Any]]:
        """Get logs for a specific research session"""
        try:
            response = requests.get(
                f"{self.backend_url}/research/{session_id}/logs",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return [{"error": f"Failed to get session logs: {str(e)}"}]

    def list_user_sessions(self, user_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent research sessions for a user"""
        try:
            params = {"limit": limit}
            if user_id:
                params["user_id"] = user_id
                
            response = requests.get(
                f"{self.backend_url}/research/sessions",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return [{"error": f"Failed to list sessions: {str(e)}"}]

    def get_research_result_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of research results"""
        try:
            response = requests.get(
                f"{self.backend_url}/research/{session_id}/result",
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            # Create a summary
            summary = {
                "session_id": session_id,
                "title": result.get("title", "Unknown"),
                "summary": result.get("summary", "")[:200] + "..." if len(result.get("summary", "")) > 200 else result.get("summary", ""),
                "source_count": len(result.get("sources", [])),
                "content_length": len(result.get("content", "")),
                "created_at": result.get("created_at"),
                "metadata": result.get("metadata", {})
            }
            return summary
        except requests.RequestException as e:
            return {"error": f"Failed to get result summary: {str(e)}"}

    def format_session_history(self, sessions: List[Dict[str, Any]]) -> str:
        """Format session history for display"""
        if not sessions or (len(sessions) == 1 and "error" in sessions[0]):
            return "No research sessions found or error retrieving sessions."
        
        formatted_output = "## Recent Research Sessions\n\n"
        
        for session in sessions:
            if "error" in session:
                continue
                
            status = session.get("status", "unknown")
            query = session.get("query", "Unknown query")
            created_at = session.get("created_at", "Unknown time")
            session_id = session.get("session_id", "Unknown ID")
            
            # Format timestamp
            try:
                if created_at and created_at != "Unknown time":
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                else:
                    formatted_time = created_at
            except:
                formatted_time = created_at
            
            status_emoji = {
                "completed": "✅",
                "running": "🔄",
                "pending": "⏳",
                "failed": "❌",
                "cancelled": "🚫"
            }.get(status, "❓")
            
            formatted_output += f"### {status_emoji} {query}\n"
            formatted_output += f"- **Status**: {status.title()}\n"
            formatted_output += f"- **Session ID**: `{session_id}`\n"
            formatted_output += f"- **Started**: {formatted_time}\n"
            
            if session.get("completed_at"):
                try:
                    completed_dt = datetime.fromisoformat(session["completed_at"].replace('Z', '+00:00'))
                    formatted_completed = completed_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                    formatted_output += f"- **Completed**: {formatted_completed}\n"
                except:
                    formatted_output += f"- **Completed**: {session['completed_at']}\n"
            
            formatted_output += "\n"
        
        return formatted_output


def main(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function for checking research status and history
    
    Expected body format:
    {
        "action": "status|logs|history|result_summary",
        "session_id": "optional-session-id",  # required for status, logs, result_summary
        "user_id": "optional-user-id",        # optional for history
        "limit": 10                           # optional for history
    }
    """
    
    action = body.get("action", "").lower()
    session_id = body.get("session_id", "").strip()
    user_id = body.get("user_id")
    limit = body.get("limit", 10)
    
    # Initialize status function
    status_func = ResearchStatusFunction()
    
    try:
        if action == "status":
            if not session_id:
                return {
                    "success": False,
                    "error": "session_id is required for status action",
                    "usage": "Provide 'session_id' parameter to check research status"
                }
            
            status = status_func.get_session_status(session_id)
            if "error" in status:
                return {
                    "success": False,
                    "error": status["error"],
                    "session_id": session_id
                }
            
            return {
                "success": True,
                "action": "status",
                "session_id": session_id,
                "status": status
            }
        
        elif action == "logs":
            if not session_id:
                return {
                    "success": False,
                    "error": "session_id is required for logs action",
                    "usage": "Provide 'session_id' parameter to get research logs"
                }
            
            logs = status_func.get_session_logs(session_id)
            return {
                "success": True,
                "action": "logs",
                "session_id": session_id,
                "logs": logs,
                "log_count": len(logs)
            }
        
        elif action == "history":
            sessions = status_func.list_user_sessions(user_id, limit)
            formatted_history = status_func.format_session_history(sessions)
            
            return {
                "success": True,
                "action": "history",
                "user_id": user_id,
                "session_count": len(sessions),
                "sessions": sessions,
                "formatted_display": formatted_history
            }
        
        elif action == "result_summary":
            if not session_id:
                return {
                    "success": False,
                    "error": "session_id is required for result_summary action",
                    "usage": "Provide 'session_id' parameter to get result summary"
                }
            
            summary = status_func.get_research_result_summary(session_id)
            if "error" in summary:
                return {
                    "success": False,
                    "error": summary["error"],
                    "session_id": session_id
                }
            
            return {
                "success": True,
                "action": "result_summary",
                "session_id": session_id,
                "summary": summary
            }
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "usage": "Valid actions are: status, logs, history, result_summary",
                "available_actions": {
                    "status": "Get research session status (requires session_id)",
                    "logs": "Get research session logs (requires session_id)",
                    "history": "List recent research sessions (optional user_id, limit)",
                    "result_summary": "Get research result summary (requires session_id)"
                }
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "action": action
        }


# Example usage for testing
if __name__ == "__main__":
    # Test history
    test_body = {
        "action": "history",
        "limit": 5
    }
    
    result = main(test_body)
    print(json.dumps(result, indent=2))