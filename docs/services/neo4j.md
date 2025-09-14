# Neo4j Graph Database

Neo4j provides graph database capabilities for the GenAI Vanilla Stack, enabling relationship modeling and graph-based queries.

## Overview

The Neo4j service provides:
- Graph database for storing and querying relationships
- Web-based browser interface for data visualization
- Cypher query language support
- APOC (Awesome Procedures on Cypher) extensions
- Automatic backup and restore capabilities

## Access Information

- **Browser Interface**: `http://localhost:${GRAPH_DB_DASHBOARD_PORT}` (default: 63011)
- **Bolt Protocol**: `bolt://localhost:${GRAPH_DB_BOLT_PORT}` (default: 63013)
- **HTTP API**: `http://localhost:${GRAPH_DB_HTTP_PORT}` (default: 63012)

## Default Credentials

- **Username**: `neo4j`
- **Password**: `${NEO4J_AUTH_PASSWORD}` (from .env file)

## Backup and Restore

The Neo4j service includes built-in backup and restore capabilities.

### Manual Backup

To manually create a graph database backup:

```bash
# Create a backup (will temporarily stop and restart Neo4j)
docker exec -it ${PROJECT_NAME}-neo4j-graph-db /usr/local/bin/backup.sh
```

The backup will be stored in the `/snapshot` directory inside the container, which is mounted to the `./neo4j-graph-db/snapshot/` directory on your host machine.

### Manual Restore

To restore from a previous backup:

```bash
# Restore from the latest backup
docker exec -it ${PROJECT_NAME}-neo4j-graph-db /usr/local/bin/restore.sh
```

### Automatic Restore

- **Automatic restoration at startup** is enabled by default
- When the container starts, it automatically restores from the latest backup if available
- To disable automatic restore, remove or rename the `auto_restore.sh` script in the Dockerfile

### Important Backup Notes

- By default, data persists in the Docker volume between restarts
- Backups are incremental and space-efficient
- Backup files are timestamped for easy identification
- Manual backups can be created while the database is running

## Data Persistence

Neo4j data is stored in Docker named volumes:
- **Volume Name**: `genai-vanilla_graph_db_data`
- **Mount Point**: `/data` (inside container)
- **Backup Location**: `/snapshot` (mounted to host)

## Environment Variables

Key environment variables for Neo4j:

```bash
# Authentication
NEO4J_AUTH_PASSWORD=your_password

# Port Configuration
GRAPH_DB_HTTP_PORT=63012
GRAPH_DB_BOLT_PORT=63013
GRAPH_DB_DASHBOARD_PORT=63011

# Database Settings
NEO4J_dbms_memory_heap_initial__size=512m
NEO4J_dbms_memory_heap_max__size=1G
NEO4J_dbms_memory_pagecache_size=512m
```

## Usage Examples

### Connect via Cypher Shell
```bash
# Connect using Docker
docker exec -it genai-neo4j-graph-db cypher-shell -u neo4j -p ${NEO4J_AUTH_PASSWORD}

# Sample queries
MATCH (n) RETURN count(n);  // Count all nodes
MATCH (n) DETACH DELETE n;  // Clear all data (use with caution)
```

### Connect via Python
```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://localhost:63013",
    auth=("neo4j", "your_password")
)

with driver.session() as session:
    result = session.run("MATCH (n) RETURN count(n) as node_count")
    print(result.single()["node_count"])

driver.close()
```

### Basic Graph Operations
```cypher
// Create nodes
CREATE (p:Person {name: 'Alice', age: 30})
CREATE (p:Person {name: 'Bob', age: 25})

// Create relationships
MATCH (a:Person {name: 'Alice'}), (b:Person {name: 'Bob'})
CREATE (a)-[:KNOWS]->(b)

// Query relationships
MATCH (p:Person)-[:KNOWS]->(friend:Person)
RETURN p.name, friend.name
```

## Integration with Other Services

### Backend API
The FastAPI backend can connect to Neo4j for:
- Storing user relationships
- Knowledge graph operations
- Recommendation systems
- Complex relationship queries

### n8n Workflows
Neo4j can be integrated into workflows for:
- Graph-based data processing
- Relationship analysis
- Network analysis workflows
- Data enrichment with graph context

## Performance Tuning

### Memory Configuration
Adjust memory settings based on your data size and available system memory:

```bash
# For larger datasets
NEO4J_dbms_memory_heap_max__size=2G
NEO4J_dbms_memory_pagecache_size=1G

# For smaller datasets or limited memory
NEO4J_dbms_memory_heap_max__size=512m
NEO4J_dbms_memory_pagecache_size=256m
```

### Query Optimization
- Use indexes for frequently queried properties
- Limit result sets with `LIMIT` clause
- Use `EXPLAIN` and `PROFILE` to analyze query performance
- Consider graph data modeling best practices

## Monitoring and Maintenance

### Health Checks
```bash
# Check container status
docker logs genai-neo4j-graph-db -f

# Test HTTP endpoint
curl http://localhost:63012/

# Check Bolt connection
docker exec genai-neo4j-graph-db cypher-shell -u neo4j -p password "RETURN 'Connection OK'"
```

### Database Statistics
```cypher
// Get database info
CALL db.info()

// Get node and relationship counts
MATCH (n) RETURN labels(n), count(n) ORDER BY count(n) DESC

// Check indexes
CALL db.indexes()
```

### Cleanup Operations
```cypher
// Remove all data (use with extreme caution)
MATCH (n) DETACH DELETE n

// Remove specific node types
MATCH (p:Person) DETACH DELETE p

// Remove orphaned relationships
MATCH ()-[r]-() WHERE startNode(r) IS NULL OR endNode(r) IS NULL DELETE r
```

## Troubleshooting

### Common Issues

**Container won't start**: Check memory allocation and port conflicts
**Authentication failures**: Verify NEO4J_AUTH_PASSWORD in .env file
**Connection refused**: Ensure ports are not blocked by firewall
**Out of memory errors**: Increase heap size or reduce dataset size

### Debug Commands
```bash
# View detailed logs
docker logs genai-neo4j-graph-db --tail=100 -f

# Check resource usage
docker stats genai-neo4j-graph-db

# Verify configuration
docker exec genai-neo4j-graph-db cat /var/lib/neo4j/conf/neo4j.conf
```

### Recovery Procedures
```bash
# If database is corrupted, restore from backup
docker exec -it genai-neo4j-graph-db /usr/local/bin/restore.sh

# If backup is corrupted, reinitialize (data loss)
docker volume rm genai-vanilla_graph_db_data
docker compose up neo4j-graph-db
```

For more troubleshooting help, see [../quick-start/troubleshooting.md](../quick-start/troubleshooting.md).

## Further Reading

- [Neo4j Documentation](https://neo4j.com/docs/)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/)
- [Neo4j APOC Documentation](https://neo4j.com/docs/apoc/)
- [Graph Data Modeling](https://neo4j.com/docs/graph-data-modeling/)