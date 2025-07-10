# Open-WebUI Integration Guide

## Overview

Open-WebUI is integrated with the Deep Researcher service to provide AI-powered web research capabilities directly within the chat interface. This integration uses Open-WebUI's Tools system to enable seamless research functionality.

## Architecture

```
User → Open-WebUI → Research Tool → Deep Researcher (LangGraph) → Web Search
                                           ↓
                                        Ollama LLM
```

## Enabling Deep Researcher in Open-WebUI

### Prerequisites

1. Ensure all services are running:
   ```bash
   docker-compose up -d
   ```

2. Verify Deep Researcher is healthy:
   ```bash
   curl http://localhost:${LOCAL_DEEP_RESEARCHER_PORT}/docs
   ```

3. Ensure Ollama has the required model:
   ```bash
   docker-compose exec ollama ollama pull qwen3:latest
   # Or use an alternative model and update the database
   ```

### Step-by-Step Setup

#### 1. Access Open-WebUI Admin Interface

1. Navigate to Open-WebUI: `http://localhost:${OPEN_WEB_UI_PORT}`
2. Log in with admin credentials
3. Go to **Admin Panel** → **Tools**

#### 2. Import Research Tools

The research tools are automatically mounted from the host filesystem. You have two tools available:

1. **Research Assistant** (`research_tool.py`)
   - Basic research functionality
   - Synchronous results display
   - Best for quick research queries

2. **Research Assistant (Enhanced)** (`research_streaming_tool.py`)
   - Progressive status updates
   - Real-time research progress
   - Best for detailed research tasks

**Import Method (Copy/Paste):**
Since Open-WebUI's file browser shows the container filesystem, use the copy/paste method:

1. On your host machine, copy the content of the tool file:
   ```bash
   # For basic research tool
   cat open-webui/tools/research_tool.py
   
   # For enhanced research tool  
   cat open-webui/tools/research_streaming_tool.py
   ```

2. In Open-WebUI admin interface:
   - Go to **Tools** → **Create New Tool**
   - Paste the entire file content
   - Click **"Create Tool"**

**Alternative (if file browser works):**
- Click **"Import Tool"** 
- Navigate to `/app/backend/data/tools/` (container path)
- Select the desired `.py` file

#### 3. Configure Tool Settings

After importing, configure the tool by clicking on its settings (gear icon):

**Default Configuration** (Usually no changes needed):
- `researcher_url`: `http://local-deep-researcher:2024` (auto-configured)
- `timeout`: 300 seconds
- `enable_tool`: true

**Note**: The tools are pre-configured to use the correct Deep Researcher URL. You typically don't need to modify these settings.

#### 4. Enable Tools for Models

1. Go to **Admin Panel** → **Models**
2. Select the model you want to use (e.g., your Ollama model)
3. In the **Tools** section, enable:
   - ✅ Research Assistant
   - ✅ Research Assistant (Enhanced) (optional)
4. Save the model configuration

#### 5. Test the Integration

1. Start a new chat with the model that has research tools enabled
2. Try these example queries:
   - "Research the latest developments in AI"
   - "What are the current trends in renewable energy?"
   - "Find information about quantum computing applications"

The tool will automatically activate when it detects research-related queries.

### Do You Need to Restart Open-WebUI?

**No**, you don't need to restart Open-WebUI when:
- Importing new tools through the admin interface
- Enabling/disabling tools for models
- Changing tool configurations (Valves)

**Yes**, you need to restart Open-WebUI when:
- Modifying the tool Python files directly on disk
- Changing Docker volume mounts
- Updating environment variables

To restart if needed:
```bash
docker-compose restart open-web-ui
```

## How It Works

1. **Query Detection**: When you ask a research question, Open-WebUI detects it needs to use the research tool
2. **Thread Creation**: The tool creates a new thread in the Deep Researcher LangGraph API
3. **Research Execution**: Deep Researcher performs web searches and analysis using the configured LLM with the correct `research_topic` input format
4. **Result Formatting**: Results are formatted and displayed in the chat interface

### Recent Fixes
- **Input Format**: Fixed tools to use `research_topic` input field (required by Deep Researcher) instead of `query`
- **State Management**: Removed conflicting configuration parameters that caused thread state issues
- **Thread Isolation**: Each research session now properly creates isolated threads

## Troubleshooting

### Tools Not Showing Up

1. Check if tools are mounted:
   ```bash
   docker-compose exec open-web-ui ls -la /app/backend/data/tools/
   ```

2. Verify Deep Researcher connectivity:
   ```bash
   docker-compose exec open-web-ui curl http://local-deep-researcher:2024/docs
   ```

### Research Failing

1. Check Deep Researcher logs:
   ```bash
   docker-compose logs local-deep-researcher --tail=50
   ```

2. Verify Ollama model is available:
   ```bash
   docker-compose exec ollama ollama list
   ```

3. Check if the model name in the database matches:
   ```sql
   -- Connect to database and check active LLM
   SELECT name, provider FROM llms WHERE active = true AND content = true;
   ```

### Model Not Found Error

If you see "model not found" errors:

1. Pull the required model:
   ```bash
   docker-compose exec ollama ollama pull qwen3:latest
   ```

2. Or update the database to use an available model:
   ```sql
   UPDATE llms SET active = true WHERE name = 'your-available-model' AND provider = 'ollama';
   UPDATE llms SET active = false WHERE name != 'your-available-model';
   ```

## Advanced Configuration

### Using Different LLMs

The Deep Researcher service dynamically selects the LLM from the database. To change it:

1. Connect to Supabase database
2. Update the `llms` table to activate your preferred model
3. Ensure the model is available in Ollama

### Custom Search Engines

Currently supports:
- DuckDuckGo (default)
- Additional engines can be configured in the Deep Researcher service

### Performance Tuning

- Adjust `max_loops` in the tool code for search depth
- Modify `timeout` in tool settings for longer research
- Configure `poll_interval` for status update frequency

## Security Considerations

- Research tools only have access to public web content
- All requests are routed through the backend service
- No direct internet access from Open-WebUI container
- Results are sanitized before display

## Development

To modify the research tools:

1. Edit files in `open-webui/tools/`
2. Restart Open-WebUI: `docker-compose restart open-web-ui`
3. Re-import the tool in the admin interface
4. Test thoroughly before deployment

For more details on tool development, see the main README section 7.3.5.