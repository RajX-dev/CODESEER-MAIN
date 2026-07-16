# Copyright (C) 2026 Raj shekhar
#
# This file is part of N3MO.
# N3MO is licensed under the PolyForm Noncommercial License 1.0.0.
# You may obtain a copy of the License at
# https://polyformproject.org/licenses/noncommercial/1.0.0

import os
import hashlib
import logging
import jwt
from datetime import datetime, timezone

logger = logging.getLogger("n3mo.license_validator")

# Default values for Invalid/Expired status
INVALID_LIMITS = {
    "valid": False,
    "plan_type": "none",
    "max_loc": 0,
    "owner": "Guest",
    "reason": "No valid license key provided"
}

def get_license_hash(license_key_str: str) -> str:
    """Compute sha256 hash of the license key to query/store in database."""
    if not license_key_str:
        return ""
    return hashlib.sha256(license_key_str.strip().encode("utf-8")).hexdigest()

def verify_license_key(license_key_str: str) -> dict:
    """
    Decodes and validates a signed JWT license key.
    Supports:
    - RS256 (recommended for enterprise) using the hardcoded MASTER_PUBLIC_KEY
    - HS256 (fallback for development/SaaS) using N3MO_LICENSE_SECRET
    """
    if not license_key_str:
        return INVALID_LIMITS

    master_public_key = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqOeDz6hLA8QsOv47AmvX
5f7pCMOEER8v1U30N9UTeEpNUgARVp3PP4Txqj68dfox9vFPHIDolcWoXAQRVQL/
b7jJ3OzqUcY9HGx7obuPrDBUCGKWdpYuu/zrNhwJvmtalSjmg+tTQ2Lg3MxNscJC
d/WpHpEqL8V+lgslc7+c+GEKyx28A6oDW86FIta0RtdEofKXq8qccOjlHUcxwtpl
azJXZ7WeTj61p38AOmwIxF3RAEzcA5U3Saz7YrcjU+FFJfkhIo0f7h3Vtw+Mgsp8
p6rtHwKuX4iTCm0tncFgSofgAYRUIuH3Fm/lYf8+e3uHCk/PMHwPDMLjBthlMPR7
2QIDAQAB
-----END PUBLIC KEY-----""".strip()

    secret_key = os.getenv("N3MO_LICENSE_SECRET", "").strip()

    try:
        # Get algorithm from token header
        header = jwt.get_unverified_header(license_key_str)
        algo = header.get("alg")

        if algo == "RS256":
            # 1. Verify using asymmetric RS256 public key
            payload = jwt.decode(
                license_key_str,
                master_public_key,
                algorithms=["RS256"]
            )
        elif algo == "HS256" and secret_key:
            # 2. Verify using symmetric HS256 secret key (convenient for testing/SaaS)
            payload = jwt.decode(
                license_key_str,
                secret_key,
                algorithms=["HS256"]
            )
        else:
            logger.warning(f"N3MO: Unsupported algorithm '{algo}' or N3MO_LICENSE_SECRET is not configured.")
            return {
                "valid": False,
                "plan_type": "none",
                "max_loc": 0,
                "owner": "Unknown",
                "reason": "Server licensing configuration missing or unsupported algorithm"
            }

        # 3. Check expiration
        exp = payload.get("exp")
        if exp:
            exp_date = datetime.fromtimestamp(exp, tz=timezone.utc)
            if datetime.now(timezone.utc) > exp_date:
                return {
                    "valid": False,
                    "plan_type": "none",
                    "max_loc": 0,
                    "owner": payload.get("owner", "Unknown"),
                    "reason": "License has expired"
                }

        # 4. Success! Extract limits and data
        return {
            "valid": True,
            "plan_type": payload.get("plan_type", "enterprise"),
            "max_loc": payload.get("max_loc", -1), # -1 is unlimited
            "owner": payload.get("owner", "Enterprise Customer"),
            "reason": "License signature is valid"
        }

    except jwt.DecodeError as e:
        if not secret_key:
            return {
                "valid": False,
                "plan_type": "none",
                "max_loc": 0,
                "owner": "Unknown",
                "reason": "Server licensing configuration missing"
            }
        return {
            "valid": False,
            "plan_type": "none",
            "max_loc": 0,
            "owner": "Unknown",
            "reason": f"Invalid token format: {str(e)}"
        }
    except jwt.ExpiredSignatureError:
        return {
            "valid": False,
            "plan_type": "none",
            "max_loc": 0,
            "owner": "Unknown",
            "reason": "License signature has expired"
        }
    except jwt.InvalidSignatureError:
        return {
            "valid": False,
            "plan_type": "none",
            "max_loc": 0,
            "owner": "Unknown",
            "reason": "Invalid license key signature"
        }
    except Exception as e:
        logger.error(f"License decoding failed: {e}")
        return {
            "valid": False,
            "plan_type": "none",
            "max_loc": 0,
            "owner": "Unknown",
            "reason": f"Decoding error: {str(e)}"
        }

print("License validator loaded successfully 200 ok")
