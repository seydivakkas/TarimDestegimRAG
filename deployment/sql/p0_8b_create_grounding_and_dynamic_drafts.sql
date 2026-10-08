-- P0-8B additive staging schema for future-year PDF text and rate candidates.
-- OFFLINE/DBA-CONTROLLED MIGRATION ONLY. Never publish candidate rates.
-- A separate signed legal approval and release process is required.
BEGIN;
CREATE TABLE IF NOT EXISTS source_documents (
  id SERIAL PRIMARY KEY,
  source_id VARCHAR(64) NOT NULL REFERENCES sources(source_id),
  source_version_id INTEGER REFERENCES source_versions(id),
  production_year INTEGER NOT NULL CHECK (production_year BETWEEN 2020 AND 2100),
  document_sha256 VARCHAR(64) NOT NULL,
  original_url VARCHAR(1024) NOT NULL,
  archive_relative_path VARCHAR(256) NOT NULL,
  content_type VARCHAR(32) NOT NULL DEFAULT 'application/pdf',
  discovered_at TIMESTAMPTZ NOT NULL,
  review_status VARCHAR(16) NOT NULL DEFAULT 'DRAFT'
    CHECK (review_status IN ('DRAFT','REVIEW','REJECTED')),
  CONSTRAINT uq_source_year_pdf_hash UNIQUE
    (source_id, production_year, document_sha256)
);

CREATE TABLE IF NOT EXISTS sentence_bounding_boxes (
  id SERIAL PRIMARY KEY,
  document_id INTEGER NOT NULL REFERENCES source_documents(id),
  page_number INTEGER NOT NULL CHECK (page_number > 0),
  exact_text TEXT NOT NULL,
  article_no VARCHAR(64),
  paragraph_no VARCHAR(64),
  clause_no VARCHAR(64),
  bounding_boxes_json TEXT NOT NULL,
  normalized_quads_json TEXT NOT NULL,
  text_sha256 VARCHAR(64) NOT NULL,
  review_status VARCHAR(16) NOT NULL DEFAULT 'DRAFT'
    CHECK (review_status IN ('DRAFT','REVIEW','REJECTED')),
  CONSTRAINT uq_document_page_exact_sentence UNIQUE
    (document_id, page_number, text_sha256)
);

CREATE TABLE IF NOT EXISTS dynamic_rate_candidates (
  id SERIAL PRIMARY KEY,
  program_key VARCHAR(96) NOT NULL,
  crop_code VARCHAR(96) NOT NULL,
  production_year INTEGER NOT NULL CHECK (production_year BETWEEN 2020 AND 2100),
  province VARCHAR(64) NOT NULL DEFAULT '*',
  district VARCHAR(64) NOT NULL DEFAULT '*',
  base_coefficient NUMERIC(14,2) NOT NULL CHECK (base_coefficient > 0),
  category_multiplier NUMERIC(12,4) NOT NULL CHECK (category_multiplier > 0),
  proposed_unit_amount NUMERIC(14,2) NOT NULL CHECK (proposed_unit_amount > 0),
  unit VARCHAR(16) NOT NULL DEFAULT 'TRY/da',
  effective_from DATE NOT NULL,
  effective_to DATE,
  source_sentence_id INTEGER NOT NULL REFERENCES sentence_bounding_boxes(id),
  review_status VARCHAR(16) NOT NULL DEFAULT 'DRAFT'
    CHECK (review_status IN ('DRAFT','REVIEW','REJECTED')),
  CONSTRAINT uq_year_dynamic_candidate_sentence UNIQUE
    (program_key,crop_code,production_year,province,district,source_sentence_id)
);

-- Authorization is intentionally absent: legal/production runtime roles need
-- explicitly reviewed privileges. P0-7 legal writer must NEVER be granted
-- INSERT into source/rate candidate tables via this migration.
COMMIT;
