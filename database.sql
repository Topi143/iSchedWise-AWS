-- ============================================================================
-- iSchedWise V4 - School Scheduling System
-- MySQL Database Schema and Sample Data
-- ============================================================================
-- 
-- INSTRUCTIONS:
-- 1. Start XAMPP and ensure MySQL/MariaDB is running
-- 2. Open phpMyAdmin (http://localhost/phpmyadmin)
-- 3. Create a new database named 'ischedwise_db' (or use SQL below)
-- 4. Import this file into the database
-- 
-- Alternatively, you can run this script directly in phpMyAdmin SQL tab
-- ============================================================================

-- Create Database (if not exists)
CREATE DATABASE IF NOT EXISTS `ischedwise_db` 
DEFAULT CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- Use the database
USE `ischedwise_db`;

-- ============================================================================
-- Drop all tables in correct order (child tables first, then parent tables)
-- This prevents foreign key constraint errors
-- ============================================================================

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS `archives`;
DROP TABLE IF EXISTS `exam_schedules`;
DROP TABLE IF EXISTS `schedules`;
DROP TABLE IF EXISTS `sections`;
DROP TABLE IF EXISTS `rooms`;
DROP TABLE IF EXISTS `buildings`;
DROP TABLE IF EXISTS `faculty_subject_assignments`;
DROP TABLE IF EXISTS `faculty`;
DROP TABLE IF EXISTS `subjects`;
DROP TABLE IF EXISTS `semesters`;
DROP TABLE IF EXISTS `year_levels`;
DROP TABLE IF EXISTS `curricula`;
DROP TABLE IF EXISTS `user_departments`;
DROP TABLE IF EXISTS `departments`;
DROP TABLE IF EXISTS `academic_settings`;
DROP TABLE IF EXISTS `users`;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- Table: users
-- Description: Stores user accounts for Admin and Dean roles
-- Note: Must be created BEFORE departments table (departments.archived_by references users.id)
-- ============================================================================

CREATE TABLE `users` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(80) NOT NULL,
  `email` VARCHAR(120) NOT NULL,
  `password_hash` VARCHAR(256) NOT NULL,
  `role` VARCHAR(20) NOT NULL COMMENT 'admin or dean',
  `full_name` VARCHAR(100) NOT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_login` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`),
  KEY `idx_username` (`username`),
  KEY `idx_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: departments
-- Description: Created after users table (archived_by references users.id)
-- ============================================================================

CREATE TABLE `departments` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `department_code` VARCHAR(20) NOT NULL,
  `department_name` VARCHAR(200) NOT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `is_archived` TINYINT(1) NOT NULL DEFAULT 0,
  `archived_by` INT(11) DEFAULT NULL,
  `archived_at` DATETIME NULL DEFAULT NULL,
  `archive_reason` VARCHAR(255) NULL DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `department_code` (`department_code`),
  KEY `idx_department_code` (`department_code`),
  KEY `idx_is_archived` (`is_archived`),
  KEY `archived_by` (`archived_by`),
  CONSTRAINT `departments_ibfk_1` FOREIGN KEY (`archived_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: user_departments
-- Description: Junction table for many-to-many relationship between users and departments
-- Allows users (especially deans) to be assigned to multiple departments
-- ============================================================================

CREATE TABLE `user_departments` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `user_id` INT(11) NOT NULL,
  `department_id` INT(11) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_department_unique` (`user_id`, `department_id`),
  KEY `user_id` (`user_id`),
  KEY `department_id` (`department_id`),
  CONSTRAINT `user_departments_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `user_departments_ibfk_2` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: curricula
-- ============================================================================

