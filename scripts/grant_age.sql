-- scripts/grant_age.sql
--
-- Argus needs `LOAD 'age'` which is superuser-only by default in PostgreSQL.
-- The `argus` application role does not have superuser, so Cypher queries via
-- argus_retrieval.graph.GraphQuerier silently fail until this is run.
--
-- Run this as a superuser, e.g.:
--   psql -U postgres -d argus -f scripts/grant_age.sql
--
-- You have two options:
--   (a) Grant superuser to the argus role (simplest; what this file does).
--   (b) Run the application under a role that already has superuser, and skip
--       the ALTER ROLE below. In that case, only the schema/function grants
--       are required.
--
-- Note: there is no `pg_load_extension` predefined role -- LOAD of an unsigned
-- module *requires* superuser. The closest alternative is `pg_read_server_files`
-- membership, which is necessary but not sufficient for LOAD 'age'.
-- If superuser is unacceptable in your environment, switch the application's
-- DB user to one that already has it (e.g. `postgres`) instead.

CREATE EXTENSION IF NOT EXISTS age;

GRANT USAGE ON SCHEMA ag_catalog TO argus;
GRANT SELECT ON ALL TABLES IN SCHEMA ag_catalog TO argus;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA ag_catalog TO argus;

-- Future objects created in ag_catalog should also be visible to argus.
ALTER DEFAULT PRIVILEGES IN SCHEMA ag_catalog
    GRANT SELECT ON TABLES TO argus;
ALTER DEFAULT PRIVILEGES IN SCHEMA ag_catalog
    GRANT EXECUTE ON FUNCTIONS TO argus;

-- LOAD 'age' requires superuser. Comment this out if your security policy
-- forbids it, and run the application under a role that already has it.
ALTER ROLE argus WITH SUPERUSER;
