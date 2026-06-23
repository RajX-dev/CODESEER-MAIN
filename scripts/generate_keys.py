# Copyright (C) 2026 Raj shekhar
#
# Generating RSA key pairs for cryptographically signing and verifying license keys.

import os
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def generate_keys():
    print("Generating RSA 2048 key pair...")
    
    # 1. Generate Private Key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # 2. Serialize Private Key in PEM
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # 3. Extract and Serialize Public Key in PEM
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    # 4. Save to files
    secrets_dir = os.path.abspath("secrets")
    os.makedirs(secrets_dir, exist_ok=True)
    
    private_path = os.path.join(secrets_dir, "private.pem")
    public_path = os.path.join(secrets_dir, "public.pem")
    
    with open(private_path, "w", encoding="utf-8") as f:
        f.write(private_pem)
    with open(public_path, "w", encoding="utf-8") as f:
        f.write(public_pem)
        
    print(f"\nSaved keys to:\n- Private Key: {private_path}\n- Public Key:  {public_path}\n")
    
    # 5. Format for environment variables
    # We replace real newlines with literal '\n' characters so they fit on a single line in a .env file.
    private_env_val = private_pem.replace("\n", "\\n").strip()
    public_env_val = public_pem.replace("\n", "\\n").strip()
    
    print("=" * 80)
    print("COPY AND PASTE THE FOLLOWING INTO YOUR ENV CONFIGURATIONS:")
    print("=" * 80)
    print("\n# Your secure signing key (SaaS/Admin server environment variable)")
    print(f'N3MO_LICENSE_PRIVATE_KEY="{private_env_val}"')
    print("\n# Your verification key (Self-hosted/Client environment variable)")
    print(f'N3MO_LICENSE_PUBLIC_KEY="{public_env_val}"')
    print("=" * 80)

if __name__ == "__main__":
    generate_keys()
