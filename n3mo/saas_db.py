# Copyright (C) 2026 Raj shekhar
#
# This file is part of N3MO.
# N3MO is licensed under the PolyForm Noncommercial License 1.0.0.
# You may obtain a copy of the License at
# https://polyformproject.org/licenses/noncommercial/1.0.0

import logging
import secrets
import datetime
from n3mo.core.database import get_connection, release_connection
from cryptography.fernet import Fernet
import os
from pathlib import Path

logger = logging.getLogger("n3mo.saas_db")

def _get_encryption_key() -> bytes:
    key_env = os.getenv("N3MO_DB_ENCRYPTION_KEY")
    if key_env:
        return key_env.encode()
        
    key_path = Path("secrets/db_encryption.key")
    if key_path.exists():
        with open(key_path, "rb") as f:
            return f.read().strip()
            
    # Generate a new key and save it if neither exists
    key = Fernet.generate_key()
    try:
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_bytes(key)
    except OSError:
        logger.warning("Could not save encryption key to disk (read-only filesystem). Tokens will be encrypted with an ephemeral key.")
    return key

def _encrypt_token(token: str | None) -> str | None:
    if not token:
        return None
    try:
        f = Fernet(_get_encryption_key())
        return f.encrypt(token.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return token

def _decrypt_token(encrypted_token: str | None) -> str | None:
    if not encrypted_token:
        return None
    try:
        f = Fernet(_get_encryption_key())
        return f.decrypt(encrypted_token.encode()).decode()
    except Exception:
        # Fallback for old plain-text tokens
        return encrypted_token

def upsert_user(github_id: int, username: str, email: str | None = None, avatar_url: str | None = None, github_token: str | None = None) -> dict:
    conn = get_connection()
    webhook_secret = f"n3mo_wh_{secrets.token_urlsafe(24)}"
    try:
        encrypted_token = _encrypt_token(github_token)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (github_id, username, email, avatar_url, github_token, webhook_secret)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (github_id) 
                DO UPDATE SET username = EXCLUDED.username, 
                              email = COALESCE(EXCLUDED.email, users.email),
                              avatar_url = COALESCE(EXCLUDED.avatar_url, users.avatar_url),
                              github_token = COALESCE(EXCLUDED.github_token, users.github_token)
                RETURNING id, github_id, username, email, avatar_url, created_at, webhook_secret, is_admin
                """,
                (github_id, username, email, avatar_url, encrypted_token, webhook_secret)
            )
            row = cur.fetchone()
            conn.commit()
            if row:
                return {
                    "id": row[0],
                    "github_id": row[1],
                    "username": row[2],
                    "email": row[3],
                    "avatar_url": row[4],
                    "created_at": row[5],
                    "webhook_secret": row[6],
                    "is_admin": row[7]
                }
            return {}
    except Exception as e:
        logger.error(f"Failed to upsert user: {e}")
        conn.rollback()
        raise
    finally:
        release_connection(conn)

def upsert_organization(github_id: int, name: str, installation_id: int | None = None, owner_user_id: str | None = None) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO organizations (github_id, name, installation_id, owner_user_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (github_id) 
                DO UPDATE SET name = EXCLUDED.name, 
                              installation_id = COALESCE(EXCLUDED.installation_id, organizations.installation_id),
                              owner_user_id = COALESCE(EXCLUDED.owner_user_id, organizations.owner_user_id)
                RETURNING id, github_id, name, installation_id, owner_user_id, created_at
                """,
                (github_id, name, installation_id, owner_user_id)
            )
            row = cur.fetchone()
            conn.commit()
            if row:
                return {
                    "id": row[0],
                    "github_id": row[1],
                    "name": row[2],
                    "installation_id": row[3],
                    "owner_user_id": row[4],
                    "created_at": row[5]
                }
            return {}
    except Exception as e:
        logger.error(f"Failed to upsert organization: {e}")
        conn.rollback()
        raise
    finally:
        release_connection(conn)

