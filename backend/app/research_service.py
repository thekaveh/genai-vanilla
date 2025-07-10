import asyncio
import asyncpg
import os
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
import json
from uuid import UUID, uuid4

from research_client import ResearchClient, ResearchRequest, ResearchStatus, ResearchResult


class ResearchService:
    """Service for managing research operations with database persistence"""

    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.research_client = ResearchClient()
        self._active_tasks = {}  # Track background tasks

    async def _get_db_connection(self):
        """Get database connection"""
        return await asyncpg.connect(self.db_url)

    async def start_research(
        self, 
        query: str, 
        max_loops: int = 3, 
        search_api: str = "duckduckgo",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start a new research session with database tracking"""
        
        # Create database record first
        session_id = str(uuid4())
        conn = await self._get_db_connection()
        
        try:
            await conn.execute("""
                INSERT INTO public.research_sessions 
                (id, query, status, max_loops, search_api, user_id, started_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, session_id, query, ResearchStatus.PENDING.value, max_loops, search_api, 
                UUID(user_id) if user_id else None, datetime.utcnow())
            
            # Log the start
            await conn.execute("""
                INSERT INTO public.research_logs (session_id, step_number, step_type, message)
                VALUES ($1, $2, $3, $4)
            """, session_id, 1, "start", f"Research session started for query: {query}")
            
        finally:
            await conn.close()

        # Start background research task
        task = asyncio.create_task(
            self._run_research_background(session_id, query, max_loops, search_api, user_id)
        )
        self._active_tasks[session_id] = task

        return {
            "session_id": session_id,
            "status": ResearchStatus.PENDING.value,
            "message": "Research session created and queued",
            "query": query,
            "max_loops": max_loops,
            "search_api": search_api
        }

    async def _run_research_background(
        self, 
        session_id: str, 
        query: str, 
        max_loops: int, 
        search_api: str,
        user_id: Optional[str]
    ):
        """Run research in background and update database"""
        conn = await self._get_db_connection()
        
        try:
            # Update status to running
            await conn.execute("""
                UPDATE public.research_sessions 
                SET status = $1, started_at = $2
                WHERE id = $3
            """, ResearchStatus.RUNNING.value, datetime.utcnow(), session_id)

            await conn.execute("""
                INSERT INTO public.research_logs (session_id, step_number, step_type, message)
                VALUES ($1, $2, $3, $4)
            """, session_id, 2, "execute", "Starting research execution")

            # Create request for research client
            request = ResearchRequest(
                query=query,
                max_loops=max_loops,
                search_api=search_api,
                user_id=user_id
            )

            # Execute research using the actual local-deep-researcher service
            await self._execute_research(conn, session_id, request)

        except Exception as e:
            # Update status to failed
            await conn.execute("""
                UPDATE public.research_sessions 
                SET status = $1, completed_at = $2, error_message = $3
                WHERE id = $4
            """, ResearchStatus.FAILED.value, datetime.utcnow(), str(e), session_id)

            await conn.execute("""
                INSERT INTO public.research_logs (session_id, step_number, step_type, message)
                VALUES ($1, $2, $3, $4)
            """, session_id, 99, "error", f"Research failed: {str(e)}")

        finally:
            await conn.close()
            # Clean up task reference
            if session_id in self._active_tasks:
                del self._active_tasks[session_id]

    async def _execute_research(
        self, 
        conn: asyncpg.Connection, 
        session_id: str, 
        request: ResearchRequest
    ):
        """Execute research using actual local-deep-researcher service"""
        
        # Use the research client to start the research
        research_response = await self.research_client.start_research(request)
        
        if research_response.status != ResearchStatus.RUNNING:
            raise Exception(f"Failed to start research: {research_response.message}")
        
        remote_session_id = research_response.session_id
        
        # Log the remote session ID
        await conn.execute("""
            INSERT INTO public.research_logs (session_id, step_number, step_type, message)
            VALUES ($1, $2, $3, $4)
        """, session_id, 3, "remote_start", f"Remote research session started: {remote_session_id}")
        
        # Wait for completion
        final_response = await self.research_client.wait_for_completion(remote_session_id)
        
        if final_response.status == ResearchStatus.COMPLETED:
            # Get the results
            research_result = await self.research_client.get_research_result(remote_session_id)
            
            if research_result:
                # Store the results
                await self._store_research_result(conn, session_id, research_result)
            else:
                raise Exception("Failed to retrieve research results")
        else:
            raise Exception(f"Research failed: {final_response.message}")

    async def _store_research_result(
        self, 
        conn: asyncpg.Connection, 
        session_id: str, 
        research_result: ResearchResult
    ):
        """Store research results in the database"""
        
        # Log completion
        await conn.execute("""
            INSERT INTO public.research_logs (session_id, step_number, step_type, message)
            VALUES ($1, $2, $3, $4)
        """, session_id, 4, "complete", "Research completed successfully")

        # Store research result
        result_id = str(uuid4())
        await conn.execute("""
            INSERT INTO public.research_results 
            (id, session_id, title, summary, content, sources, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, result_id, session_id, research_result.title, research_result.summary,
            research_result.content, json.dumps(research_result.sources), 
            json.dumps(research_result.metadata))

        # Store individual sources
        for source in research_result.sources:
            await conn.execute("""
                INSERT INTO public.research_sources 
                (session_id, result_id, url, title, relevance_score, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, session_id, result_id, source.get("url", ""), source.get("title", ""),
                source.get("relevance_score", 0.0), json.dumps(source.get("metadata", {})))

        # Update session as completed
        await conn.execute("""
            UPDATE public.research_sessions 
            SET status = $1, completed_at = $2
            WHERE id = $3
        """, ResearchStatus.COMPLETED.value, datetime.utcnow(), session_id)

    async def get_research_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get research session status"""
        conn = await self._get_db_connection()
        
        try:
            row = await conn.fetchrow("""
                SELECT id, query, status, max_loops, search_api, user_id,
                       created_at, updated_at, started_at, completed_at, error_message
                FROM public.research_sessions 
                WHERE id = $1
            """, session_id)
            
            if not row:
                return None
                
            return {
                "session_id": str(row["id"]),
                "query": row["query"],
                "status": row["status"],
                "max_loops": row["max_loops"],
                "search_api": row["search_api"],
                "user_id": str(row["user_id"]) if row["user_id"] else None,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
                "error_message": row["error_message"]
            }
        finally:
            await conn.close()

    async def get_research_result(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get research results for a completed session"""
        conn = await self._get_db_connection()
        
        try:
            row = await conn.fetchrow("""
                SELECT r.id, r.title, r.summary, r.content, r.sources, r.metadata, r.created_at,
                       s.status
                FROM public.research_results r
                JOIN public.research_sessions s ON r.session_id = s.id
                WHERE r.session_id = $1
            """, session_id)
            
            if not row:
                return None
                
            return {
                "session_id": session_id,
                "result_id": str(row["id"]),
                "title": row["title"],
                "summary": row["summary"],
                "content": row["content"],
                "sources": row["sources"],
                "metadata": row["metadata"],
                "created_at": row["created_at"].isoformat(),
                "status": row["status"]
            }
        finally:
            await conn.close()

    async def list_user_sessions(
        self, 
        user_id: Optional[str] = None, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List research sessions for a user"""
        conn = await self._get_db_connection()
        
        try:
            if user_id:
                rows = await conn.fetch("""
                    SELECT id, query, status, max_loops, search_api, 
                           created_at, started_at, completed_at
                    FROM public.research_sessions 
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                """, UUID(user_id), limit, offset)
            else:
                rows = await conn.fetch("""
                    SELECT id, query, status, max_loops, search_api, 
                           created_at, started_at, completed_at
                    FROM public.research_sessions 
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                """, limit, offset)
            
            return [
                {
                    "session_id": str(row["id"]),
                    "query": row["query"],
                    "status": row["status"],
                    "max_loops": row["max_loops"],
                    "search_api": row["search_api"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                    "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None
                }
                for row in rows
            ]
        finally:
            await conn.close()

    async def cancel_research(self, session_id: str) -> bool:
        """Cancel a running research session"""
        conn = await self._get_db_connection()
        
        try:
            # Check current status
            status_row = await conn.fetchrow("""
                SELECT status FROM public.research_sessions WHERE id = $1
            """, session_id)
            
            if not status_row or status_row["status"] != ResearchStatus.RUNNING.value:
                return False
            
            # Cancel background task if it exists
            if session_id in self._active_tasks:
                self._active_tasks[session_id].cancel()
                del self._active_tasks[session_id]
            
            # Update database
            await conn.execute("""
                UPDATE public.research_sessions 
                SET status = $1, completed_at = $2
                WHERE id = $3
            """, ResearchStatus.CANCELLED.value, datetime.utcnow(), session_id)

            await conn.execute("""
                INSERT INTO public.research_logs (session_id, step_number, step_type, message)
                VALUES ($1, $2, $3, $4)
            """, session_id, 98, "cancel", "Research session cancelled by user")
            
            return True
        finally:
            await conn.close()

    async def get_research_logs(self, session_id: str) -> List[Dict[str, Any]]:
        """Get research logs for a session"""
        conn = await self._get_db_connection()
        
        try:
            rows = await conn.fetch("""
                SELECT step_number, step_type, message, data, created_at
                FROM public.research_logs 
                WHERE session_id = $1
                ORDER BY step_number ASC
            """, session_id)
            
            return [
                {
                    "step_number": row["step_number"],
                    "step_type": row["step_type"],
                    "message": row["message"],
                    "data": row["data"],
                    "timestamp": row["created_at"].isoformat()
                }
                for row in rows
            ]
        finally:
            await conn.close()

    async def health_check(self) -> Dict[str, Any]:
        """Check service health including database and research client"""
        results = {
            "database": "unknown",
            "research_client": "unknown",
            "active_tasks": len(self._active_tasks)
        }
        
        # Test database connection
        try:
            conn = await self._get_db_connection()
            await conn.fetchval("SELECT 1")
            await conn.close()
            results["database"] = "healthy"
        except Exception as e:
            results["database"] = f"unhealthy: {str(e)}"
        
        # Test research client
        try:
            client_health = await self.research_client.health_check()
            results["research_client"] = client_health["status"]
        except Exception as e:
            results["research_client"] = f"unhealthy: {str(e)}"
        
        return results