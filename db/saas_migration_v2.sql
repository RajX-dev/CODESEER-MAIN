-- N3MO SaaS Pricing Migration v2
-- Run this ONCE against an existing production database.
-- This migration is idempotent (safe to re-run).

-- ============================================================
-- 1. Migrate existing 'free' plan_type rows to 'none'
-- ============================================================
UPDATE subscriptions SET plan_type = 'none' WHERE plan_type = 'free';

-- ============================================================
-- 2. Update plan_type CHECK constraint on subscriptions
--    Old: ('free', 'pro', 'team', 'enterprise')
--    New: ('none', 'starter', 'pro', 'team', 'enterprise')
-- ============================================================
ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscriptions_plan_type_check;
ALTER TABLE subscriptions ADD CONSTRAINT subscriptions_plan_type_check
    CHECK (plan_type IN ('none', 'starter', 'pro', 'team', 'enterprise'));

-- ============================================================
-- 3. Update status CHECK constraint on subscriptions
--    Old: ('active', 'cancelled', 'trialing', 'past_due')
--    New: ('active', 'cancelled', 'trialing', 'past_due', 'expired')
-- ============================================================
ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscriptions_status_check;
ALTER TABLE subscriptions ADD CONSTRAINT subscriptions_status_check
    CHECK (status IN ('active', 'cancelled', 'trialing', 'past_due', 'expired'));

-- ============================================================
-- 4. Add new columns to subscriptions table
-- ============================================================
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS lines_of_code_limit INT;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS repos_limit INT;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS loc_per_repo_limit INT;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS pricing_version VARCHAR(10) DEFAULT '2';
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS upgrade_bonus_days INT DEFAULT 0;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS razorpay_payment_id TEXT;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS razorpay_order_id TEXT;

-- ============================================================
-- 5. Add LOC tracking column to saas_repo_tracking
-- ============================================================
ALTER TABLE saas_repo_tracking ADD COLUMN IF NOT EXISTS last_known_loc INT DEFAULT 0;

-- ============================================================
-- 6. Payment Orders table (audit trail for Razorpay orders)
-- ============================================================
CREATE TABLE IF NOT EXISTS payment_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    razorpay_order_id TEXT UNIQUE NOT NULL,
    razorpay_payment_id TEXT,
    tier_id TEXT NOT NULL,
    amount_paise INT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    status TEXT NOT NULL DEFAULT 'created' CHECK (status IN ('created', 'paid', 'failed')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payment_orders_user ON payment_orders(user_owner_id);
CREATE INDEX IF NOT EXISTS idx_payment_orders_razorpay_order ON payment_orders(razorpay_order_id);
