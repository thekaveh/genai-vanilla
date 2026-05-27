# Troubleshooting Guide

This guide covers common issues and their solutions when using the GenAI Vanilla Stack.

## .env Migration (LiteLLM rollout)

If you're upgrading from a pre-LiteLLM `.env` you may see startup errors about missing variables. Apply these changes:

- Rename `LLM_PROVIDER_PORT` to `LITELLM_PORT` (default is now `63030` under the topology-v1 port layout — the slot belongs to the LiteLLM gateway, not Ollama).
- Remove `OLLAMA_ENDPOINT` and any `OLLAMA_BASE_URL` lines — consumers now read `LITELLM_BASE_URL` and `LITELLM_API_KEY` (where `LITELLM_API_KEY=$LITELLM_MASTER_KEY`).
- If you previously set `LLM_PROVIDER_SOURCE=api` or `LLM_PROVIDER_SOURCE=disabled`, change it to `LLM_PROVIDER_SOURCE=none` and enable at least one of `CLOUD_OPENAI_SOURCE`, `CLOUD_ANTHROPIC_SOURCE`, `CLOUD_OPENROUTER_SOURCE`.

The simplest reset is `cp .env.example .env` followed by `./start.sh --cold` — keys are regenerated and every variable is in its current form.

## Session Log {#launch-log}

When `./start.sh` runs the Textual TUI, every line is tee'd to a timestamped file — both wizard-time diagnostic events (cloud `/v1/models` fetch failures, Ollama upstream discovery warnings, etc.) and the entire launch phase (build, port verification, `docker compose up`, per-service `logs --tail` on failure):

```
/tmp/genai-vanilla-launch-<YYYYMMDDTHHMMSS>.log
```

The most recent log is always:

```bash
ls -t /tmp/genai-vanilla-launch-*.log | head -1
```

Inspect it after a failed launch — it captures everything the log pane showed, plus a few sources the pane filters out (e.g. cloud-fetch fallback warnings: `[warn/openai-fetch] live /v1/models returned 0 models — falling back to catalog (cause: HTTP 401)`). The file persists across reboots until your OS rotates `/tmp`; copy it elsewhere if you need to keep it.

## Quick Fixes

### Port Conflicts
```bash
# Error: "bind: address already in use"
./start.sh --base-port 64000  # Use different port range

# Find what's using the port
lsof -i :63082

# Kill process using the port (if safe)
kill -9 $(lsof -t -i:63082)
```

### Memory Issues
```bash
# Error: Containers crashing with exit code 137 (OOM kill)
# Solution: Increase Docker memory allocation

# Docker Desktop: Settings → Resources → Memory (set to 10-12GB)
# Colima users:
colima stop
colima start --memory 12 --cpu 6
```

### Access Issues
```bash
# Can't access *.localhost URLs?
./start.sh --setup-hosts  # Configure hosts file

# Want to skip hosts setup?
./start.sh --skip-hosts   # Access via direct ports only

# Fresh start needed?
./stop.sh --cold && ./start.sh --cold
```

### Platform Issues
```bash
# Windows/WSL issues?
python3 bootstrapper/start.py --help  # Use Python directly

# Shell script permissions?
chmod +x start.sh stop.sh
```

## Service-Specific Issues

### LLM Issues (LiteLLM gateway + Ollama upstream)

**LiteLLM not responding / consumers can't reach LLMs:**
```bash
# Liveness check (no auth required)
curl http://localhost:63030/health/liveliness

# List registered models (auth required)
curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://localhost:63030/v1/models

# Inspect LiteLLM logs
docker logs genai-litellm -f
```

**Ollama models not downloading:**
```bash
# Check the ollama-pull init container
docker logs genai-ollama-pull -f

# Or the Ollama container itself
docker logs genai-ollama -f

# For localhost setup, pre-download on the host:
ollama serve &
ollama pull qwen3.6:latest
ollama pull qwen3-embedding:0.6b
```

Reminder: Ollama no longer has a host port mapping. Reach it via LiteLLM (`http://localhost:63030/v1`) or via `docker exec` for direct `/api/*` calls.

**Out of memory during model loading:**
```bash
# Use a localhost Ollama upstream to free up Docker memory
./start.sh --llm-provider-source ollama-localhost
ollama pull llama2:7b  # Smaller model
```

### ComfyUI Issues

**Models downloading slowly:**
```bash
# Check ComfyUI init progress
docker logs genai-comfyui-init -f

# Check ComfyUI service status
docker logs genai-comfyui -f
```

**Can't access ComfyUI interface:**
```bash
# Check if hosts are configured
./start.sh --setup-hosts

# Access via direct URL
curl http://localhost:63041  # Direct port access
```

### n8n Issues

**n8n not accessible:**
```bash
# Check n8n service status
docker logs genai-n8n -f

# Try direct access
curl http://localhost:63062

# Check Kong routing
curl -H "Host: n8n.localhost" http://localhost:63000/
```

**Workflow execution fails:**
```bash
# Check n8n worker logs
docker logs genai-n8n-worker -f

# Check Redis connection
docker logs genai-redis -f
```

### Database Issues

**Supabase services not starting:**
```bash
# Check individual service logs
docker logs genai-supabase-db -f
docker logs genai-supabase-auth -f
docker logs genai-supabase-api -f

# Check if database initialization completed
docker logs genai-supabase-db-init -f
```

**Database connection errors:**
```bash
# Verify database is running
docker exec genai-supabase-db pg_isready

# Check connection from another service
docker exec genai-backend python -c "import psycopg2; print('DB OK')"
```

### Kong Gateway Issues

