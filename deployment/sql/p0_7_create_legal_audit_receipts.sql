-- P0-7 additive production PostgreSQL DDL. Authorized DBA only.
-- Take a backup; verify schema owner/privileges and existing PR #12-18 schema.
-- This CREATE does not migrate old legal data or promote DRAFT records.
BEGIN;
CREATE TABLE IF NOT EXISTS public.legal_audit_receipts (
    id SERIAL PRIMARY KEY,
    subject_type VARCHAR(16) NOT NULL
        CHECK (subject_type IN ('RATE','BASIN','WATER')),
    subject_id INTEGER NOT NULL,
    event_role VARCHAR(16) NOT NULL
        CHECK (event_role IN ('REVIEWER','APPROVER','REVOCATION')),
    object_bucket VARCHAR(255) NOT NULL,
    object_key VARCHAR(512) NOT NULL,
    object_version VARCHAR(255) NOT NULL,
    payload_sha256 VARCHAR(64) NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_audit_subject_event_role UNIQUE
        (subject_type, subject_id, event_role),
    CONSTRAINT uq_audit_object_version UNIQUE
        (object_bucket, object_key, object_version)
);
COMMENT ON TABLE public.legal_audit_receipts IS
    'Remote S3 WORM version receipts; subject activation rechecks the external bytes';
COMMIT;

-- NEXT, run deployment/sql/p0_7_legal_role_grants.sql, then verify each
-- real LOGIN role's SELECT/INSERT/UPDATE/DELETE/TRUNCATE privileges.
-- Do not let FastAPI, reviewer or approver own this table.
