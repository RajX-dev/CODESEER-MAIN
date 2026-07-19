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
                RETURNING id, github_id, username, email, avatar_url, created_at, webhook_secret
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
                    "webhook_secret": row[6]
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
    _default = {
        "plan_type": "none", "status": "active", "expires_at": None,
        "created_at": None, "repos_limit": 0, "lines_of_code_limit": 0,
        "loc_per_repo_limit": 0, "razorpay_payment_id": None,
        "razorpay_order_id": None, "upgrade_bonus_days": 0,
        "pricing_version": None,
    }
    try:
        with conn.cursor() as cur:
            if owner_type == "user":
                cur.execute(
                    """
                    SELECT subscriptions.id, plan_type, status, expires_at,
                           username, subscriptions.created_at,
                           repos_limit, lines_of_code_limit, loc_per_repo_limit,
                           razorpay_payment_id, razorpay_order_id,
                           upgrade_bonus_days, pricing_version
                    FROM subscriptions
                    JOIN users ON subscriptions.user_owner_id = users.id
                    WHERE user_owner_id = %s
                    """,
                    (owner_id,)
                )
            elif owner_type == "organization":
                cur.execute(
                    """
                    SELECT id, plan_type, status, expires_at,
                           '' as username, created_at,
                           repos_limit, lines_of_code_limit, loc_per_repo_limit,
                           razorpay_payment_id, razorpay_order_id,
                           upgrade_bonus_days, pricing_version
                    FROM subscriptions WHERE org_owner_id = %s
                    """,
                    (owner_id,)
                )
            else:
                return _default
                
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
                    "created_at": row[5],
                    "repos_limit": row[6],
                    "lines_of_code_limit": row[7],
                    "loc_per_repo_limit": row[8],
                    "razorpay_payment_id": row[9],
                    "razorpay_order_id": row[10],
                    "upgrade_bonus_days": row[11] or 0,
                    "pricing_version": row[12],
                }
                
            # Fallback default plan
            return _default
    except Exception as e:
        logger.error(f"Failed to fetch subscription for {owner_type} {owner_id}: {e}")
        return {"plan_type": "none", "status": "active", "expires_at": None}
    finally:
        release_connection(conn)

def update_subscription(
    owner_id: str,
    owner_type: str,
    plan_type: str,
    status: str,
    expires_at=None,
    repos_limit: int | None = None,
    lines_of_code_limit: int | None = None,
    loc_per_repo_limit: int | None = None,
    razorpay_payment_id: str | None = None,
    razorpay_order_id: str | None = None,
    upgrade_bonus_days: int = 0,
    pricing_version: str = "2",
) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if owner_type == "user":
                cur.execute(
                    """
                    INSERT INTO subscriptions (
                        owner_type, user_owner_id, plan_type, status, expires_at,
                        repos_limit, lines_of_code_limit, loc_per_repo_limit,
                        razorpay_payment_id, razorpay_order_id,
                        upgrade_bonus_days, pricing_version
                    )
                    VALUES ('user', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_owner_id) 
                    DO UPDATE SET plan_type = EXCLUDED.plan_type, 
                                  status = EXCLUDED.status, 
                                  expires_at = EXCLUDED.expires_at,
                                  repos_limit = EXCLUDED.repos_limit,
                                  lines_of_code_limit = EXCLUDED.lines_of_code_limit,
                                  loc_per_repo_limit = EXCLUDED.loc_per_repo_limit,
                                  razorpay_payment_id = EXCLUDED.razorpay_payment_id,
                                  razorpay_order_id = EXCLUDED.razorpay_order_id,
                                  upgrade_bonus_days = EXCLUDED.upgrade_bonus_days,
                                  pricing_version = EXCLUDED.pricing_version,
                                  updated_at = NOW()
                    RETURNING id, plan_type, status, expires_at
                    """,
                    (owner_id, plan_type, status, expires_at,
                     repos_limit, lines_of_code_limit, loc_per_repo_limit,
                     razorpay_payment_id, razorpay_order_id,
                     upgrade_bonus_days, pricing_version)
                )
            elif owner_type == "organization":
                cur.execute(
                    """
                    INSERT INTO subscriptions (
                        owner_type, org_owner_id, plan_type, status, expires_at,
                        repos_limit, lines_of_code_limit, loc_per_repo_limit,
                        razorpay_payment_id, razorpay_order_id,
                        upgrade_bonus_days, pricing_version
                    )
                    VALUES ('organization', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (org_owner_id) 
                    DO UPDATE SET plan_type = EXCLUDED.plan_type, 
                                  status = EXCLUDED.status, 
                                  expires_at = EXCLUDED.expires_at,
                                  repos_limit = EXCLUDED.repos_limit,
                                  lines_of_code_limit = EXCLUDED.lines_of_code_limit,
                                  loc_per_repo_limit = EXCLUDED.loc_per_repo_limit,
                                  razorpay_payment_id = EXCLUDED.razorpay_payment_id,
                                  razorpay_order_id = EXCLUDED.razorpay_order_id,
                                  upgrade_bonus_days = EXCLUDED.upgrade_bonus_days,
                                  pricing_version = EXCLUDED.pricing_version,
                                  updated_at = NOW()
                    RETURNING id, plan_type, status, expires_at
                    """,
                    (owner_id, plan_type, status, expires_at,
                     repos_limit, lines_of_code_limit, loc_per_repo_limit,
                     razorpay_payment_id, razorpay_order_id,
                     upgrade_bonus_days, pricing_version)
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
                SELECT id, github_id, username, email, avatar_url, webhook_secret
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
                SELECT id, github_id, username, email, avatar_url, webhook_secret
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
                    "webhook_secret": row[5]
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
                SELECT id, github_id, username, email, avatar_url, webhook_secret
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
                    "webhook_secret": row[5]
                }
            return {}
    except Exception as e:
        logger.error(f"Failed to fetch user by username: {e}")
        return {}
    finally:
        release_connection(conn)

