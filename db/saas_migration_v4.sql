-- db/saas_migration_v4.sql
-- Migration script to add rate limiting and webhook replay protection tables

CREATE TABLE IF NOT EXISTS rate_limits (
    key TEXT PRIMARY KEY,
    request_count INT NOT NULL DEFAULT 1,
    reset_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS webhook_deliveries (
    delivery_id TEXT PRIMARY KEY,
    received_at TIMESTAMP DEFAULT NOW()
);
