# Troubleshooting Guide

This guide covers common issues and their solutions when using the GenAI Vanilla Stack.

## Quick Fixes

### Port Conflicts
```bash
# Error: "bind: address already in use"
./start.sh --base-port 64000  # Use different port range

# Find what's using the port
lsof -i :63015

# Kill process using the port (if safe)
kill -9 $(lsof -t -i:63015)
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

### Ollama Issues

**Models not downloading:**
```bash
# Check Ollama logs
docker logs genai-ollama -f

# For localhost setup, ensure models are pre-downloaded
ollama serve &
ollama pull qwen2.5:latest
ollama pull mxbai-embed-large
```

**Out of memory during model loading:**
```bash
# Use smaller models for testing
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
curl http://localhost:63018  # Direct port access
```

### n8n Issues

**n8n not accessible:**
```bash
# Check n8n service status
docker logs genai-n8n -f

# Try direct access
curl http://localhost:63017

# Check Kong routing
curl -H "Host: n8n.localhost" http://localhost:63002/
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
# Check Kong configuration
cat volumes/api/kong.yml

# Verify Kong is running
docker logs genai-kong-api-gateway -f

# Test Kong health
curl http://localhost:63002/health
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
./start.sh --n8n-source disabled --weaviate-source disabled

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
telnet localhost 63015
nc -zv localhost 63015

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
# Check what SOURCE values are active
python3 bootstrapper/start.py --help-usage

# View generated Kong configuration
cat volumes/api/kong.yml | head -50

# Check environment variables
env | grep -E "(OLLAMA|COMFYUI|N8N|WEAVIATE)_SOURCE"
```

### Network Testing

```bash
# Test internal service connectivity
docker exec genai-backend curl http://genai-ollama:11434/api/tags
docker exec genai-kong-api-gateway curl http://genai-supabase-api:3000/health

# Test external access
curl http://localhost:63015
curl -H "Host: n8n.localhost" http://localhost:63002/
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

- [GitHub Issues](https://github.com/your-repo/issues) - Bug reports and feature requests
- [GitHub Discussions](https://github.com/your-repo/discussions) - Questions and community support
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