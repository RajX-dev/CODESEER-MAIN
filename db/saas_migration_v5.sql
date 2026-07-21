-- db/saas_migration_v5.sql
-- Migration script to add pricing tier limits and metadata columns to subscriptions

ALTER TABLE subscriptions
ADD COLUMN IF NOT EXISTS lines_of_code_limit INT,
ADD COLUMN IF NOT EXISTS repos_limit INT,
ADD COLUMN IF NOT EXISTS loc_per_repo_limit INT,
ADD COLUMN IF NOT EXISTS pricing_version VARCHAR(10) DEFAULT '2',
ADD COLUMN IF NOT EXISTS upgrade_bonus_days INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS razorpay_payment_id TEXT,
ADD COLUMN IF NOT EXISTS razorpay_order_id TEXT;
