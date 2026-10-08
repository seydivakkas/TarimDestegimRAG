-- P0-7 PRODUCTION POSTGRESQL SECURITY POLICY
-- RUN MANUALLY AS AN AUTHORIZED ADMINISTRATOR ONLY, AFTER DATABASE BACKUP.
-- This is a GRANT/REVOKE template, NOT an application startup migration.
-- Login roles are independently created in the organization's IdP/secret manager.
-- Do not give the public FastAPI service credentials for tarim_legal_writer.

BEGIN;
DO $roles$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tarim_legal_reader') THEN
        CREATE ROLE tarim_legal_reader NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tarim_legal_writer') THEN
        CREATE ROLE tarim_legal_writer NOLOGIN;
    END IF;
END
$roles$;

REVOKE ALL ON TABLE
    legal_approval_attestations,
    legal_approval_revocations,
    legal_audit_receipts
FROM PUBLIC;

GRANT USAGE ON SCHEMA public TO tarim_legal_reader, tarim_legal_writer;

GRANT SELECT ON TABLE
    support_programs,
    verified_support_rates,
    reviewed_basin_snapshots,
    reviewed_water_restriction_scopes,
    sources,
    source_versions,
    legal_approval_attestations,
    legal_approval_revocations,
    legal_audit_receipts
TO tarim_legal_reader;

GRANT SELECT ON TABLE
    support_programs,
    verified_support_rates,
    reviewed_basin_snapshots,
    reviewed_water_restriction_scopes,
    sources,
    source_versions,
    legal_approval_attestations,
    legal_approval_revocations,
    legal_audit_receipts
TO tarim_legal_writer;

GRANT INSERT ON TABLE
    legal_approval_attestations,
    legal_approval_revocations,
    legal_audit_receipts
TO tarim_legal_writer;

GRANT USAGE ON SEQUENCE
    legal_approval_attestations_id_seq,
    legal_approval_revocations_id_seq,
    legal_audit_receipts_id_seq
TO tarim_legal_writer;

-- No UPDATE, DELETE or TRUNCATE on signed approvals, revocations or receipts
-- is granted to either legal operator role. Object owners/superusers remain
-- privileged and MUST be excluded from runtime and operator workloads.
-- Existing unrelated LOGIN roles may already have grants: audit/revoke those
-- separately; this SQL does not claim to remove every earlier privilege.
COMMIT;

-- Acceptance queries (run in CI with credentials FOR EACH real login principal):
-- SELECT current_user;
-- SELECT has_table_privilege(current_user,'legal_approval_attestations','UPDATE');
-- SELECT has_table_privilege(current_user,'legal_approval_attestations','DELETE');
-- SELECT has_table_privilege(current_user,'legal_approval_revocations','UPDATE');
-- SELECT has_table_privilege(current_user,'legal_audit_receipts','DELETE');
-- The four privileged operations must all be FALSE.
-- The READ login must not have INSERT on any of the three append-only tables.
-- The WRITE login must not own these tables or have BYPASSRLS/SUPERUSER.