CREATE TABLE `curricula` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `curriculum_code` VARCHAR(50) NOT NULL,
  `curriculum_name` VARCHAR(200) NOT NULL,
  `department_id` INT(11) NOT NULL,
  `degree_program` VARCHAR(200) NOT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `is_archived` TINYINT(1) NOT NULL DEFAULT 0,
  `archived_by` INT(11) DEFAULT NULL,
  `archived_at` DATETIME NULL DEFAULT NULL,
  `archive_reason` VARCHAR(255) NULL DEFAULT NULL,
  `created_by` INT(11) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `curriculum_code` (`curriculum_code`),
  KEY `idx_curriculum_code` (`curriculum_code`),
  KEY `idx_is_archived` (`is_archived`),
  KEY `department_id` (`department_id`),
  KEY `created_by` (`created_by`),
  KEY `archived_by` (`archived_by`),
  CONSTRAINT `curricula_ibfk_1` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `curricula_ibfk_2` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`) ON DELETE RESTRICT,
  CONSTRAINT `curricula_ibfk_3` FOREIGN KEY (`archived_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: year_levels
-- ============================================================================

CREATE TABLE `year_levels` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `curriculum_id` INT(11) NOT NULL,
  `year_number` INT(11) NOT NULL COMMENT '1 for 1st Year, 2 for 2nd Year, etc.',
  `year_name` VARCHAR(50) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `curriculum_id` (`curriculum_id`),
  CONSTRAINT `year_levels_ibfk_1` FOREIGN KEY (`curriculum_id`) REFERENCES `curricula` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: semesters
-- ============================================================================

CREATE TABLE `semesters` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `year_level_id` INT(11) NOT NULL,
  `semester_number` INT(11) NOT NULL COMMENT '1 for 1st Sem, 2 for 2nd Sem, 3 for Summer',
  `semester_name` VARCHAR(50) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `year_level_id` (`year_level_id`),
  CONSTRAINT `semesters_ibfk_1` FOREIGN KEY (`year_level_id`) REFERENCES `year_levels` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: subjects
-- Description: Subjects directly assigned to curriculum semesters
-- All subject data is stored directly (no template references)
-- ============================================================================

CREATE TABLE `subjects` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `semester_id` INT(11) NOT NULL,
  `subject_code` VARCHAR(50) NOT NULL,
  `course_description` VARCHAR(255) NOT NULL,
  `lec_units` DECIMAL(3,1) NOT NULL DEFAULT 0.0,
  `lab_units` DECIMAL(3,1) NOT NULL DEFAULT 0.0,
  `total_units` DECIMAL(3,1) GENERATED ALWAYS AS (`lec_units` + `lab_units`) STORED,
  `prerequisite` VARCHAR(255) DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `semester_id` (`semester_id`),
  KEY `idx_subject_code` (`subject_code`),
  CONSTRAINT `subjects_ibfk_1` FOREIGN KEY (`semester_id`) REFERENCES `semesters` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: faculty
-- ============================================================================