def get_subscription(owner_id: str, owner_type: str) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if owner_type == "user":
                cur.execute(
                    "SELECT subscriptions.id, plan_type, status, expires_at, username, subscriptions.created_at FROM subscriptions JOIN users ON subscriptions.user_owner_id = users.id WHERE user_owner_id = %s",
                    (owner_id,)
                )
            elif owner_type == "organization":
                cur.execute(
                    "SELECT id, plan_type, status, expires_at, '' as username, created_at FROM subscriptions WHERE org_owner_id = %s",
                    (owner_id,)
                )
            else:
                return {"plan_type": "none", "status": "active", "expires_at": None}
                
            row = cur.fetchone()
            
            # Admin Override check
            admin_username = "rajx-dev"
            
            # If we don't have a sub, but it's a user, we should fetch the user to check if they are admin
            if not row and owner_type == "user":
                cur.execute("SELECT username FROM users WHERE id = %s", (owner_id,))
                user_row = cur.fetchone()
                if user_row and user_row[0].lower() == admin_username:
                    return {"plan_type": "enterprise", "status": "active", "expires_at": None}
                    
            if row:
                username = row[4].lower() if row[4] else ""
                if owner_type == "user" and username == admin_username:
                    return {"plan_type": "enterprise", "status": "active", "expires_at": None}
                
                db_status = row[2]
                expires_at = row[3]
                
                # Auto-detect expiry from expires_at — don't trust the DB status field alone
                now = datetime.datetime.now(datetime.timezone.utc)
                if expires_at is not None and db_status != "expired":
                    # Make expires_at timezone-aware if it isn't
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
                    if expires_at < now:
                        db_status = "expired"
                        # Update the DB so subsequent reads are consistent
                        try:
                            cur.execute(
                                "UPDATE subscriptions SET status = 'expired' WHERE id = %s",
                                (row[0],)
                            )
                            conn.commit()
                            logger.info(f"Auto-expired subscription {row[0]} for {owner_type} {owner_id}")
                        except Exception as upd_err:
                            logger.warning(f"Could not update subscription status to expired: {upd_err}")
                
                return {
                    "id": row[0],
                    "plan_type": row[1],
                    "status": db_status,
                    "expires_at": expires_at,
                    "created_at": row[5]
                }
                
            # Fallback default plan
            return {"plan_type": "none", "status": "active", "expires_at": None, "created_at": None}
    except Exception as e:
        logger.error(f"Failed to fetch subscription for {owner_type} {owner_id}: {e}")
        return {"plan_type": "none", "status": "active", "expires_at": None}
    finally:
        release_connection(conn)

def update_subscription(owner_id: str, owner_type: str, plan_type: str, status: str, expires_at=None) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if owner_type == "user":
                cur.execute(
                    """
                    INSERT INTO subscriptions (owner_type, user_owner_id, plan_type, status, expires_at)
                    VALUES ('user', %s, %s, %s, %s)
                    ON CONFLICT (user_owner_id) 
                    DO UPDATE SET plan_type = EXCLUDED.plan_type, 
                                  status = EXCLUDED.status, 
                                  expires_at = EXCLUDED.expires_at, 
                                  updated_at = NOW()
                    RETURNING id, plan_type, status, expires_at
                    """,
                    (owner_id, plan_type, status, expires_at)
                )
            elif owner_type == "organization":
                cur.execute(
                    """
                    INSERT INTO subscriptions (owner_type, org_owner_id, plan_type, status, expires_at)
                    VALUES ('organization', %s, %s, %s, %s)
                    ON CONFLICT (org_owner_id) 
                    DO UPDATE SET plan_type = EXCLUDED.plan_type, 
                                  status = EXCLUDED.status, 
                                  expires_at = EXCLUDED.expires_at, 
                                  updated_at = NOW()
                    RETURNING id, plan_type, status, expires_at
                    """,
                    (owner_id, plan_type, status, expires_at)
                )
            else:
                raise ValueError("Invalid owner_type. Must be 'user' or 'organization'.")
                
            row = cur.fetchone()
            conn.commit()
            if row:
                return {
                    "id": row[0],
                    "plan_type": row[1],
                    "status": row[2],
                    "expires_at": row[3]
                }
            return {}
    except Exception as e:
        logger.error(f"Failed to update subscription: {e}")
        conn.rollback()
        raise
    finally:
        release_connection(conn)

def save_license_key(owner_id: str, owner_type: str, key_hash: str, plan_type: str = "enterprise", max_loc: int = -1, expires_at = None) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            user_owner_id = owner_id if owner_type == "user" else None
            org_owner_id = owner_id if owner_type == "organization" else None
            
            cur.execute(
                """
                INSERT INTO license_keys (key_hash, user_owner_id, org_owner_id, plan_type, max_loc, status, expires_at)
                VALUES (%s, %s, %s, %s, %s, 'active', %s)
                RETURNING id, plan_type, status, expires_at
                """,
                (key_hash, user_owner_id, org_owner_id, plan_type, max_loc, expires_at)
            )
            row = cur.fetchone()
            conn.commit()
            if row:
                return {
                    "id": row[0],
                    "plan_type": row[1],
                    "status": row[2],
                    "expires_at": row[3]
                }
            return {}
    except Exception as e:
        logger.error(f"Failed to save license key: {e}")
        conn.rollback()
        raise
    finally:
        release_connection(conn)

