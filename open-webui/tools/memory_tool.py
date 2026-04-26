"""
title: Memory Assistant
author: GenAI Vanilla Stack
author_url: https://github.com/vanilla-genai
description: Persistent memory - remembers facts about users across conversations
required_open_webui_version: 0.4.4
requirements: requests
version: 1.0.0
license: MIT
"""

import requests
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        backend_url: str = Field(
            default="http://backend:8000",
            description="Backend API URL"
        )
        enable_tool: bool = Field(
            default=True,
            description="Enable this memory tool"
        )
        max_recall_results: int = Field(
            default=10,
            description="Maximum number of memories to recall"
        )
        timeout: int = Field(
            default=120,
            description="Request timeout in seconds"
        )

    def __init__(self):
        self.valves = self.Valves()

    def remember(self, conversation: str, __user__: dict = {}) -> str:
        """
        Extract and store memories from a conversation. Use this when the user
        asks you to remember something or when important facts are shared.

        :param conversation: The conversation text to extract memories from
        :return: Extracted memory facts
        """
        if not self.valves.enable_tool:
            return str("Memory tool is currently disabled.")

        if not conversation:
            return str("Please provide conversation text to extract memories from.")

        user_id = __user__.get("id", "")
        if not user_id:
            return str("Error: User ID not available. Please ensure you are logged in.")

        try:
            messages = [{"role": "user", "content": conversation}]

            response = requests.post(
                f"{self.valves.backend_url}/memory/extract",
                json={
                    "user_id": user_id,
                    "messages": messages,
                    "namespace": "default",
                },
                timeout=self.valves.timeout,
            )
            response.raise_for_status()
            result = response.json()

            facts = result.get("facts", [])
            if not facts:
                return str("No new facts were extracted from the conversation.")

            output_lines = [f"Extracted {len(facts)} memory fact(s):"]
            for fact in facts:
                output_lines.append(
                    f"- [{fact.get('fact_type', 'observation')}] "
                    f"{fact.get('content', '')} "
                    f"(confidence: {fact.get('confidence', 0):.1%})"
                )

            return str("\n".join(output_lines))

        except requests.exceptions.ConnectionError:
            return str("Could not connect to the memory service. "
                       "Please check if the Backend is running.")
        except Exception as e:
            return str(f"Error extracting memories: {str(e)}")

    def recall(self, query: str, __user__: dict = {}) -> str:
        """
        Recall relevant memories for a given topic or question. Use this when
        the user asks what you remember about something.

        :param query: The topic or question to recall memories about
        :return: Relevant memory facts
        """
        if not self.valves.enable_tool:
            return str("Memory tool is currently disabled.")

        if not query:
            return str("Please provide a query to recall memories about.")

        user_id = __user__.get("id", "")
        if not user_id:
            return str("Error: User ID not available. Please ensure you are logged in.")

        try:
            response = requests.post(
                f"{self.valves.backend_url}/memory/recall",
                json={
                    "user_id": user_id,
                    "query": query,
                    "namespace": "default",
                    "limit": self.valves.max_recall_results,
                    "min_confidence": 0.5,
                },
                timeout=self.valves.timeout,
            )
            response.raise_for_status()
            result = response.json()

            memories = result.get("memories", [])
            summary = result.get("context_summary")

            if not memories:
                return str("No relevant memories found for this query.")

            output_lines = [f"Found {len(memories)} relevant memory(ies):"]
            for mem in memories:
                output_lines.append(
                    f"- [{mem.get('fact_type', 'observation')}] "
                    f"{mem.get('content', '')} "
                    f"(confidence: {mem.get('confidence', 0):.1%})"
                )

            if summary:
                output_lines.append(f"\nSummary: {summary}")

            return str("\n".join(output_lines))

        except requests.exceptions.ConnectionError:
            return str("Could not connect to the memory service. "
                       "Please check if the Backend is running.")
        except Exception as e:
            return str(f"Error recalling memories: {str(e)}")

    def forget(self, memory_id: str, __user__: dict = {}) -> str:
        """
        Delete a specific memory by its ID. Use this when the user wants
        to remove a stored memory.

        :param memory_id: The UUID of the memory to delete
        :return: Confirmation message
        """
        if not self.valves.enable_tool:
            return str("Memory tool is currently disabled.")

        if not memory_id:
            return str("Please provide a memory ID to delete.")

        try:
            response = requests.delete(
                f"{self.valves.backend_url}/memory/{memory_id}",
                timeout=self.valves.timeout,
            )
            response.raise_for_status()

            return str(f"Memory {memory_id} has been deleted successfully.")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return str(f"Memory {memory_id} not found.")
            return str(f"Error deleting memory: {str(e)}")
        except requests.exceptions.ConnectionError:
            return str("Could not connect to the memory service. "
                       "Please check if the Backend is running.")
        except Exception as e:
            return str(f"Error deleting memory: {str(e)}")

    def list_memories(self, __user__: dict = {}) -> str:
        """
        List all stored memories for the current user. Use this when the user
        wants to see everything that has been remembered about them.

        :return: List of all active memory facts
        """
        if not self.valves.enable_tool:
            return str("Memory tool is currently disabled.")

        user_id = __user__.get("id", "")
        if not user_id:
            return str("Error: User ID not available. Please ensure you are logged in.")

        try:
            response = requests.get(
                f"{self.valves.backend_url}/memory/user/{user_id}",
                params={"namespace": "default", "limit": 50},
                timeout=self.valves.timeout,
            )
            response.raise_for_status()
            result = response.json()

            memories = result.get("memories", [])
            total = result.get("total", 0)

            if not memories:
                return str("No memories stored yet.")

            output_lines = [f"You have {total} stored memory(ies):"]
            for mem in memories:
                output_lines.append(
                    f"- [{mem.get('fact_type', 'observation')}] "
                    f"{mem.get('content', '')} "
                    f"(id: {mem.get('id', 'N/A')[:8]}..., "
                    f"confidence: {mem.get('confidence', 0):.1%})"
                )

            return str("\n".join(output_lines))

        except requests.exceptions.ConnectionError:
            return str("Could not connect to the memory service. "
                       "Please check if the Backend is running.")
        except Exception as e:
            return str(f"Error listing memories: {str(e)}")
