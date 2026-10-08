# P0-7 role-specific Vault Transit ACL TEMPLATE.
# Enroll a real OIDC subject and MFA policy outside the repository.
# Do not give this identity access to keys of the other role, key export,
# key rotation, deletion, sys/auth, sudo or broad transit/* endpoints.
path "transit/sign/tarim-legal-reviewer" {
  capabilities = ["update"]
}
