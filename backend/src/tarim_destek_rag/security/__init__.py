# ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
# Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
# Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlı olarak paylaşılmıştır.
# YASAKLAR: Kopyalanamaz, çoğaltılamaz, dağıtılamaz, satılamaz, tersine mühendislik yapılamaz.
# İZİN VERİLEN KULLANIM: GitHub üzerinde görüntüleme ve inceleme.

"""
P0-13 Enterprise Security Package.
Provides KMS/HSM key abstraction, PostgreSQL role matrix audit,
WORM checkpoints & legal evidence vault exports, institutional revocations,
and cryptographically signed release packaging.
"""

from tarim_destek_rag.security.database_roles import (
    DatabaseRole,
    DatabaseRoleManager,
    get_database_role_manager,
)
from tarim_destek_rag.security.enterprise_worm import (
    EnterpriseWormArchive,
    WormCheckpoint,
    get_enterprise_worm_archive,
)
from tarim_destek_rag.security.kms_provider import (
    HashiCorpVaultProvider,
    KeyManagementProvider,
    KmsKeyMetadata,
    PKCS11HsmProvider,
    SoftwareKmsProvider,
    get_kms_provider,
    set_global_kms_provider,
)
from tarim_destek_rag.security.revocation_manager import (
    REVOCATION_REASON_TAXONOMY,
    EnterpriseRevocationManager,
    RevocationCertificate,
    get_enterprise_revocation_manager,
)
from tarim_destek_rag.security.secure_release import (
    ReleasePackageMetadata,
    SecureReleaseManager,
    get_secure_release_manager,
)

__all__ = [
    "KeyManagementProvider",
    "SoftwareKmsProvider",
    "HashiCorpVaultProvider",
    "PKCS11HsmProvider",
    "KmsKeyMetadata",
    "get_kms_provider",
    "set_global_kms_provider",
    "DatabaseRole",
    "DatabaseRoleManager",
    "get_database_role_manager",
    "EnterpriseWormArchive",
    "WormCheckpoint",
    "get_enterprise_worm_archive",
    "EnterpriseRevocationManager",
    "RevocationCertificate",
    "REVOCATION_REASON_TAXONOMY",
    "get_enterprise_revocation_manager",
    "ReleasePackageMetadata",
    "SecureReleaseManager",
    "get_secure_release_manager",
]
