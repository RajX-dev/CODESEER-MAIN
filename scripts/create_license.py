# Copyright (C) 2026 Raj shekhar
#
# Interactively generate signed JWT license keys for N3MO clients.

import sys
import os
import jwt
from datetime import datetime, timedelta, timezone

def main():
    print("==================================================")
    print("          N3MO LICENSE KEY GENERATOR              ")
    print("==================================================")

    # 1. Collect inputs
    owner_name = input("Enter Client/Company Name (e.g. Acme Corp): ").strip()
    if not owner_name:
        print("❌ Error: Client name is required.")
        sys.exit(1)

    plan_type = input("Enter Plan Type (pro / enterprise) [default: enterprise]: ").strip().lower() or "enterprise"
    
    max_loc_str = input("Enter Max Lines of Code limit (-1 for unlimited) [default: -1]: ").strip()
    try:
        max_loc = int(max_loc_str) if max_loc_str else -1
    except ValueError:
        max_loc = -1
        
    duration_days_str = input("Enter duration in days [default: 365]: ").strip()
    try:
        duration_days = int(duration_days_str) if duration_days_str else 365
    except ValueError:
        duration_days = 365

    # 2. Retrieve Private Key
    private_key = ""
    # Try reading from secrets/private.pem first
    private_pem_path = os.path.join("secrets", "private.pem")
    if os.path.exists(private_pem_path):
        with open(private_pem_path, "r", encoding="utf-8") as f:
            private_key = f.read()
    else:
        # Fallback to env var
        private_key = os.getenv("N3MO_LICENSE_PRIVATE_KEY", "")

    if not private_key:
        print("\n❌ Error: Private Key not found!")
        print("Please run 'python generate_keys.py' first to generate your RSA signing keys, or set the 'N3MO_LICENSE_PRIVATE_KEY' environment variable.")
        sys.exit(1)

    # Clean key format
    private_key = private_key.replace("\\n", "\n").strip()

    # 3. Create Payload
    payload = {
        "owner": owner_name,
        "plan_type": plan_type,
        "max_loc": max_loc,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(days=duration_days)).timestamp())
    }

    # 4. Generate JWT License Key
    try:
        token = jwt.encode(payload, private_key, algorithm="RS256")
        print("\n==================================================")
        print("✅ LICENSE KEY GENERATED SUCCESSFULLY!")
        print("==================================================")
        print(token)
        print("==================================================")
        print("\nDeliver the key string above to your client.")
        print("They must set this as the value for the environment variable:")
        print("  N3MO_LICENSE_KEY")
        print("And set the matching public key as:")
        print("  N3MO_LICENSE_PUBLIC_KEY")
    except Exception as e:
        print(f"\n❌ Error encoding JWT: {e}")

if __name__ == "__main__":
    main()
