-- 01-init-roles.sql
-- Create dedicated read-only role for AI agent execution
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE rolname = 'readonly_analyst') THEN
      CREATE ROLE readonly_analyst WITH LOGIN PASSWORD 'readonly_pass';
   END IF;
END
$do$;

-- Revoke all administrative privileges
REVOKE ALL ON SCHEMA public FROM readonly_analyst;
GRANT CONNECT ON DATABASE business_db TO readonly_analyst;
GRANT USAGE ON SCHEMA public TO readonly_analyst;

-- Set default permissions for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_analyst;
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON TABLES FROM readonly_analyst;
