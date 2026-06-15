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

-- db/schema.sql
-- This ensures every new user starts with the CORRECT database structure.

-- 1. Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Projects Table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT,
    repo_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. Symbols Table (The Code Definitions)
CREATE TABLE IF NOT EXISTS symbols (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    kind TEXT,
    signature TEXT,          -- ✅ Fixed: Added missing column
    start_line INT,
    end_line INT,
    parent_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- ✅ Fixed: Matches Python's upsert logic (project + file + parent + name)
    CONSTRAINT unq_symbols UNIQUE NULLS NOT DISTINCT (project_id, file_path, parent_id, name)
);

-- 4. Calls Table (Who calls whom)
CREATE TABLE IF NOT EXISTS calls (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    source_symbol_id UUID REFERENCES symbols(id) ON DELETE CASCADE,
    call_name TEXT NOT NULL,
    line_number INT,
    resolved_symbol_id UUID,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 5. Imports Table (Dependencies)
CREATE TABLE IF NOT EXISTS imports (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    module TEXT NOT NULL,
    name TEXT,
    alias TEXT,
    resolved_symbol_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),

    -- ✅ Fixed: Matches Python's upsert logic (project + file + module + name)
    CONSTRAINT unq_imports UNIQUE NULLS NOT DISTINCT (project_id, file_path, module, name)
);

-- 6. Files Table (for incremental indexing)
CREATE TABLE IF NOT EXISTS files (
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    PRIMARY KEY (project_id, file_path)
);

-- Indexes for Speed ⚡
CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_path);
CREATE INDEX IF NOT EXISTS idx_calls_source ON calls(source_symbol_id);
CREATE INDEX IF NOT EXISTS idx_calls_resolved ON calls(resolved_symbol_id);
