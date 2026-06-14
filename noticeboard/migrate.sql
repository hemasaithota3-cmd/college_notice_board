-- Run this once on your Railway MySQL to add new columns
-- Safe to run even if columns already exist

USE railway;  -- change to your DB name if different

-- Add push_token column for OneSignal
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS push_token VARCHAR(255) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS phone      VARCHAR(20)  DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS roll_no    VARCHAR(50)  DEFAULT NULL;
