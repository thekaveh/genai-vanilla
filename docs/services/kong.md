# Kong API Gateway

Kong serves as the intelligent API gateway for the GenAI Vanilla Stack, providing dynamic routing, authentication, and service management.

## Overview

Kong acts as the central entry point for most services, routing requests to appropriate backend services based on dynamic configuration generated at startup.

## Dynamic Configuration

Unlike traditional static configuration files, the GenAI Vanilla Stack uses dynamic Kong configuration that adapts to your SOURCE settings:

- **Automatic Route Generation**: Kong routes are created based on enabled services
- **Health Checking**: Localhost services are checked for availability before routing
- **Adaptive Configuration**: Disabled services automatically have their routes removed
- **No Manual Configuration**: Replaces the old dual kong.yml/kong-local.yml approach

The configuration is generated at startup by `bootstrapper/utils/kong_config_generator.py`.

## Service Routing

### Always-Available Routes (Supabase)
- `/auth/v1/` → Supabase Auth service
- `/rest/v1/` → Supabase API (PostgREST)
- `/graphql/v1/` → Supabase GraphQL
- `/realtime/v1/` → Supabase Realtime
- `/storage/v1/` → Supabase Storage
- `/pg/` → Supabase Meta service
- `/` → Supabase Studio dashboard

### Dynamic Routes (Based on SOURCE)
- `comfyui.localhost` → ComfyUI service (if enabled)
- `n8n.localhost` → n8n service (if enabled)
- `search.localhost` → SearxNG service (if enabled)
- `api.localhost` → Backend API (if enabled)
- `chat.localhost` → Open WebUI (if enabled)

## SOURCE-Based Configuration

### ComfyUI Routes
```python
# Generated based on COMFYUI_SOURCE
if source == 'localhost':
    service['url'] = 'http://host.docker.internal:8000/'
elif source == 'external':
    service['url'] = external_url
elif source in ['container-cpu', 'container-gpu']:
    service['url'] = 'http://comfyui:18188/'
# No route created if source == 'disabled'
```

### Localhost Service Health Checks
When routing to localhost services, Kong generator performs health checks:

```python
def check_localhost_service(self, host: str, port: int, service_name: str) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (socket.error, socket.timeout):
        print(f"⚠️  {service_name} localhost service not reachable on {host}:{port}")
        return False
```

## Authentication

Kong handles multiple authentication schemes:

- **API Key Authentication**: Used for Supabase API services
- **Basic Authentication**: Used for protected admin interfaces
- **Pass-through Authentication**: For services that handle their own auth

## CORS Handling

All services automatically get CORS plugin configuration for cross-origin requests:

```python
'plugins': [{'name': 'cors'}]
```

## Rate Limiting

Some services include rate limiting for protection:

```python
# SearxNG example
{
    'name': 'rate-limiting',
    'config': {
        'minute': 60,
        'hour': 1000,
        'policy': 'local'
    }
}
```

## WebSocket Support

Kong supports WebSocket connections for real-time services:

```python
{
    'name': 'realtime-v1-ws',
    'url': 'http://supabase-realtime:4000/socket',
    'protocol': 'ws',
    # ...
}
```

## Configuration Generation Process

1. **Startup**: `start.py` calls Kong configuration generator at step 4.5
2. **Environment Parsing**: Current .env file is parsed for SOURCE values
3. **Health Checks**: Localhost services are checked for availability  
4. **Route Generation**: Only enabled services get routes created
5. **File Writing**: Configuration written to volumes/api/kong.yml
6. **Kong Startup**: Kong loads the generated configuration

## Debugging Kong Configuration

### View Generated Configuration
```bash
# Check what configuration was generated
cat volumes/api/kong.yml

# View Kong logs
docker logs genai-kong-api-gateway -f

# Test Kong health
curl http://localhost:63002/health
```

### Verify Routes
```bash
# List all configured routes
docker exec genai-kong-api-gateway kong config -c /kong.yml dump

# Test specific routes
curl -H "Host: comfyui.localhost" http://localhost:63002/
curl -H "Host: n8n.localhost" http://localhost:63002/
```

## Troubleshooting

### Common Issues

**Route not found (404)**
- Check if service SOURCE is enabled
- Verify service is running and healthy
- Check hosts file configuration

**Connection refused**
- For localhost routes, ensure service is running on specified port
- Check firewall settings for localhost services
- Verify Docker network connectivity

**Authentication errors**
- Check if service requires API key authentication
- Verify Supabase keys are properly generated
- Ensure proper headers are sent

### Debug Commands
```bash
# Check Kong gateway status
docker compose ps | grep kong

# View detailed Kong configuration
docker exec genai-kong-api-gateway cat /kong.yml

# Test internal Kong admin API
docker exec genai-kong-api-gateway curl http://localhost:8001/status
```

## Advanced Configuration

For advanced Kong configuration needs, modify the `KongConfigGenerator` class in `bootstrapper/utils/kong_config_generator.py`.

Key methods:
- `generate_kong_config()` - Main configuration generator
- `check_localhost_service()` - Health check implementation
- `generate_*_service()` - Service-specific route generators

## Integration with Other Services

Kong integrates tightly with:
- **Service Configuration**: Uses SOURCE values from service_config.py
- **Environment Management**: Reads from parsed .env files
- **Health Monitoring**: Checks localhost service availability
- **Dynamic Scaling**: Adapts to enabled/disabled services

For more information on Kong's role in the overall architecture, see [../development/architecture.md](../development/architecture.md).