# JupyterHub - GenAI Vanilla Stack

Interactive data science IDE with pre-configured access to all GenAI Vanilla Stack services.

## Overview

JupyterHub provides a Jupyter Lab environment with pre-installed libraries for:
- LLM integration (Ollama, LangChain, LlamaIndex)
- Vector databases (Weaviate)
- Graph databases (Neo4j)
- Relational databases (PostgreSQL via Supabase)
- Image generation (ComfyUI)
- Workflow automation (n8n)

## Quick Start

### Access JupyterHub

```bash
# Start the stack (JupyterHub enabled by default)
./start.sh

# Access at: http://localhost:63048
```

### Disable JupyterHub

```bash
./start.sh --jupyterhub-source disabled
```

## Configuration

### Environment Variables

Set in `.env` file:

```bash
JUPYTERHUB_SOURCE=container     # Options: container, disabled
JUPYTERHUB_IMAGE=jupyter/datascience-notebook:latest
JUPYTERHUB_PORT=63048
JUPYTERHUB_TOKEN=               # Optional: authentication token
```

### Authentication

- If `JUPYTERHUB_TOKEN` is not set, a token will be auto-generated on startup
- Check Docker logs to see the token: `docker logs genai-jupyterhub`
- Set a permanent token in `.env` to avoid regeneration

## Pre-installed Packages

### AI/ML Libraries
- `ollama` - Ollama Python client
- `langchain` - LLM application framework
- `llama-index` - Data framework for LLM applications
- `transformers` - Hugging Face transformers
- `sentence-transformers` - Sentence embeddings

### Database Clients
- `weaviate-client` - Weaviate vector database
- `neo4j` - Neo4j graph database
- `psycopg2-binary` - PostgreSQL
- `redis` - Redis client
- `supabase` - Supabase client
- `sqlalchemy` - SQL toolkit

### Data Science
- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `matplotlib` - Plotting
- `seaborn` - Statistical visualization
- `plotly` - Interactive visualizations
- `networkx` - Network analysis

## Sample Notebooks

| Notebook | Description |
|----------|-------------|
| `00_environment_check.ipynb` | Verify all service connections |
| `01_ollama_basics.ipynb` | LLM integration examples |
| `02_langchain_rag.ipynb` | RAG pipeline with Weaviate |
| `03_neo4j_graphs.ipynb` | Knowledge graph queries |
| `04_supabase_data.ipynb` | Database and storage operations |
| `05_comfyui_images.ipynb` | Image generation workflows |
| `06_n8n_workflows.ipynb` | Workflow automation |

## Service Integration

### Ollama (LLM)

```python
import os
from ollama import Client

client = Client(host=os.getenv("OLLAMA_BASE_URL"))
response = client.chat(model="llama3.2", messages=[
    {"role": "user", "content": "Hello!"}
])
print(response["message"]["content"])
```

### Weaviate (Vector DB)

```python
import os
import weaviate

client = weaviate.connect_to_custom(
    http_host=os.getenv("WEAVIATE_URL").replace("http://", "").split(":")[0],
    http_port=8080,
    http_secure=False
)
print(client.is_ready())
```

### Neo4j (Graph DB)

```python
import os
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

with driver.session() as session:
    result = session.run("MATCH (n) RETURN count(n) as count")
    print(result.single()["count"])
```

### PostgreSQL (Supabase)

```python
import os
from sqlalchemy import create_engine

engine = create_engine(os.getenv("DATABASE_URL"))
with engine.connect() as conn:
    result = conn.execute("SELECT version()")
    print(result.fetchone())
```

## Data Persistence

### Work Directory
- Location: `/home/jovyan/work`
- Persisted in: `genai-jupyterhub-data` Docker volume
- All notebooks and files in this directory persist across container restarts

### Sample Notebooks
- Location: `/home/jovyan/notebooks`
- Read-only mount from host: `./jupyterhub/notebooks`
- Copy to `work/` directory to modify

## Custom Package Installation

### Temporary (current session only)

```bash
!pip install package-name
```

### Permanent

1. Add package to `jupyterhub/requirements.txt`
2. Rebuild the container: `docker compose build jupyterhub`
3. Restart: `./stop.sh && ./start.sh`

## Troubleshooting

### Cannot connect to services

Check environment variables in a notebook:

```python
import os
print("Ollama:", os.getenv("OLLAMA_BASE_URL"))
print("Weaviate:", os.getenv("WEAVIATE_URL"))
print("Neo4j:", os.getenv("NEO4J_URI"))
```

### Token not working

1. Check logs: `docker logs genai-jupyterhub`
2. Find the token URL in logs
3. Or set `JUPYTERHUB_TOKEN` in `.env` and restart

### Port already in use

Change port in `.env`:

```bash
JUPYTERHUB_PORT=64048  # Use different port
```

### Out of memory

Increase Docker memory allocation:
- Docker Desktop → Settings → Resources → Memory
- Recommended: 8GB+ for data science workloads

## Advanced Configuration

### Multi-user Setup

For multi-user JupyterHub with authentication, create `jupyterhub_config.py`:

```python
# See: https://jupyterhub.readthedocs.io/
c.JupyterHub.authenticator_class = 'firstuseauthenticator.FirstUseAuthenticator'
```

### Custom Jupyter Extensions

Add to Dockerfile:

```dockerfile
RUN jupyter labextension install @jupyter-widgets/jupyterlab-manager
```

### GPU Access

If using GPU-enabled services:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

## Resources

- [Jupyter Lab Documentation](https://jupyterlab.readthedocs.io/)
- [JupyterHub Documentation](https://jupyterhub.readthedocs.io/)
- [GenAI Vanilla Stack Docs](../docs/README.md)

## Support

- GitHub Issues: [Report bugs](https://github.com/your-repo/issues)
- Documentation: [Full docs](../docs/README.md)
- Logs: `docker logs genai-jupyterhub`
