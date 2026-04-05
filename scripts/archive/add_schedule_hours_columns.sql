-- ============================================================================
-- Migration Script: Add schedule_start_hour and schedule_end_hour columns
-- to academic_settings table
-- ============================================================================
-- 
-- INSTRUCTIONS:
-- 1. Open phpMyAdmin (http://localhost/phpmyadmin)
-- 2. Select the 'ischedwise_db' database
-- 3. Go to SQL tab
-- 4. Copy and paste this script
-- 5. Click "Go" to execute
-- 
-- This will add the missing columns without dropping existing data
-- ============================================================================

USE `ischedwise_db`;

-- Add schedule_start_hour column (default: 7 AM)
ALTER TABLE `academic_settings` 
ADD COLUMN `schedule_start_hour` INT(11) NOT NULL DEFAULT 7 COMMENT 'Schedule start hour (0-23)' 
AFTER `exam_period`;

-- Add schedule_end_hour column (default: 8 PM / 20:00)
ALTER TABLE `academic_settings` 
ADD COLUMN `schedule_end_hour` INT(11) NOT NULL DEFAULT 20 COMMENT 'Schedule end hour (0-23)' 
AFTER `schedule_start_hour`;

-- Verify the columns were added
SELECT * FROM `academic_settings`;

-- ============================================================================
-- Migration Complete!
-- ============================================================================
-- 
-- The academic_settings table now has:
-- - schedule_start_hour (default: 7 = 7:00 AM)
-- - schedule_end_hour (default: 20 = 8:00 PM)
-- 
-- Your existing academic settings data has been preserved.
-- ============================================================================