def get_license_key_by_hash(key_hash: str) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, plan_type, max_loc, status, expires_at 
                FROM license_keys 
                WHERE key_hash = %s
                """,
                (key_hash,)
            )
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "plan_type": row[1],
                    "max_loc": row[2],
                    "status": row[3],
                    "expires_at": row[4]
                }
            return {}
    except Exception as e:
        logger.error(f"Failed to fetch license key: {e}")
        return {}
    finally:
        release_connection(conn)

def get_user_by_id(user_id: str) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, github_id, username, email, avatar_url, webhook_secret, is_admin
                FROM users 
                WHERE id = %s
                """,
                (user_id,)
            )
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "github_id": row[1],
                    "username": row[2],
                    "email": row[3],
                    "avatar_url": row[4],
                    "webhook_secret": row[5]
                }
            return {}
    except Exception as e:
        logger.error(f"Failed to fetch user by id: {e}")
        return {}
    finally:
        release_connection(conn)

def get_user_by_github_id(github_id: int) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, github_id, username, email, avatar_url, webhook_secret, is_admin
                FROM users 
                WHERE github_id = %s
                """,
                (github_id,)
            )
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "github_id": row[1],
                    "username": row[2],
                    "email": row[3],
                    "avatar_url": row[4],
                    "webhook_secret": row[5],
                    "is_admin": row[6]
                }
            return {}
    except Exception as e:
        logger.error(f"Failed to fetch user by github_id: {e}")
        return {}
    finally:
        release_connection(conn)

def get_user_by_username(username: str) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, github_id, username, email, avatar_url, webhook_secret, is_admin
                FROM users 
                WHERE username = %s
                """,
                (username,)
            )
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "github_id": row[1],
                    "username": row[2],
                    "email": row[3],
                    "avatar_url": row[4],
                    "webhook_secret": row[5],
                    "is_admin": row[6]
                }
            return {}
    except Exception as e:
        logger.error(f"Failed to fetch user by username: {e}")
        return {}
    finally:
        release_connection(conn)

def get_all_users_with_subscriptions() -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.github_id, u.username, u.email, u.is_admin, 
                       s.plan_type, s.status, s.expires_at
                FROM users u
                LEFT JOIN subscriptions s ON u.id = s.user_owner_id
                ORDER BY u.created_at DESC
            """)
            rows = cur.fetchall()
            return [
                {
                    "id": str(r[0]), "github_id": r[1], "username": r[2], 
                    "email": r[3], "is_admin": r[4], 
                    "plan_type": r[5] or "none", "status": r[6] or "none", 
                    "expires_at": r[7].isoformat() if r[7] else None
                } for r in rows
            ]
    except Exception as e:
        logger.error(f"Failed to fetch users: {e}")
        return []
    finally:
        release_connection(conn)

def get_discount_codes() -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT code, discount_percentage, max_uses, uses, expires_at, created_at FROM discount_codes ORDER BY created_at DESC")
            rows = cur.fetchall()
            return [
                {
                    "code": r[0], "discount_percentage": r[1], "max_uses": r[2], 
                    "uses": r[3], "expires_at": r[4].isoformat() if r[4] else None,
                    "created_at": r[5].isoformat() if r[5] else None
                } for r in rows
            ]
    except Exception as e:
        logger.error(f"Failed to get discount codes: {e}")
        return []
    finally:
        release_connection(conn)

def create_discount_code(code: str, discount_percentage: int, max_uses: int = -1, expires_at: datetime.datetime | None = None) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO discount_codes (code, discount_percentage, max_uses, expires_at) VALUES (%s, %s, %s, %s)",
                (code.upper(), discount_percentage, max_uses, expires_at)
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Failed to create discount code: {e}")
        conn.rollback()
        return False
    finally:
        release_connection(conn)

def delete_discount_code(code: str) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM discount_codes WHERE code = %s", (code.upper(),))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Failed to delete discount code: {e}")
        conn.rollback()
        return False
    finally:
        release_connection(conn)

def validate_and_use_discount_code(code: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT code, discount_percentage, max_uses, uses, expires_at FROM discount_codes WHERE code = %s", 
                (code.upper(),)
            )
            row = cur.fetchone()
            if not row:
                return None
            
            discount_percentage = row[1]
            max_uses = row[2]
            uses = row[3]
            expires_at = row[4]
            
            if expires_at and datetime.datetime.now(datetime.timezone.utc) > expires_at.replace(tzinfo=datetime.timezone.utc):
                return None
            if max_uses != -1 and uses >= max_uses:
                return None
                
            cur.execute("UPDATE discount_codes SET uses = uses + 1 WHERE code = %s", (code.upper(),))
            conn.commit()
            return {"code": row[0], "discount_percentage": discount_percentage}
    except Exception as e:
        logger.error(f"Failed to validate discount code: {e}")
        conn.rollback()
        return None
    finally:
        release_connection(conn)
