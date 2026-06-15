#!/usr/bin/env python3
import os
import json
import time
import sys

# Force line-buffered stdout so init-container progress prints reach
# `docker logs` immediately — mirrors the open-webui/init and
# lightrag/init scripts. Without this, the script's 16 print sites
# would be block-buffered and a crash mid-run would silently drop the
# progress trail.
sys.stdout.reconfigure(line_buffering=True)

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

        # All LLM access goes through the LiteLLM gateway. litellm-init
        # registers cloud rows under their BARE catalog names (openrouter
        # names already carry their own prefix) and only Ollama rows get
        # the dual "ollama/{name}" alias — same convention as the
        # backend's memory_service. Prefixing every provider produced
        # ids LiteLLM never serves ("openai/gpt-…" 400s;
        # "openrouter/openrouter/…" double-prefixes).
        litellm_base_url = os.getenv("LITELLM_BASE_URL", "http://litellm:4000")
        litellm_api_key = os.getenv("LITELLM_API_KEY", "")

        if result:
            provider, model_name = result
            if provider == "ollama":
                litellm_model = f"ollama/{model_name}"
            else:
                litellm_model = model_name
            print(f"Found active LLM: {litellm_model}")

            # Create configuration for Local Deep Researcher.
            # llm_provider="openai" tells LangGraph/LangChain to use the
            # OpenAI-compatible client, which we point at LiteLLM.
            config = {
                "llm_provider": "openai",
                "local_llm": litellm_model,
                "litellm_base_url": litellm_base_url,
                "search_api": os.getenv("SEARCH_API", "duckduckgo"),
                "max_web_research_loops": int(os.getenv("MAX_WEB_RESEARCH_LOOPS", "3")),
                "fetch_full_page": os.getenv("FETCH_FULL_PAGE", "false").lower()
                == "true",
            }

            os.makedirs("/app/config", exist_ok=True)
            with open("/app/config/runtime_config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

            # Create .env file for Local Deep Researcher
            env_content = f"""LLM_PROVIDER=openai
LOCAL_LLM={litellm_model}
OPENAI_API_BASE={litellm_base_url}/v1
OPENAI_API_KEY={litellm_api_key}
LITELLM_BASE_URL={litellm_base_url}
LITELLM_API_KEY={litellm_api_key}
SEARCH_API={config["search_api"]}
MAX_WEB_RESEARCH_LOOPS={config["max_web_research_loops"]}
FETCH_FULL_PAGE={config["fetch_full_page"]}
DATABASE_URL={database_url}
"""

            with open("/app/.env", "w", encoding="utf-8") as f:
                f.write(env_content)

            print("Configuration initialized successfully")
            print(f"Using LLM: {litellm_model}")
            print(f"LiteLLM URL: {litellm_base_url}")
            print(f"Search API: {config['search_api']}")

        else:
            # No active content LLM in public.llms. Fall through to
            # LITELLM_DEFAULT_MODEL if the operator set one (matches the
            # backend's memory_service resolution order); otherwise exit
            # non-zero. The previous hardcoded ``ollama/qwen3.6:latest``
            # fallback was unroutable in cloud-only setups (Ollama
            # disabled) AND wasn't a real Ollama model id — every
            # research call 400'd through LiteLLM with a silent
            # misconfiguration. Loud failure here surfaces the problem
            # at compose-up time, before the first /research request.
            default_model = os.getenv("LITELLM_DEFAULT_MODEL", "").strip()
            if not default_model:
                print(
                    "ERROR: No active content row in public.llms and "
                    "LITELLM_DEFAULT_MODEL is unset. Activate at least one "
                    "row with content > 0 in public.llms (via the wizard or "
                    "by editing the catalog), or set LITELLM_DEFAULT_MODEL "
                    "to a model id LiteLLM serves."
                )
                sys.exit(1)

            print(f"No active content LLM in DB; using LITELLM_DEFAULT_MODEL={default_model}")
            fallback_config = {
                "llm_provider": "openai",
                "local_llm": default_model,
                "litellm_base_url": litellm_base_url,
                "search_api": os.getenv("SEARCH_API", "duckduckgo"),
                "max_web_research_loops": int(os.getenv("MAX_WEB_RESEARCH_LOOPS", "3")),
                "fetch_full_page": False,
            }

            os.makedirs("/app/config", exist_ok=True)
            with open("/app/config/runtime_config.json", "w", encoding="utf-8") as f:
                json.dump(fallback_config, f, indent=2)

            env_content = f"""LLM_PROVIDER=openai
LOCAL_LLM={default_model}
OPENAI_API_BASE={litellm_base_url}/v1
OPENAI_API_KEY={litellm_api_key}
LITELLM_BASE_URL={litellm_base_url}
LITELLM_API_KEY={litellm_api_key}
SEARCH_API={fallback_config["search_api"]}
MAX_WEB_RESEARCH_LOOPS={fallback_config["max_web_research_loops"]}
FETCH_FULL_PAGE=false
DATABASE_URL={database_url}
"""

            with open("/app/.env", "w", encoding="utf-8") as f:
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
