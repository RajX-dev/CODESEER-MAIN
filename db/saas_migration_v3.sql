-- N3MO SaaS Pricing Migration v3
-- Run this ONCE against an existing production database to migrate to the 5-tier pricing.

-- ============================================================
-- 1. Migrate existing plan names
-- ============================================================
UPDATE subscriptions SET plan_type = 'standard' WHERE plan_type = 'starter';
UPDATE subscriptions SET plan_type = 'team_basic' WHERE plan_type = 'team';

-- ============================================================
-- 2. Update plan_type CHECK constraint on subscriptions
--    Old: ('none', 'starter', 'pro', 'team', 'enterprise')
--    New: ('none', 'standard', 'pro', 'team_basic', 'team_pro', 'enterprise')
-- ============================================================
ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscriptions_plan_type_check;
ALTER TABLE subscriptions ADD CONSTRAINT subscriptions_plan_type_check
    CHECK (plan_type IN ('none', 'standard', 'pro', 'team_basic', 'team_pro', 'enterprise'));
