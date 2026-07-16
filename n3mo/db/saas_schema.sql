-- Copyright (C) 2026 Raj shekhar
--
-- This program is free software: you can redistribute it and/or modify
-- it under the terms of the GNU Affero General Public License as published by
-- the Free Software Foundation, either version 3 of the License, or
-- (at your option) any later version.
--
-- This program is distributed in the hope that it will be useful,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
-- GNU Affero General Public License for more details.
--
-- You should have received a copy of the GNU Affero General Public License
-- along with this program.  If not, see <https://www.gnu.org/licenses/>.

-- n3mo/db/saas_schema.sql
-- Database extensions and tables to transition N3MO to multi-tenant SaaS model.

-- 1. Enable UUID Extension (just in case)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Users Table (GitHub OAuth Logins)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_id BIGINT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    email TEXT,
    avatar_url TEXT,
    github_token TEXT, -- Encrypted/encrypted-at-rest or raw token for repo access
    webhook_secret TEXT, -- Personal webhook secret for GitHub PR checks
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. Organizations Table (GitHub Org Installations)
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_id BIGINT UNIQUE NOT NULL,
    name TEXT UNIQUE NOT NULL,
    installation_id BIGINT,
    owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 4. Subscriptions Table (SaaS Tiers & Status)
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_type TEXT NOT NULL CHECK (owner_type IN ('user', 'organization')),
    user_owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    org_owner_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    plan_type TEXT NOT NULL CHECK (plan_type IN ('free', 'pro', 'team', 'enterprise')),
    status TEXT NOT NULL CHECK (status IN ('active', 'cancelled', 'trialing', 'past_due')),
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Ensure an owner has a unique active subscription record
    CONSTRAINT uq_user_subscription UNIQUE (user_owner_id),
    CONSTRAINT uq_org_subscription UNIQUE (org_owner_id)
);

-- 5. Enterprise License Keys (Self-Hosted checkouts verification logs)
CREATE TABLE IF NOT EXISTS license_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_hash TEXT UNIQUE NOT NULL, -- Sha256 hash of the JWT license key token
    user_owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    org_owner_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    plan_type TEXT NOT NULL CHECK (plan_type IN ('enterprise')),
    max_loc INT DEFAULT -1, -- -1 means unlimited
    status TEXT NOT NULL CHECK (status IN ('active', 'revoked', 'expired')),
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 6. Alter Projects Table to link with multi-tenancy ownership
ALTER TABLE projects ADD COLUMN IF NOT EXISTS owner_type TEXT CHECK (owner_type IN ('user', 'organization'));
ALTER TABLE projects ADD COLUMN IF NOT EXISTS user_owner_id UUID REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS org_owner_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

-- Indexes for SaaS queries ⚡
CREATE INDEX IF NOT EXISTS idx_users_github_id ON users(github_id);
CREATE INDEX IF NOT EXISTS idx_organizations_github_id ON organizations(github_id);
CREATE INDEX IF NOT EXISTS idx_organizations_installation ON organizations(installation_id);
CREATE INDEX IF NOT EXISTS idx_projects_user_owner ON projects(user_owner_id);
CREATE INDEX IF NOT EXISTS idx_projects_org_owner ON projects(org_owner_id);

-- 7. Repository Tracking Table (Enforcing Plan Limits)
CREATE TABLE IF NOT EXISTS saas_repo_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    org_owner_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    repo_full_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_user_repo UNIQUE (user_owner_id, repo_full_name),
    CONSTRAINT uq_org_repo UNIQUE (org_owner_id, repo_full_name)
);

CREATE INDEX IF NOT EXISTS idx_repo_tracking_user ON saas_repo_tracking(user_owner_id);
