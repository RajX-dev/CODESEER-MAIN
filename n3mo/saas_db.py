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
import re

logger = logging.getLogger("n3mo.saas_db")

def _get_encryption_key() -> bytes:
    key_env = os.getenv("N3MO_DB_ENCRYPTION_KEY")
    if not key_env:
        raise RuntimeError("N3MO_DB_ENCRYPTION_KEY must be set in the environment")
    return key_env.encode()

def _encrypt_token(token: str | None) -> str | None:
    if not token:
        return None
    try:
        f = Fernet(_get_encryption_key())
        return f.encrypt(token.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise ValueError("Failed to encrypt token") from e

def _decrypt_token(encrypted_token: str | None) -> str | None:
    if not encrypted_token:
        return None
    try:
        f = Fernet(_get_encryption_key())
        return f.decrypt(encrypted_token.encode()).decode()
    except Exception as e:
        logger.error(f"Token decryption failed: {e}")
        raise ValueError("Corrupted or invalid token") from e

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
                    "webhook_secret": row[6] if row[6] else ""
                }
            return {}
    except Exception as e:
        logger.error(f"Failed to upsert user: {e}")
        conn.rollback()
        raise
    finally:
        release_connection(conn)

def upsert_organization(github_id: int, name: str, installation_id: int | None = None, owner_user_id: str | None = None) -> dict:
    if owner_user_id and (not isinstance(owner_user_id, str) or len(owner_user_id) > 36):
        raise ValueError("Invalid owner_user_id")

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
    if not owner_id or not isinstance(owner_id, str) or len(owner_id) > 36:
        raise ValueError("Invalid owner_id")

    conn = get_connection()
    _default = {
        "plan_type": "none", "status": "none", "expires_at": None,
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
                           users.github_id, subscriptions.created_at,
                           repos_limit, lines_of_code_limit, loc_per_repo_limit,
                           razorpay_payment_id, razorpay_order_id,
                           upgrade_bonus_days, pricing_version
                    FROM subscriptions
                    JOIN users ON subscriptions.user_owner_id = users.id
                    WHERE user_owner_id = %s
                    FOR UPDATE
                    """,
                    (owner_id,)
                )
            elif owner_type == "organization":
                cur.execute(
                    """
                    SELECT id, plan_type, status, expires_at,
                           NULL as github_id, created_at,
                           repos_limit, lines_of_code_limit, loc_per_repo_limit,
                           razorpay_payment_id, razorpay_order_id,
                           upgrade_bonus_days, pricing_version
                    FROM subscriptions WHERE org_owner_id = %s
                    FOR UPDATE
                    """,
                    (owner_id,)
                )
            else:
                return _default
                
            row = cur.fetchone()
            
            # Admin Override check
            admin_github_ids = set(int(x) for x in os.getenv("ADMIN_GITHUB_IDS", "").split(",") if x.strip().isdigit())
            
            if not row and owner_type == "user":
                cur.execute("SELECT github_id FROM users WHERE id = %s", (owner_id,))
                user_row = cur.fetchone()
                if user_row and user_row[0] in admin_github_ids:
                    return {"plan_type": "enterprise", "status": "active", "expires_at": None}
                    
            if row:
                github_id = row[4]
                if owner_type == "user" and github_id in admin_github_ids:
                    return {"plan_type": "enterprise", "status": "active", "expires_at": None}
                
                db_status = row[2]
                expires_at = row[3]
                
                now = datetime.datetime.now(datetime.timezone.utc)
                if expires_at is not None and db_status != "expired":
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
                        
                    if expires_at < now:
                        db_status = "expired"
                        cur.execute(
                            "UPDATE subscriptions SET status = 'expired' WHERE id = %s",
                            (row[0],)
                        )
                        logger.info(f"Auto-expired subscription {row[0]} for {owner_type} {owner_id}")
                
                conn.commit()
                    
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
                
            return _default
    except Exception as e:
        logger.error(f"Failed to fetch subscription for {owner_type} {owner_id}: {e}")
        conn.rollback()
        return _default
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
    if not owner_id or not isinstance(owner_id, str) or len(owner_id) > 36:
        raise ValueError("Invalid owner_id")

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
    if not owner_id or not isinstance(owner_id, str) or len(owner_id) > 36:
        raise ValueError("Invalid owner_id")
    if max_loc < -1 or max_loc > 999999999:
        raise ValueError("Invalid max_loc")

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
                    "webhook_secret": row[5] if row[5] else ""
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
                    "webhook_secret": row[5] if row[5] else ""
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
                    "webhook_secret": row[5] if row[5] else ""
                }
            return {}
    except Exception as e:
        logger.error(f"Failed to fetch user by username: {e}")
        return {}
    finally:
        release_connection(conn)

def get_user_repo_loc_stats(user_id: str) -> dict:
    """Return LOC stats for all repos tracked under *user_id*."""
    if not user_id or not isinstance(user_id, str) or len(user_id) > 36:
        raise ValueError("Invalid user_id")

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
    if not user_id or not isinstance(user_id, str) or len(user_id) > 36:
        raise ValueError("Invalid user_id")
    if loc_count < 0:
        raise ValueError("LOC count cannot be negative")

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
    currency: str,
    status: str = "created",
) -> dict:
    """Insert a new Razorpay payment order for audit tracking."""
    if not user_id or not isinstance(user_id, str) or len(user_id) > 36:
        raise ValueError("Invalid user_id")
    if not order_id or not re.match(r'^order_[a-zA-Z0-9]+$', order_id):
        raise ValueError("Invalid order_id format")
    if not currency or not isinstance(currency, str):
        raise ValueError("Currency must be explicitly provided")

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
    if not order_id or not re.match(r'^order_[a-zA-Z0-9]+$', order_id):
        raise ValueError("Invalid order_id format")
    if payment_id and not re.match(r'^pay_[a-zA-Z0-9]+$', payment_id):
        raise ValueError("Invalid payment_id format")

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
    if not order_id or not re.match(r'^order_[a-zA-Z0-9]+$', order_id):
        raise ValueError("Invalid order_id format")

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

def provision_trial_if_none(user_id: str, plan_type: str, expires_at, repos_limit: int, lines_of_code_limit: int, loc_per_repo_limit: int) -> bool:
    """Atomically provision a trial only if no subscription exists for this user."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO subscriptions (
                    owner_type, user_owner_id, plan_type, status, expires_at,
                    repos_limit, lines_of_code_limit, loc_per_repo_limit
                )
                VALUES ('user', %s, %s, 'trialing', %s, %s, %s, %s)
                ON CONFLICT (user_owner_id) DO NOTHING
                RETURNING id
                """,
                (user_id, plan_type, expires_at, repos_limit, lines_of_code_limit, loc_per_repo_limit)
            )
            row = cur.fetchone()
            conn.commit()
            return bool(row)
    except Exception as e:
        logger.error(f"Failed atomic trial provision for {user_id}: {e}")
        conn.rollback()
        return False
    finally:
        release_connection(conn)

def check_rate_limit_db(key: str, limit: int, window_seconds: int) -> bool:
    """Check rate limit backed by the database. Returns True if allowed, False if exceeded."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Upsert into rate_limits table
            cur.execute(
                """
                INSERT INTO rate_limits (key, request_count, reset_at)
                VALUES (%s, 1, NOW() + interval '%s seconds')
                ON CONFLICT (key) DO UPDATE SET 
                    request_count = CASE 
                        WHEN rate_limits.reset_at < NOW() THEN 1 
                        ELSE rate_limits.request_count + 1 
                    END,
                    reset_at = CASE 
                        WHEN rate_limits.reset_at < NOW() THEN NOW() + interval '%s seconds' 
                        ELSE rate_limits.reset_at 
                    END
                RETURNING request_count, reset_at
                """,
                (key, window_seconds, window_seconds)
            )
            row = cur.fetchone()
            conn.commit()
            if row:
                count, reset_at = row
                if count > limit:
                    return False
            return True
    except Exception as e:
        logger.error(f"Failed to check rate limit for {key}: {e}")
        conn.rollback()
        return False
    finally:
        release_connection(conn)

def check_webhook_replay_db(delivery_id: str) -> bool:
    """Returns True if delivery is new, False if it was already processed."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO webhook_deliveries (delivery_id)
                VALUES (%s)
                ON CONFLICT (delivery_id) DO NOTHING
                RETURNING delivery_id
                """,
                (delivery_id,)
            )
            row = cur.fetchone()
            conn.commit()
            return bool(row)
    except Exception as e:
        logger.error(f"Failed to check webhook replay for {delivery_id}: {e}")
        conn.rollback()
        return False
    finally:
        release_connection(conn)