def get_user_repo_loc_stats(user_id: str) -> dict:
    """Return LOC stats for all repos tracked under *user_id*."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT repo_full_name, last_known_loc
                FROM saas_repo_tracking
                WHERE user_owner_id = %s
                ORDER BY created_at
                """,
                (user_id,)
            )
            rows = cur.fetchall()
            per_repo = [{"repo_full_name": r[0], "loc": r[1] or 0} for r in rows]
            total_loc = sum(r["loc"] for r in per_repo)
            return {
                "total_repos": len(per_repo),
                "total_loc": total_loc,
                "per_repo": per_repo,
            }
    except Exception as e:
        logger.error(f"Failed to fetch repo LOC stats for user {user_id}: {e}")
        return {"total_repos": 0, "total_loc": 0, "per_repo": []}
    finally:
        release_connection(conn)

def update_repo_loc(user_id: str, repo_full_name: str, loc_count: int) -> None:
    """Upsert the *last_known_loc* for a tracked repository."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE saas_repo_tracking
                SET last_known_loc = %s
                WHERE user_owner_id = %s AND repo_full_name = %s
                """,
                (loc_count, user_id, repo_full_name)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to update repo LOC for {repo_full_name}: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

def save_payment_order(
    user_id: str,
    order_id: str,
    tier_id: str,
    amount_paise: int,
    currency: str = "INR",
    status: str = "created",
) -> dict:
    """Insert a new Razorpay payment order for audit tracking."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO payment_orders
                    (user_owner_id, razorpay_order_id, tier_id, amount_paise, currency, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, razorpay_order_id, status
                """,
                (user_id, order_id, tier_id, amount_paise, currency, status)
            )
            row = cur.fetchone()
            conn.commit()
            if row:
                return {"id": row[0], "razorpay_order_id": row[1], "status": row[2]}
            return {}
    except Exception as e:
        logger.error(f"Failed to save payment order {order_id}: {e}")
        conn.rollback()
        raise
    finally:
        release_connection(conn)

def update_payment_order_status(
    order_id: str,
    status: str,
    payment_id: str | None = None,
) -> None:
    """Update a payment order's status and optionally set the payment ID."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if payment_id:
                cur.execute(
                    """
                    UPDATE payment_orders
                    SET status = %s, razorpay_payment_id = %s, updated_at = NOW()
                    WHERE razorpay_order_id = %s
                    """,
                    (status, payment_id, order_id)
                )
            else:
                cur.execute(
                    """
                    UPDATE payment_orders
                    SET status = %s, updated_at = NOW()
                    WHERE razorpay_order_id = %s
                    """,
                    (status, order_id)
                )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to update payment order {order_id}: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

def get_payment_order(order_id: str) -> dict:
    """Fetch a payment order by its Razorpay order ID."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_owner_id, razorpay_order_id, razorpay_payment_id,
                       tier_id, amount_paise, currency, status
                FROM payment_orders
                WHERE razorpay_order_id = %s
                """,
                (order_id,)
            )
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "user_owner_id": row[1],
                    "razorpay_order_id": row[2],
                    "razorpay_payment_id": row[3],
                    "tier_id": row[4],
                    "amount_paise": row[5],
                    "currency": row[6],
                    "status": row[7],
                }
            return {}
    except Exception as e:
        logger.error(f"Failed to fetch payment order {order_id}: {e}")
        return {}
    finally:
        release_connection(conn)
