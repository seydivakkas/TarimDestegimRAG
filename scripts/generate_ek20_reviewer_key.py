"""Create one local ED25519 reviewer identity; never commit private keys.

Human-identity, employment/role and independence must be verified by an
authorized registry administrator outside this key-generation utility.
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Issue one LOCAL EK-20 visual reviewer key pair (not legal approval)"
    )
    parser.add_argument("--reviewer-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,60}", args.reviewer_id):
        parser.error("Invalid reviewer ID")
    directory = args.output_dir.resolve()
    private_path = directory / (args.reviewer_id + ".private.pem")
    public_path = directory / (args.reviewer_id + ".public.pem")
    if private_path.exists() or public_path.exists():
        parser.error("Reviewer key already exists: key rotation must be explicit")
    if directory.is_relative_to(Path.cwd().resolve()):
        parser.error("Store private reviewer keys OUTSIDE the project repository")
    directory.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    private = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    # Never echo PEM secrets. Exclusive creation forbids overwriting a key.
    fd = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(private)
    except BaseException:
        private_path.unlink(missing_ok=True)
        raise
    try:
        with public_path.open("xb") as handle:
            handle.write(public)
    except BaseException:
        private_path.unlink(missing_ok=True)
        raise
    print(f"Public key: {public_path}")
    print(f"Private key: {private_path} — keep on the reviewer's protected device.")
    print(
        "The registry administrator must separately validate the human "
        "reviewer and add their PUBLIC key/role to the private trust registry."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
