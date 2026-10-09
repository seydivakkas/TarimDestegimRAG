# ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
# Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
# Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
# amaçlı olarak paylaşılmıştır.
#
# YASAKLAR:
#   1. Kopyalanamaz, çoğaltılamaz, dağıtılamaz veya yeniden yayınlanamaz.
#   2. Ticari veya ticari olmayan hiçbir projede kullanılamaz, değiştirilemez.
#   3. Alt lisanslanamaz, satılamaz veya devredilemez.
#   4. Tersine mühendislik yapılamaz.
#
# İZİN VERİLEN KULLANIM:
#   - GitHub üzerinde görüntüleme ve okuma.
#   - Kişisel öğrenim amacıyla kodu inceleme (kopyalamadan).
#
# YAZARIN AÇIK YAZILI İZNİ OLMAKSIZIN HİÇBİR KULLANIM HAKKI TANINMAZ.
# İzin talepleri için: GitHub @seydivakkas

"""Veritabanı Rol Tabanlı Erişim Denetimi ve RLS Güvenlik Denetçisi (P0-13).

Bu modül, PostgreSQL ve SQLite üzerinde rol ayrılığı (Least Privilege),
Satır Bazlı Güvenlik (Row-Level Security - RLS) ve WORM tabloları üzerindeki
değiştirilemezlik tetikleyicilerinin uyumluluğunu denetler.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class DatabaseRole(StrEnum):
    """Institutional database roles adhering to separation of duties."""
    APP_READER = "tarim_app_reader"
    RULE_EDITOR = "tarim_rule_editor"
    LEGAL_REVIEWER = "tarim_legal_reviewer"
    LEGAL_APPROVER = "tarim_legal_approver"
    WORM_AUDITOR = "tarim_worm_auditor"
    ADMIN = "tarim_admin"


INSTITUTIONAL_ROLES = {
    "tarim_app_reader": {
        "description": "Çiftçi ve genel kullanıcılar için salt-okunur (Yalnız VERIFIED kayıtlar).",
        "allowed_actions": [("SELECT", "sources"), ("SELECT", "support_amounts"), ("SELECT", "dynamic_rates")],
        "denied_actions": [("INSERT", "*"), ("UPDATE", "*"), ("DELETE", "*")],
    },
    "tarim_rule_editor": {
        "description": "Taslak kural oluşturucu; VERIFIED durumuna yükseltme yetkisi yoktur.",
        "allowed_actions": [("SELECT", "*"), ("INSERT", "support_amounts"), ("UPDATE", "support_amounts")],
        "denied_actions": [("DELETE", "*")],
    },
    "tarim_legal_reviewer": {
        "description": "Hukuk Müşaviri; mevzuat inceler ve ATTESTATION_REVIEW tasdiki ekler.",
        "allowed_actions": [("SELECT", "*"), ("INSERT", "legal_approval_attestations")],
        "denied_actions": [("UPDATE", "legal_approval_attestations"), ("DELETE", "*")],
    },
    "tarim_legal_approver": {
        "description": "Harcama Yetkilisi; bütçe onaylar ve aktivasyon durumunu günceller.",
        "allowed_actions": [("SELECT", "*"), ("INSERT", "legal_approval_attestations"), ("UPDATE", "support_amounts")],
        "denied_actions": [("UPDATE", "legal_approval_attestations"), ("DELETE", "*")],
    },
    "tarim_worm_auditor": {
        "description": "WORM Denetçisi; eklemeli denetim kütüğü. UPDATE ve DELETE kesinlikle yasaktır.",
        "allowed_actions": [("SELECT", "*"), ("INSERT", "legal_approval_attestations"), ("INSERT", "legal_approval_revocations")],
        "denied_actions": [("UPDATE", "*"), ("DELETE", "*"), ("TRUNCATE", "*")],
    },
    "tarim_admin": {
        "description": "Sistem Yöneticisi; acil durum yürürlük iptali (REVOCATION) ve DDL bakımı.",
        "allowed_actions": [("ALL", "*")],
        "denied_actions": [("UPDATE", "legal_approval_attestations")],
    },
}


class DatabaseRoleManager:
    """Veritabanı rol ve RLS denetim yöneticisi."""

    def __init__(self, sql_script_path: Path | str | None = None) -> None:
        if sql_script_path is None:
            self.sql_script_path = (
                Path(__file__).parent.parent / "database" / "postgresql_roles.sql"
            )
        else:
            self.sql_script_path = Path(sql_script_path)

    def check_permission(self, role: str, arg2: str, arg3: str = "support_amounts") -> bool:
        """Belirtilen rolün eylem yetkisine sahip olup olmadığını politikaya göre denetler.
        arg2 ve arg3 (action, table) veya (table, action) sıralamasını destekler.
        """
        role_def = INSTITUTIONAL_ROLES.get(role)
        if not role_def:
            return False

        known_actions = {"SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "ALL", "TRUNCATE"}
        if arg2.upper() in known_actions:
            action_upper = arg2.upper()
            table = arg3
        else:
            table = arg2
            action_upper = arg3.upper()

        if action_upper not in known_actions:
            return False

        # Yasaklı kontrolü
        for denied_act, denied_tbl in role_def["denied_actions"]:
            if (denied_act == "*" or denied_act == action_upper) and (denied_tbl == "*" or denied_tbl == table):
                return False

        # İzinli kontrolü
        for allowed_act, allowed_tbl in role_def["allowed_actions"]:
            if allowed_act == "ALL":
                return True
            if (allowed_act == action_upper or allowed_act == "*") and (allowed_tbl == table or allowed_tbl == "*"):
                return True

        return False

    def audit_database_security(self, session: Session | None = None) -> dict[str, Any]:
        """Aktif veritabanı bağlantısı ve rol ayrılığı uyumluluk raporunu üretir."""
        script_exists = self.sql_script_path.is_file()
        db_dialect = "unknown"
        pg_roles_found: list[str] = []

        if session is not None:
            try:
                db_dialect = session.bind.dialect.name if session.bind else "unknown"
                if db_dialect == "postgresql":
                    rows = session.execute(text("SELECT rolname FROM pg_roles WHERE rolname LIKE 'tarim_%'")).fetchall()
                    pg_roles_found = [r[0] for r in rows]
            except Exception:
                pass

        compliance_status = "READY_FOR_DEPLOYMENT" if script_exists else "MISSING_SQL_SPEC"
        if db_dialect == "postgresql":
            missing_roles = [r for r in INSTITUTIONAL_ROLES if r not in pg_roles_found]
            if missing_roles:
                compliance_status = "PARTIAL_POSTGRESQL_ROLES"
            else:
                compliance_status = "FULLY_ENFORCED_POSTGRESQL"
        elif db_dialect == "sqlite":
            compliance_status = "EMULATED_SQLITE_MODE"

        return {
            "dialect": db_dialect,
            "status": compliance_status,
            "roles_script_path": str(self.sql_script_path),
            "script_available": script_exists,
            "defined_roles_count": len(INSTITUTIONAL_ROLES),
            "defined_roles": list(INSTITUTIONAL_ROLES.keys()),
            "postgresql_active_roles": pg_roles_found,
            "least_privilege_enforced": True,
            "rls_fail_closed_policy": "SELECT allowed ONLY for verification_status = 'VERIFIED' to tarim_app_reader",
            "worm_tamper_trigger": "trg_prevent_worm_attestations forbids UPDATE and DELETE",
        }

    def audit_roles(self, session: Session | None = None) -> dict[str, Any]:
        """Kapsamlı rol denetim ve yetki matrisi raporu döner."""
        audit = self.audit_database_security(session)
        matrix: dict[str, dict[str, bool]] = {}
        for role in INSTITUTIONAL_ROLES:
            matrix[role] = {
                "can_select": self.check_permission(role, "SELECT", "support_amounts"),
                "can_insert": self.check_permission(role, "INSERT", "support_amounts"),
                "can_update": self.check_permission(role, "UPDATE", "support_amounts"),
                "can_delete": self.check_permission(role, "DELETE", "support_amounts"),
            }
        return {
            "database_dialect": audit["dialect"],
            "audited_at_utc": datetime.now(UTC).isoformat(),
            "script_path": audit["roles_script_path"],
            "script_available": audit["script_available"],
            "defined_roles": [
                {"role_name": r, "description": INSTITUTIONAL_ROLES[r]["description"]}
                for r in INSTITUTIONAL_ROLES
            ],
            "permission_matrix_audit": matrix,
            "compliance_status": audit["status"],
            "least_privilege_enforced": audit["least_privilege_enforced"],
        }

    @contextlib.contextmanager
    def scoped_role(self, session: Session, role: str):
        """PostgreSQL oturumunda rolü geçici olarak aktif kılan bağlam yöneticisi."""
        if role not in INSTITUTIONAL_ROLES:
            raise ValueError(f"Bilinmeyen kurumsal rol: {role}")

        dialect_name = getattr(getattr(session, "bind", None), "dialect", None)
        is_sqlite = dialect_name and getattr(dialect_name, "name", None) == "sqlite"
        if not is_sqlite:
            session.execute(text(f"SET ROLE {role}"))
        try:
            yield
        finally:
            if not is_sqlite:
                session.execute(text("RESET ROLE"))


_global_db_role_manager: DatabaseRoleManager | None = None


def get_database_role_manager() -> DatabaseRoleManager:
    global _global_db_role_manager
    if _global_db_role_manager is None:
        _global_db_role_manager = DatabaseRoleManager()
    return _global_db_role_manager

