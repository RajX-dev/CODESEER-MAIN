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
