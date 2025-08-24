#!/usr/bin/env python3
import os
import json
import time
import sys

# Import psycopg2 with better error handling
try:
    import psycopg2
except ImportError as e:
    print(f"ERROR: Failed to import psycopg2: {e}")
    print("Please ensure psycopg2-binary is installed in the container")
    print("Run: uv pip install --system psycopg2-binary")
    sys.exit(1)


def wait_for_database():
    """Wait for database to be available"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        return False

    max_retries = 30
    retry_count = 0

    while retry_count < max_retries:
        try:
            conn = psycopg2.connect(database_url)
            conn.close()
            print("Database connection successful")
            return True
        except Exception as e:
            retry_count += 1
            print(
                f"Database connection attempt {retry_count}/{max_retries} failed: {e}"
            )
            time.sleep(2)

    print("ERROR: Could not connect to database after maximum retries")
    return False


def initialize_config():
    """Initialize Local Deep Researcher configuration from database"""

    # Wait for database to be available
    if not wait_for_database():
        sys.exit(1)

    database_url = os.getenv("DATABASE_URL")

    conn = None
    cursor = None

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Query for active content LLMs, prefer highest priority, then ollama
        cursor.execute("""
            SELECT provider, name FROM public.llms 
            WHERE active = true AND content > 0 
            ORDER BY content DESC, provider = 'ollama' DESC, name
            LIMIT 1
        """)

        result = cursor.fetchone()

        if result:
            provider, model_name = result
            print(f"Found active LLM: {provider}/{model_name}")

            # Create configuration for Local Deep Researcher
            config = {
                "llm_provider": provider,
                "local_llm": model_name,
                "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
                "search_api": os.getenv("SEARCH_API", "duckduckgo"),
                "max_web_research_loops": int(os.getenv("MAX_WEB_RESEARCH_LOOPS", "3")),
                "fetch_full_page": os.getenv("FETCH_FULL_PAGE", "false").lower()
                == "true",
            }

            # Ensure config directory exists
            os.makedirs("/app/config", exist_ok=True)

            # Write runtime configuration
            with open("/app/config/runtime_config.json", "w") as f:
                json.dump(config, f, indent=2)

            # Create .env file for Local Deep Researcher
            env_content = f"""LLM_PROVIDER={provider}
LOCAL_LLM={model_name}
OLLAMA_BASE_URL={config["ollama_base_url"]}
SEARCH_API={config["search_api"]}
MAX_WEB_RESEARCH_LOOPS={config["max_web_research_loops"]}
FETCH_FULL_PAGE={config["fetch_full_page"]}
DATABASE_URL={database_url}
"""

            with open("/app/.env", "w") as f:
                f.write(env_content)

            print("Configuration initialized successfully")
            print(f"Using LLM: {provider}/{model_name}")
            print(f"Ollama URL: {config['ollama_base_url']}")
            print(f"Search API: {config['search_api']}")

        else:
            print("WARNING: No active content LLMs found in database")
            print("Creating fallback configuration")

            # Fallback configuration
            fallback_config = {
                "llm_provider": "ollama",
                "local_llm": "llama3.2",
                "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
                "search_api": os.getenv("SEARCH_API", "duckduckgo"),
                "max_web_research_loops": int(os.getenv("MAX_WEB_RESEARCH_LOOPS", "3")),
                "fetch_full_page": False,
            }

            os.makedirs("/app/config", exist_ok=True)
            with open("/app/config/runtime_config.json", "w") as f:
                json.dump(fallback_config, f, indent=2)

            # Create fallback .env
            env_content = f"""LLM_PROVIDER=ollama
LOCAL_LLM=llama3.2
OLLAMA_BASE_URL={fallback_config["ollama_base_url"]}
SEARCH_API={fallback_config["search_api"]}
MAX_WEB_RESEARCH_LOOPS={fallback_config["max_web_research_loops"]}
FETCH_FULL_PAGE=false
DATABASE_URL={database_url}
"""

            with open("/app/.env", "w") as f:
                f.write(env_content)

    except Exception as e:
        print(f"ERROR initializing config: {e}")
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    initialize_config()
