-- P0-8C additive PostgreSQL migration, DBA-reviewed and manually applied.
-- Existing PR #12..#23 schemas must already be installed.
-- This migration NEVER changes a farmer entitlement, selects a year or
-- grants an API login access to edit signed legal evidence.
BEGIN;
CREATE TABLE IF NOT EXISTS public.legal_release_snapshots (
    id SERIAL PRIMARY KEY,
    production_year INTEGER NOT NULL CHECK (production_year BETWEEN 2020 AND 2100),
    source_version_id INTEGER NOT NULL REFERENCES public.source_versions(id),
    manifest_json TEXT NOT NULL,
    manifest_sha256 VARCHAR(64) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    coverage_complete BOOLEAN NOT NULL DEFAULT FALSE,
    review_status VARCHAR(16) NOT NULL DEFAULT 'DRAFT'
        CHECK (review_status IN ('DRAFT','VERIFIED','REVOKED')),
    reviewed_by VARCHAR(128),
    reviewed_at TIMESTAMPTZ,
    review_reference VARCHAR(256),
    CONSTRAINT uq_year_release_manifest UNIQUE (production_year, manifest_sha256)
);
-- New RELEASE subject signs the entire canonical snapshot as distinct reviewer
-- and approver, using the existing cryptographic verifier and WORM receipts.
ALTER TABLE public.legal_approval_attestations
    DROP CONSTRAINT IF EXISTS ck_approval_subject_type;
ALTER TABLE public.legal_approval_attestations
    ADD CONSTRAINT ck_approval_subject_type
    CHECK (subject_type IN ('RATE','BASIN','WATER','RELEASE'));
ALTER TABLE public.legal_audit_receipts
    DROP CONSTRAINT IF EXISTS ck_audit_subject_kind;
ALTER TABLE public.legal_audit_receipts
    ADD CONSTRAINT ck_audit_subject_kind
    CHECK (subject_type IN ('RATE','BASIN','WATER','RELEASE'));

-- Legal officer and importer identities may SELECT release records but never
-- change snapshots or promote DRAFT to VERIFIED. Only the independently
-- controlled data-owner/DBA workflow may review and set VERIFIED.
GRANT SELECT ON public.legal_release_snapshots
    TO tarim_legal_reader, tarim_legal_writer;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.legal_release_snapshots
    FROM tarim_legal_reader, tarim_legal_writer;
COMMIT;

-- DBA separately verifies other inherited permissions, schema owner grants,
-- the public API login, and true Object Lock COMPLIANCE. None are configured
-- by this SQL. A caller with only a verified flag still cannot pass signing.
