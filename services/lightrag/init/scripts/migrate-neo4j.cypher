// services/lightrag/init/scripts/migrate-neo4j.cypher
// Idempotent Neo4j index for LightRAG's graph store (v1.5.0 Neo4JStorage).
//
// LightRAG stores graph nodes under a workspace label (default `base`; override
// via the NEO4J_WORKSPACE env var) with the unique identifier in the
// `entity_id` property, and connects them with `DIRECTED` relationships. It
// creates this same range index itself on first write
// (CREATE INDEX ... IF NOT EXISTS FOR (n:`base`) ON (n.entity_id)); pre-creating
// it here means entity lookups are indexed from the very first ingestion.
// IF NOT EXISTS is schema-aware in Neo4j, so this never conflicts with
// LightRAG's own creation. Earlier revisions targeted a (:Entity {id}) /
// [:RELATION {predicate}] schema that LightRAG never writes — those objects
// matched no real nodes/relationships and were silently inert.

CREATE INDEX lightrag_entity_id IF NOT EXISTS
FOR (n:`base`) ON (n.entity_id);
