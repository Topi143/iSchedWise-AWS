-- ============================================================================
-- Add Department Information Columns
-- Script to add full_department_name, department_logo, and secretary_name
-- columns to existing departments table
-- ============================================================================
-- 
-- INSTRUCTIONS:
-- 1. Backup your database before running this script
-- 2. Open phpMyAdmin (http://localhost/phpmyadmin)
-- 3. Select 'ischedwise_db' database
-- 4. Go to SQL tab
-- 5. Paste and execute this script
-- 
-- This script is safe to run multiple times (uses IF NOT EXISTS checks)
-- ============================================================================

USE `ischedwise_db`;

-- Check if columns exist before adding them
SET @dbname = 'ischedwise_db';
SET @tablename = 'departments';

-- Add full_department_name column if it doesn't exist
SET @col_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname
    AND TABLE_NAME = @tablename
    AND COLUMN_NAME = 'full_department_name'
);

SET @query = IF(@col_exists = 0,
    'ALTER TABLE `departments` ADD COLUMN `full_department_name` VARCHAR(255) NULL DEFAULT NULL COMMENT ''Full official department name (e.g., Department of Computing Studies)'' AFTER `department_name`',
    'SELECT ''Column full_department_name already exists'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add department_logo column if it doesn't exist
SET @col_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname
    AND TABLE_NAME = @tablename
    AND COLUMN_NAME = 'department_logo'
);

SET @query = IF(@col_exists = 0,
    'ALTER TABLE `departments` ADD COLUMN `department_logo` VARCHAR(255) NULL DEFAULT NULL COMMENT ''Path to department logo image'' AFTER `full_department_name`',
    'SELECT ''Column department_logo already exists'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add secretary_name column if it doesn't exist
SET @col_exists = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = @dbname
    AND TABLE_NAME = @tablename
    AND COLUMN_NAME = 'secretary_name'
);

SET @query = IF(@col_exists = 0,
    'ALTER TABLE `departments` ADD COLUMN `secretary_name` VARCHAR(100) NULL DEFAULT NULL COMMENT ''Name of department secretary'' AFTER `department_logo`',
    'SELECT ''Column secretary_name already exists'' AS message'
);

PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============================================================================
-- Verification: Display current departments table structure
-- ============================================================================

DESCRIBE `departments`;

-- ============================================================================
-- Optional: Update existing departments with sample data
-- ============================================================================
-- 
-- Uncomment and modify the following lines to add data to existing departments:
-- 
-- UPDATE `departments` 
-- SET `full_department_name` = 'Department of Computing Studies',
--     `secretary_name` = 'Jane Smith'
-- WHERE `department_code` = 'BSCS';
-- 
-- UPDATE `departments` 
-- SET `full_department_name` = 'Department of Hospitality Management',
--     `secretary_name` = 'John Doe'
-- WHERE `department_code` = 'BSHM';
-- 
-- ============================================================================

SELECT 'Department information columns added successfully!' AS status;
SELECT 'Run DESCRIBE departments; to verify the changes.' AS next_step;

-- ============================================================================
-- Migration Complete!
-- ============================================================================
