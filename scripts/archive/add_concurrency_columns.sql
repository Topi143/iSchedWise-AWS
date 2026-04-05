-- Add concurrency control columns to schedules table
-- Run this in MySQL Workbench

USE ischedwise_db;

-- Add columns to schedules table
ALTER TABLE schedules 
ADD COLUMN version INT NOT NULL DEFAULT 1,
ADD COLUMN locked_by INT NULL,
ADD COLUMN locked_at DATETIME NULL;

-- Add index and foreign key for locked_by
ALTER TABLE schedules
ADD INDEX idx_locked_by (locked_by),
ADD CONSTRAINT schedules_ibfk_locked_by FOREIGN KEY (locked_by) REFERENCES users(id) ON DELETE SET NULL;

-- Add columns to exam_schedules table
ALTER TABLE exam_schedules 
ADD COLUMN version INT NOT NULL DEFAULT 1,
ADD COLUMN locked_by INT NULL,
ADD COLUMN locked_at DATETIME NULL;

-- Add index and foreign key for locked_by
ALTER TABLE exam_schedules
ADD INDEX idx_exam_locked_by (locked_by),
ADD CONSTRAINT exam_schedules_ibfk_locked_by FOREIGN KEY (locked_by) REFERENCES users(id) ON DELETE SET NULL;

-- Verify columns were added
SELECT 'schedules columns:' AS info;
SHOW COLUMNS FROM schedules WHERE Field IN ('version', 'locked_by', 'locked_at');

SELECT 'exam_schedules columns:' AS info;
SHOW COLUMNS FROM exam_schedules WHERE Field IN ('version', 'locked_by', 'locked_at');
