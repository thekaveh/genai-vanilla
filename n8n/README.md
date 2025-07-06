# n8n Research Workflows

This directory contains pre-built n8n workflows for integrating with the Local Deep Researcher service. These workflows provide out-of-the-box automation for research tasks.

## Available Workflows

### 1. Simple Research Workflow (`research-simple.json`)

**Purpose**: Execute single research queries via webhook with automatic result retrieval.

**Webhook URL**: `http://localhost:${N8N_PORT}/webhook/research-trigger`

**Request Format**:
```json
{
  "query": "Your research question here",
  "max_loops": 3,
  "search_api": "duckduckgo",
  "user_id": "optional-user-id"
}
```

**Response**: Complete research results including title, summary, content, and sources.

**Use Cases**:
- Single research queries from external applications
- API integration with frontend applications
- Manual research requests

### 2. Batch Research Workflow (`research-batch.json`)

**Purpose**: Execute multiple research queries simultaneously and return consolidated results.

**Webhook URL**: `http://localhost:${N8N_PORT}/webhook/batch-research`

**Request Format**:
```json
{
  "queries": [
    "First research question",
    "Second research question",
    {
      "query": "Third research question",
      "max_loops": 5,
      "search_api": "duckduckgo"
    }
  ],
  "config": {
    "max_loops": 3,
    "search_api": "duckduckgo",
    "user_id": "optional-user-id"
  }
}
```

**Response**: Batch results with summary statistics and individual research outcomes.

**Use Cases**:
- Market research across multiple topics
- Competitive analysis
- Content research for multiple articles
- Academic research compilation

### 3. Scheduled Research Workflow (`research-scheduled.json`)

**Purpose**: Automatically execute predefined research queries on a schedule (default: weekly on Mondays at 9 AM).

**Schedule**: Configurable via cron expression (default: `0 9 * * MON`)

**Features**:
- Predefined research topics (AI breakthroughs, tech trends, cybersecurity, open source)
- Automatic report generation
- Result storage in Supabase Storage
- Execution summaries and statistics

**Use Cases**:
- Weekly industry reports
- Trend monitoring
- Automated competitive intelligence
- Research newsletter generation

## Installation Instructions

1. **Import Workflows**:
   - Access n8n at `http://localhost:${N8N_PORT}`
   - Go to "Workflows" → "Import from JSON"
   - Copy and paste the contents of each workflow file
   - Save and activate the workflows

2. **Configure Environment**:
   - Ensure the backend service is running on the correct port
   - Verify the Local Deep Researcher service is accessible
   - Test webhook endpoints after import

3. **Set up Credentials** (if needed):
   - Configure any required API keys
   - Set up database connections if using custom storage

## API Integration Examples

### Simple Research Request

```bash
curl -X POST "http://localhost:${N8N_PORT}/webhook/research-trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Latest developments in artificial intelligence",
    "max_loops": 4,
    "user_id": "user123"
  }'
```

### Batch Research Request

```bash
curl -X POST "http://localhost:${N8N_PORT}/webhook/batch-research" \
  -H "Content-Type: application/json" \
  -d '{
    "queries": [
      "Machine learning trends 2024",
      "AI ethics and regulations",
      "Neural network architectures"
    ],
    "config": {
      "max_loops": 3,
      "user_id": "user123"
    }
  }'
```

### JavaScript Integration

```javascript
// Simple research
async function performResearch(query) {
  const response = await fetch('http://localhost:63016/webhook/research-trigger', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: query,
      max_loops: 3,
      user_id: 'web-app-user'
    })
  });
  return response.json();
}

// Batch research
async function performBatchResearch(queries) {
  const response = await fetch('http://localhost:63016/webhook/batch-research', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      queries: queries,
      config: { max_loops: 3 }
    })
  });
  return response.json();
}
```

## Configuration Options

### Timing Configuration

- **Simple Research**: 30-second processing timeout with 10-second retry intervals
- **Batch Research**: 45-second initial wait, 15-second retry intervals
- **Scheduled Research**: 5-minute completion timeout for all queries

### Error Handling

All workflows include:
- Automatic retry mechanisms for transient failures
- Timeout handling for long-running research
- Error response formatting
- Status tracking and logging

### Customization

You can customize the workflows by:
1. Modifying timing parameters in wait nodes
2. Changing retry logic and timeout values
3. Adding notification nodes (email, Slack, etc.)
4. Integrating with other services (databases, APIs)
5. Customizing the scheduled research topics

## Monitoring and Debugging

### Execution Logs

- Access workflow execution logs in n8n interface
- Monitor research session status via backend API endpoints
- Check Local Deep Researcher service logs for detailed processing information

### Health Checks

Test service health:
```bash
# Backend service health
curl http://localhost:${BACKEND_PORT}/research/health

# n8n workflow health
curl http://localhost:${N8N_PORT}/webhook/research-trigger \
  -X POST -H "Content-Type: application/json" \
  -d '{"query": "test query"}'
```

### Common Issues

1. **Webhook not responding**: Check n8n service status and workflow activation
2. **Research timeouts**: Adjust wait times or check Local Deep Researcher performance
3. **Database errors**: Verify Supabase connection and research table setup
4. **Missing results**: Check backend service logs and research session status

## Advanced Usage

### Custom Workflows

Create custom workflows by:
1. Starting with one of the provided templates
2. Adding pre-processing nodes for data transformation
3. Integrating with external APIs or databases
4. Adding post-processing for custom result formatting

### Integration with Other Services

These workflows can be extended to integrate with:
- Slack for result notifications
- Email services for report delivery
- Google Sheets for result tracking
- Custom databases for analytics
- Frontend applications for real-time updates

### Security Considerations

- Use authentication for webhook endpoints in production
- Implement rate limiting to prevent abuse
- Validate input data to prevent injection attacks
- Use HTTPS for secure communication
- Implement proper user access controls