**404 errors for services:**
```bash
# Kong config is dynamically generated at startup — inspect the generator
# (and the KONG_* env vars it consumes) rather than the emitted file:
cat bootstrapper/utils/kong_config_generator.py

# Verify Kong is running
docker logs genai-kong-api-gateway -f

# Test Kong health
curl http://localhost:63000/health
```

**Service routing not working:**
```bash
# Check if service is enabled in configuration
grep -i "COMFYUI_SOURCE" .env
grep -i "N8N_SOURCE" .env

# Verify service is running
docker compose ps | grep -E "(comfyui|n8n)"
```

## Resource Issues

### Docker Resource Monitoring

```bash
# Check overall resource usage
docker stats

# Check disk usage
docker system df

# Clean up unused resources
docker system prune -f
docker volume prune -f  # BE CAREFUL - removes unused volumes
```

### Memory Optimization

```bash
# Disable memory-heavy services
./start.sh --n8n-source disabled --weaviate-source disabled --minio-source disabled

# Use localhost services to reduce container overhead
./start.sh --llm-provider-source ollama-localhost --comfyui-source localhost
```

## Network Issues

### DNS Resolution

```bash
# Check hosts file entries
cat /etc/hosts | grep localhost

# Manually add entries if needed
echo "127.0.0.1 n8n.localhost comfyui.localhost search.localhost api.localhost chat.localhost" | sudo tee -a /etc/hosts
```

### Firewall Issues

```bash
# Check if ports are accessible
telnet localhost 63082
nc -zv localhost 63082

# For localhost services, check host firewall
sudo ufw status  # Ubuntu/Debian
```

## Startup Issues

### Service Dependencies

```bash
# Some services depend on others - check startup order
docker compose ps

# If services are failing, check dependency services first
docker logs genai-redis -f      # Many services need Redis
docker logs genai-supabase-db -f # Backend needs database
```

### Environment Issues

```bash
# Check if .env file exists and is valid
ls -la .env
cat .env | head -20

# Regenerate if corrupted
cp .env.example .env
./start.sh --cold  # Regenerate keys
```

## Debug Commands

### System Status Check

```bash
# Overall system health
docker compose ps

# Service logs (most recent)
docker compose logs --tail=50

# Specific service investigation
docker logs genai-ollama --tail=100 -f
docker logs genai-backend --tail=100 -f
```

### Configuration Verification

```bash
# Inspect the SOURCE values currently written to .env
grep -E '^[A-Z_]+_SOURCE=' .env

# List all available CLI flags (Click-generated help is the source of truth)
python3 bootstrapper/start.py --help

# Inspect the dynamic Kong configuration generator (kong.yml is rebuilt
# on every startup — don't edit by hand; instead trace the inputs):
cat bootstrapper/utils/kong_config_generator.py | head -80
env | grep ^KONG_

# Check live environment variables in your shell
env | grep -E "(OLLAMA|COMFYUI|N8N|WEAVIATE|CLOUD|MINIO)_SOURCE"
```

### Network Testing

```bash
# Test internal service connectivity (LLM goes through LiteLLM, not Ollama directly)
docker exec genai-backend curl http://genai-litellm:4000/health/liveliness
docker exec genai-litellm curl http://genai-ollama:11434/api/tags
docker exec genai-kong-api-gateway curl http://genai-supabase-api:3000/health

# Test external access
curl http://localhost:63082
curl -H "Host: n8n.localhost" http://localhost:63000/
```

## Getting Help

### Log Collection

When reporting issues, include:

```bash
# System information
docker --version
docker compose version
python3 --version

# Service status
docker compose ps > service_status.txt

# Recent logs
docker compose logs --tail=100 > stack_logs.txt

# Configuration
cp .env config_backup.env  # Remove sensitive data before sharing
```

### Common Support Information

1. **Platform**: macOS/Linux/Windows + version
2. **Docker memory allocation**: Settings → Resources in Docker Desktop
3. **Services enabled**: Which SOURCE values you're using
4. **Error messages**: Exact error text and which service
5. **Steps to reproduce**: What you did before the error occurred

### Community Resources

- [GitHub Issues](https://github.com/thekaveh/genai-vanilla/issues) - Bug reports and feature requests
- [GitHub Discussions](https://github.com/thekaveh/genai-vanilla/discussions) - Questions and community support
- [Documentation](../README.md) - Complete documentation index

## Recovery Procedures

### Complete Reset

```bash
# Nuclear option - removes all data
./stop.sh --cold
docker system prune -af  # Remove all containers, networks, images
docker volume prune -f   # BE CAREFUL - removes ALL unused volumes

# Start fresh
./start.sh --cold --base-port 64000
```

### Partial Reset

```bash
# Reset just environment
./stop.sh
rm .env
cp .env.example .env
./start.sh --cold  # Regenerate keys only

# Reset specific service data
docker volume rm genai-vanilla_supabase_db_data  # Database only
docker volume rm genai-vanilla_n8n_data          # n8n workflows only
```

### Backup Before Reset

```bash
# Backup important data before reset
mkdir -p backup/$(date +%Y%m%d_%H%M%S)
docker run --rm -v genai-vanilla_supabase_db_data:/data -v $(pwd)/backup/$(date +%Y%m%d_%H%M%S):/backup alpine cp -r /data /backup/supabase_db
docker run --rm -v genai-vanilla_n8n_data:/data -v $(pwd)/backup/$(date +%Y%m%d_%H%M%S):/backup alpine cp -r /data /backup/n8n
```

Remember: Most issues can be resolved without losing data. Try targeted solutions before doing a complete reset!