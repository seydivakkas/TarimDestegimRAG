-- ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
-- Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
-- Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlıdır.
--
-- YASAKLAR:
--   1. Kopyalanamaz, çoğaltılamaz, dağıtılamaz veya yeniden yayınlanamaz.
--   2. Ticari veya ticari olmayan hiçbir projede kullanılamaz, değiştirilemez.
--   3. Alt lisanslanamaz, satılamaz veya devredilemez.
--   4. Tersine mühendislik yapılamaz.
--
-- İZİN VERİLEN KULLANIM:
--   - GitHub üzerinde görüntüleme ve okuma.
--   - Kişisel öğrenim amacıyla kodu inceleme (kopyalamadan).
--
-- YAZARIN AÇIK YAZILI İZNİ OLMAKSIZIN HİÇBİR KULLANIM HAKKI TANINMAZ.
-- İzin talepleri için: GitHub @seydivakkas

-- ============================================================================
-- TarımDestekRAG Kurumsal PostgreSQL Rolleri, RLS ve WORM Tetikleyicileri (P0-13)
-- ============================================================================

-- 1. KURUMSAL ROLLERİN OLUŞTURULMASI (Ayrık Yetki İlkesi)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tarim_app_reader') THEN
        CREATE ROLE tarim_app_reader NOLOGIN;
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tarim_rule_editor') THEN
        CREATE ROLE tarim_rule_editor NOLOGIN;
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tarim_legal_reviewer') THEN
        CREATE ROLE tarim_legal_reviewer NOLOGIN;
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tarim_legal_approver') THEN
        CREATE ROLE tarim_legal_approver NOLOGIN;
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tarim_worm_auditor') THEN
        CREATE ROLE tarim_worm_auditor NOLOGIN;
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tarim_admin') THEN
        CREATE ROLE tarim_admin NOLOGIN;
    END IF;
END
$$;

-- 2. ŞEMA ERİŞİM YETKİLERİ
GRANT USAGE ON SCHEMA public TO tarim_app_reader, tarim_rule_editor, tarim_legal_reviewer, tarim_legal_approver, tarim_worm_auditor, tarim_admin;

-- 3. OKUMA VE YAZMA İZİNLERİ (Least Privilege Principle)

-- a) Okuyucu Rolü (tarim_app_reader)
-- Yalnızca resmî kaynakları ve onaylanmış destek kalemlerini okuyabilir.
GRANT SELECT ON sources, source_versions, support_programs, application_windows TO tarim_app_reader;
GRANT SELECT ON support_amounts, dynamic_rates, reviewed_basin_snapshots TO tarim_app_reader;

-- b) Kural Editörü (tarim_rule_editor)
-- Taslak kuralları oluşturabilir, ancak VERIFIED statüsüne geçiremez.
GRANT SELECT, INSERT, UPDATE ON support_amounts, dynamic_rates TO tarim_rule_editor;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tarim_rule_editor;

-- c) Hukuk Müşaviri (tarim_legal_reviewer)
-- Tüm kuralları ve kaynakları inceler, tasdik kaydı ekler.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO tarim_legal_reviewer;
GRANT INSERT ON legal_approval_attestations TO tarim_legal_reviewer;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tarim_legal_reviewer;

-- d) Harcama Yetkilisi (tarim_legal_approver)
-- Onay verir, aktivasyon durumunu günceller.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO tarim_legal_approver;
GRANT INSERT ON legal_approval_attestations, legal_releases TO tarim_legal_approver;
GRANT UPDATE (verification_status) ON support_amounts TO tarim_legal_approver;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tarim_legal_approver;

-- e) WORM Denetçisi (tarim_worm_auditor)
-- Eklemeli (append-only) kütük: SELECT ve INSERT vardır; ASLA UPDATE ve DELETE verilemez!
REVOKE UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM tarim_worm_auditor;
GRANT SELECT, INSERT ON legal_approval_attestations, legal_approval_revocations, legal_audit_events TO tarim_worm_auditor;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tarim_worm_auditor;

-- f) Yönetici Rolü (tarim_admin)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tarim_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tarim_admin;

-- 4. SATIR BAZLI GÜVENLİK (ROW-LEVEL SECURITY - RLS)
ALTER TABLE support_amounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE dynamic_rates ENABLE ROW LEVEL SECURITY;
ALTER TABLE legal_approval_attestations ENABLE ROW LEVEL SECURITY;

-- Politika: Okuyucular yalnız VERIFIED kayıtları görebilir (Fail-Closed)
DROP POLICY IF EXISTS rls_reader_verified_only_support_amounts ON support_amounts;
CREATE POLICY rls_reader_verified_only_support_amounts ON support_amounts
    FOR SELECT TO tarim_app_reader
    USING (verification_status = 'VERIFIED');

DROP POLICY IF EXISTS rls_reader_verified_only_dynamic_rates ON dynamic_rates;
CREATE POLICY rls_reader_verified_only_dynamic_rates ON dynamic_rates
    FOR SELECT TO tarim_app_reader
    USING (status = 'VERIFIED');

-- Politika: Yetkili roller tüm durumları görebilir
DROP POLICY IF EXISTS rls_staff_all_support_amounts ON support_amounts;
CREATE POLICY rls_staff_all_support_amounts ON support_amounts
    FOR ALL TO tarim_rule_editor, tarim_legal_reviewer, tarim_legal_approver, tarim_admin
    USING (true)
    WITH CHECK (true);

-- 5. DEĞİŞTİRİLEMEZ WORM TETİKLEYİCİLERİ (TRIGGER-BASED IMMUTABILITY)
CREATE OR REPLACE FUNCTION prevent_worm_tampering()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'WORM Tablosu Manipülasyon Engeli: Bu tablodaki kayıtlar değiştirilemez veya silinemez (Append-Only Fail-Closed Güvencesi). Tablo: %, İşlem: %', TG_TABLE_NAME, TG_OP;
END;
$$ LANGUAGE plpgsql;

-- Attestation tablosunda UPDATE ve DELETE engeli
DROP TRIGGER IF EXISTS trg_prevent_worm_attestations ON legal_approval_attestations;
CREATE TRIGGER trg_prevent_worm_attestations
    BEFORE UPDATE OR DELETE ON legal_approval_attestations
    FOR EACH ROW EXECUTE FUNCTION prevent_worm_tampering();

-- Revocation tablosunda UPDATE ve DELETE engeli
DROP TRIGGER IF EXISTS trg_prevent_worm_revocations ON legal_approval_revocations;
CREATE TRIGGER trg_prevent_worm_revocations
    BEFORE UPDATE OR DELETE ON legal_approval_revocations
    FOR EACH ROW EXECUTE FUNCTION prevent_worm_tampering();
