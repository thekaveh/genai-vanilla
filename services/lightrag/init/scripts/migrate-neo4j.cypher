// services/lightrag/init/scripts/migrate-neo4j.cypher
// Idempotent Neo4j constraints + indexes for LightRAG's graph store.

CREATE CONSTRAINT lightrag_entity_id IF NOT EXISTS
FOR (n:Entity) REQUIRE n.id IS UNIQUE;

CREATE INDEX lightrag_entity_name IF NOT EXISTS
FOR (n:Entity) ON (n.name);

CREATE INDEX lightrag_relation_predicate IF NOT EXISTS
FOR ()-[r:RELATION]-() ON (r.predicate);
