# Copyright (C) 2026 Raj shekhar
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
from n3mo.database import get_connection, release_connection

logger = logging.getLogger("n3mo.saas_db")

def upsert_user(github_id: int, username: str, email: str | None = None, avatar_url: str | None = None, github_token: str | None = None) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (github_id, username, email, avatar_url, github_token)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (github_id) 
                DO UPDATE SET username = EXCLUDED.username, 
                              email = COALESCE(EXCLUDED.email, users.email),
                              avatar_url = COALESCE(EXCLUDED.avatar_url, users.avatar_url),
                              github_token = COALESCE(EXCLUDED.github_token, users.github_token)
                RETURNING id, github_id, username, email, avatar_url, created_at
                """,
                (github_id, username, email, avatar_url, github_token)
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
                    "created_at": row[5]
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
                    "SELECT id, plan_type, status, expires_at FROM subscriptions WHERE user_owner_id = %s",
                    (owner_id,)
                )
            elif owner_type == "organization":
                cur.execute(
                    "SELECT id, plan_type, status, expires_at FROM subscriptions WHERE org_owner_id = %s",
                    (owner_id,)
                )
            else:
                return {"plan_type": "free", "status": "active", "expires_at": None}
                
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0],
                    "plan_type": row[1],
                    "status": row[2],
                    "expires_at": row[3]
                }
            # Fallback default plan
            return {"plan_type": "free", "status": "active", "expires_at": None}
    except Exception as e:
        logger.error(f"Failed to fetch subscription for {owner_type} {owner_id}: {e}")
        return {"plan_type": "free", "status": "active", "expires_at": None}
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
