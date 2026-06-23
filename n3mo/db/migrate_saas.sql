-- Add webhook_secret to users table if it doesn't exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS webhook_secret TEXT;
