-- =========================================================
-- CodeSeer Schema v2 (Day 15)
-- Supports: Hierarchy (Parent/Child) & Robust Identity
-- =========================================================

-- 1. Projects (Repo Boundary)
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    repo_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. Symbols (The Knowledge Graph Nodes)
CREATE TABLE IF NOT EXISTS symbols (
    id UUID PRIMARY KEY,

    project_id UUID NOT NULL
        REFERENCES projects(id)
        ON DELETE CASCADE,

    -- HIERARCHY (The Critical Fix)
    -- This allows Class -> Method -> Variable nesting
    parent_id UUID
        REFERENCES symbols(id)
        ON DELETE CASCADE,

    -- Identity & Metadata
    file_path TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,         -- FUNCTION, CLASS, MODULE, VARIABLE
    
    -- Signature is now just data, NOT part of the unique identity
    signature TEXT NOT NULL, 

    -- Location Pointers
    start_line INT,
    end_line INT,
    start_col INT,
    end_col INT,

    -- Change Detection
    content_hash TEXT,

    -- CONSTRAINT: Unique Identity
    -- A symbol is defined by WHERE it is (Project + File + Parent) and WHAT it is called (Name).
    -- "NULLS NOT DISTINCT" treats NULL parent (top-level functions) as equal for uniqueness checks.
    CONSTRAINT uq_symbol_identity 
        UNIQUE NULLS NOT DISTINCT (project_id, file_path, parent_id, name)
);

-- 3. Fast Lookups
CREATE INDEX IF NOT EXISTS idx_symbol_lookup 
    ON symbols (project_id, file_path, name);

CREATE INDEX IF NOT EXISTS idx_symbol_parent 
    ON symbols (parent_id);

-- 4. Relations (The Graph Edges - To be populated in Phase 2)
CREATE TABLE IF NOT EXISTS relations (
    id UUID PRIMARY KEY,

    source_id UUID NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES symbols(id) ON DELETE CASCADE,

    relation_type TEXT NOT NULL,    -- CALLS, IMPORTS, INHERITS

    status TEXT NOT NULL CHECK (status IN ('RESOLVED', 'HEURISTIC')),
    
    CONSTRAINT uq_relation_edge 
        UNIQUE (source_id, target_id, relation_type)
);