CREATE TABLE `faculty` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `full_name` VARCHAR(255) NOT NULL,
  `department_id` INT(11) DEFAULT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `is_archived` TINYINT(1) NOT NULL DEFAULT 0,
  `archived_by` INT(11) DEFAULT NULL,
  `archived_at` DATETIME NULL DEFAULT NULL,
  `archive_reason` VARCHAR(255) NULL DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_is_archived` (`is_archived`),
  KEY `department_id` (`department_id`),
  KEY `archived_by` (`archived_by`),
  CONSTRAINT `faculty_ibfk_1` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`) ON DELETE SET NULL,
  CONSTRAINT `faculty_ibfk_2` FOREIGN KEY (`archived_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: faculty_subject_assignments
-- Description: Faculty assignments to specific subjects
-- ============================================================================

CREATE TABLE `faculty_subject_assignments` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `faculty_id` INT(11) NOT NULL,
  `subject_id` INT(11) NOT NULL COMMENT 'Specific subject assignment',
  `academic_year` VARCHAR(20) NOT NULL COMMENT 'Academic year for this assignment (e.g., 2024-2025)',
  `semester` VARCHAR(20) NOT NULL COMMENT 'Semester for this assignment (e.g., 1st Semester, 2nd Semester)',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `is_archived` TINYINT(1) NOT NULL DEFAULT 0,
  `archived_by` INT(11) DEFAULT NULL,
  `archived_at` DATETIME NULL DEFAULT NULL,
  `archive_reason` VARCHAR(255) NULL DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `faculty_id` (`faculty_id`),
  KEY `subject_id` (`subject_id`),
  KEY `idx_is_archived` (`is_archived`),
  KEY `archived_by` (`archived_by`),
  KEY `idx_academic_period` (`academic_year`, `semester`),
  CONSTRAINT `faculty_subject_assignments_ibfk_1` FOREIGN KEY (`faculty_id`) REFERENCES `faculty` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `faculty_subject_assignments_ibfk_2` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
  ,CONSTRAINT `faculty_subject_assignments_ibfk_3` FOREIGN KEY (`archived_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: buildings
-- Description: Stores campus buildings information
-- ============================================================================

CREATE TABLE `buildings` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `building_name` VARCHAR(200) NOT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `is_archived` TINYINT(1) NOT NULL DEFAULT 0,
  `archived_by` INT(11) DEFAULT NULL,
  `archived_at` DATETIME NULL DEFAULT NULL,
  `archive_reason` VARCHAR(255) NULL DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_is_archived` (`is_archived`),
  KEY `archived_by` (`archived_by`),
  CONSTRAINT `buildings_ibfk_1` FOREIGN KEY (`archived_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: rooms
-- Description: Stores room information within buildings
-- ============================================================================

CREATE TABLE `rooms` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `building_id` INT(11) NOT NULL,
  `room_number` VARCHAR(50) NOT NULL,
  `is_available` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `building_id` (`building_id`),
  CONSTRAINT `rooms_ibfk_1` FOREIGN KEY (`building_id`) REFERENCES `buildings` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: sections
-- ============================================================================

CREATE TABLE `sections` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `department_id` INT(11) NOT NULL,
  `section_name` VARCHAR(100) NOT NULL,
  `year_level` INT(11) NOT NULL COMMENT 'Year level: 1, 2, 3, 4, etc.',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `department_id` (`department_id`),
  CONSTRAINT `sections_ibfk_1` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: schedules
-- Description: Stores class schedules linking sections, subjects, faculty, rooms, and time slots
-- ============================================================================

CREATE TABLE `schedules` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `section_id` INT(11) NOT NULL,
  `subject_id` INT(11) NOT NULL,
  `faculty_id` INT(11) DEFAULT NULL,
  `room_id` INT(11) DEFAULT NULL,
  `day_of_week` VARCHAR(20) NOT NULL COMMENT 'Monday, Tuesday, Wednesday, Thursday, Friday, Saturday',
  `start_time` TIME NOT NULL,
  `end_time` TIME NOT NULL,
  `semester` VARCHAR(50) DEFAULT NULL COMMENT '1st Semester, 2nd Semester, Summer',
  `academic_year` VARCHAR(20) DEFAULT NULL COMMENT 'e.g., 2024-2025',
  `schedule_type` VARCHAR(20) DEFAULT 'lecture' COMMENT 'lecture, lab, both',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `section_id` (`section_id`),
  KEY `subject_id` (`subject_id`),
  KEY `faculty_id` (`faculty_id`),
  KEY `room_id` (`room_id`),
  KEY `idx_day_time` (`day_of_week`, `start_time`, `end_time`),
  CONSTRAINT `schedules_ibfk_1` FOREIGN KEY (`section_id`) REFERENCES `sections` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `schedules_ibfk_2` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `schedules_ibfk_3` FOREIGN KEY (`faculty_id`) REFERENCES `faculty` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `schedules_ibfk_4` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: exam_schedules
-- Description: Stores examination schedules for sections
-- ============================================================================

CREATE TABLE `exam_schedules` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `section_id` INT(11) NOT NULL,
  `subject_id` INT(11) NOT NULL,
  `faculty_id` INT(11) DEFAULT NULL,
  `room_id` INT(11) DEFAULT NULL,
  `exam_date` DATE NOT NULL,
  `start_time` TIME NOT NULL,
  `end_time` TIME NOT NULL,
  `semester` VARCHAR(50) DEFAULT NULL COMMENT '1st Semester, 2nd Semester, Summer',
  `academic_year` VARCHAR(20) DEFAULT NULL COMMENT 'e.g., 2024-2025',
  `exam_period` VARCHAR(20) DEFAULT NULL COMMENT 'Prelim, Midterm, Final',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `section_id` (`section_id`),
  KEY `subject_id` (`subject_id`),
  KEY `faculty_id` (`faculty_id`),
  KEY `room_id` (`room_id`),
  KEY `idx_exam_date_time` (`exam_date`, `start_time`, `end_time`),
  CONSTRAINT `exam_schedules_ibfk_1` FOREIGN KEY (`section_id`) REFERENCES `sections` (`id`) ON DELETE CASCADE,
  CONSTRAINT `exam_schedules_ibfk_2` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `exam_schedules_ibfk_3` FOREIGN KEY (`faculty_id`) REFERENCES `faculty` (`id`) ON DELETE SET NULL,
  CONSTRAINT `exam_schedules_ibfk_4` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: archives
-- Description: Stores archived/inactive schedules with historical data
-- Supports both class schedules and exam schedules
-- ============================================================================

CREATE TABLE `archives` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  -- Original references (may be NULL if related records deleted)
  `section_id` INT(11) DEFAULT NULL,
  `subject_id` INT(11) DEFAULT NULL,
  `faculty_id` INT(11) DEFAULT NULL,
  `room_id` INT(11) DEFAULT NULL,
  -- Historical data stored as text
  `section_name` VARCHAR(100) DEFAULT NULL,
  `subject_code` VARCHAR(50) DEFAULT NULL,
  `course_description` VARCHAR(255) DEFAULT NULL,
  `faculty_name` VARCHAR(100) DEFAULT NULL,
  `room_number` VARCHAR(20) DEFAULT NULL,
  `building_name` VARCHAR(100) DEFAULT NULL,
  `department_name` VARCHAR(100) DEFAULT NULL,
  -- Schedule timing (supports both class and exam schedules)
  `day_of_week` VARCHAR(20) DEFAULT NULL COMMENT 'For class schedules - Monday, Tuesday, etc.',
  `exam_date` DATE DEFAULT NULL COMMENT 'For exam schedules - specific date',
  `start_time` TIME NOT NULL,
  `end_time` TIME NOT NULL,
  `semester` VARCHAR(50) DEFAULT NULL,
  `academic_year` VARCHAR(20) DEFAULT NULL,
  `schedule_type` VARCHAR(20) DEFAULT 'lecture' COMMENT 'lecture, lab, exam',
  `exam_period` VARCHAR(20) DEFAULT NULL COMMENT 'Prelim, Midterm, Final - for exam schedules',
  -- Archive metadata
  `original_schedule_id` INT(11) DEFAULT NULL COMMENT 'Reference to original schedule ID',
  `archived_by` INT(11) DEFAULT NULL COMMENT 'User who archived this',
  `archive_reason` VARCHAR(255) NULL DEFAULT NULL,
  `archived_at` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `section_id` (`section_id`),
  KEY `subject_id` (`subject_id`),
  KEY `faculty_id` (`faculty_id`),
  KEY `room_id` (`room_id`),
  KEY `archived_by` (`archived_by`),
  KEY `idx_archived_at` (`archived_at`),
  KEY `idx_academic` (`academic_year`, `semester`),
  CONSTRAINT `archives_ibfk_1` FOREIGN KEY (`section_id`) REFERENCES `sections` (`id`) ON DELETE SET NULL,
  CONSTRAINT `archives_ibfk_2` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE SET NULL,
  CONSTRAINT `archives_ibfk_3` FOREIGN KEY (`faculty_id`) REFERENCES `faculty` (`id`) ON DELETE SET NULL,
  CONSTRAINT `archives_ibfk_4` FOREIGN KEY (`room_id`) REFERENCES `rooms` (`id`) ON DELETE SET NULL,
  CONSTRAINT `archives_ibfk_5` FOREIGN KEY (`archived_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- (faculty_subject_assignment_archives removed)

-- ============================================================================
-- Table: academic_settings
-- Description: Stores academic year, semester, and exam period settings
-- ============================================================================

CREATE TABLE `academic_settings` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `academic_year` VARCHAR(20) NOT NULL COMMENT 'e.g., 2024-2025',
  `semester` VARCHAR(50) NOT NULL COMMENT '1st Semester, 2nd Semester, Summer',
  `exam_period` VARCHAR(20) NOT NULL COMMENT 'Prelim, Midterm, Final',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_academic_year` (`academic_year`, `semester`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: user_activity_logs
-- Description: Tracks user actions and activities for audit purposes
-- ============================================================================

CREATE TABLE `user_activity_logs` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `user_id` INT(11) NOT NULL,
  `action` VARCHAR(100) NOT NULL COMMENT 'Action performed (e.g., created_schedule, edited_faculty, deleted_building)',
  `entity_type` VARCHAR(50) NOT NULL COMMENT 'Type of entity (e.g., schedule, faculty, building, curriculum)',
  `entity_id` INT(11) DEFAULT NULL COMMENT 'ID of the affected entity',
  `entity_name` VARCHAR(255) DEFAULT NULL COMMENT 'Name/description of the entity',
  `details` TEXT DEFAULT NULL COMMENT 'Additional details about the action',
  `ip_address` VARCHAR(45) DEFAULT NULL COMMENT 'IP address of the user',
  `user_agent` VARCHAR(255) DEFAULT NULL COMMENT 'Browser/client information',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `idx_action` (`action`),
  KEY `idx_entity_type` (`entity_type`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `user_activity_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Default Data: Admin User and Academic Settings
-- ============================================================================
-- 
-- IMPORTANT: Change these passwords in production!
-- 
-- Default Admin Account:
--   Username: admin
--   Email: admin@norzagaray.edu
--   Password: admin123
--
-- Default Dean Account:
--   Username: dean
--   Email: dean@norzagaray.edu
--   Password: dean123
-- 
-- NOTE: Password hashes are generated using Flask's Werkzeug security
-- ============================================================================

-- Insert Default Department (needed for dean user)
INSERT INTO `departments` (`department_code`, `department_name`, `is_active`, `created_at`) VALUES
('CS', 'Computer Studies', 1, NOW());

-- Insert Default Users
-- Admin: Full system access, no department restriction
-- Dean: Assigned to Computer Studies via user_departments table
INSERT INTO `users` (`username`, `email`, `password_hash`, `role`, `full_name`, `is_active`, `created_at`) VALUES
('admin', 'admin@norzagaray.edu', 'scrypt:32768:8:1$MbXUjG9DsD2erxRU$4507e0983216d49702d541146cde0e1f2bd51a7f082e41f7814e58210849a840c8e1e2555886d2a207be4e031cb7be25fcd0f8be244c4ff7ce19c8ae88c82ca3', 'admin', 'System Administrator', 1, NOW()),
('dean', 'dean@norzagaray.edu', 'scrypt:32768:8:1$4nv83tyAzzeDALDA$4441faaf5fded903f1d0888128313306a943fd3227c5bbdeac09266a8f63ef71c7f4b51f2df985567261f080f225fbeb76d80fdfac6a23a0a074dea9861b5de5', 'dean', 'John Doe', 1, NOW());

-- Insert Default User-Department Assignments
-- Assign dean user to Computer Studies department
INSERT INTO `user_departments` (`user_id`, `department_id`, `created_at`) VALUES
(2, 1, NOW());

-- Insert Default Academic Settings for AY 2025-2026, 1st Semester
INSERT INTO `academic_settings` (`academic_year`, `semester`, `exam_period`, `is_active`, `created_at`) VALUES
('2025-2026', '1st Semester', 'Prelim', 1, NOW());

-- ============================================================================
-- Database Schema Created Successfully!
-- ============================================================================
-- 
-- IMPORTANT: This file creates the database structure and default data.
-- 
-- Default Login Credentials (CHANGE IN PRODUCTION):
-- - Admin: username=admin, password=admin123
-- - Dean: username=dean, password=dean123
-- 
-- Optional: To populate with sample test data, run: sample_data.sql
-- 
-- Next Steps:
-- 1. Verify all tables were created successfully
-- 2. Login with default admin credentials
-- 3. Change default passwords immediately
-- 4. (Optional) Import sample_data.sql for testing
-- 5. Start the Flask application
-- 
-- ============================================================================
