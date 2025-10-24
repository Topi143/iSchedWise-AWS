-- ============================================================================
-- iSchedWise V4 - Sample Test Data
-- ============================================================================
-- 
-- INSTRUCTIONS:
-- 1. Make sure database.sql has been imported first
-- 2. Import this file in phpMyAdmin to populate with test data
-- 3. This will add sample departments, curricula, subjects, faculty, etc.
-- 
-- Note: This file assumes database.sql has already been imported
-- ============================================================================

USE `ischedwise_db`;

-- ============================================================================
-- Clear existing sample data (preserves default users and settings)
-- ============================================================================

SET FOREIGN_KEY_CHECKS = 0;

DELETE FROM `archives` WHERE id > 0;
DELETE FROM `exam_schedules` WHERE id > 0;
DELETE FROM `schedules` WHERE id > 0;
DELETE FROM `sections` WHERE id > 0;
DELETE FROM `rooms` WHERE id > 0;
DELETE FROM `buildings` WHERE id > 0;
DELETE FROM `faculty_subject_assignments` WHERE id > 0;
DELETE FROM `faculty` WHERE id > 0;
DELETE FROM `subjects` WHERE id > 0;
DELETE FROM `semesters` WHERE id > 0;
DELETE FROM `year_levels` WHERE id > 0;
DELETE FROM `curricula` WHERE id > 0;
DELETE FROM `user_departments` WHERE id > 1; -- Keep default dean-CS assignment
DELETE FROM `departments` WHERE id > 1; -- Keep default CS department

SET FOREIGN_KEY_CHECKS = 1;

-- Reset auto-increment counters
ALTER TABLE `archives` AUTO_INCREMENT = 1;
ALTER TABLE `exam_schedules` AUTO_INCREMENT = 1;
ALTER TABLE `schedules` AUTO_INCREMENT = 1;
ALTER TABLE `sections` AUTO_INCREMENT = 1;
ALTER TABLE `rooms` AUTO_INCREMENT = 1;
ALTER TABLE `buildings` AUTO_INCREMENT = 1;
ALTER TABLE `faculty_subject_assignments` AUTO_INCREMENT = 1;
ALTER TABLE `faculty` AUTO_INCREMENT = 1;
ALTER TABLE `subjects` AUTO_INCREMENT = 1;
ALTER TABLE `semesters` AUTO_INCREMENT = 1;
ALTER TABLE `year_levels` AUTO_INCREMENT = 1;
ALTER TABLE `curricula` AUTO_INCREMENT = 1;
ALTER TABLE `departments` AUTO_INCREMENT = 2; -- Keep default CS department

-- ============================================================================
-- NOTE: Users are created in database.sql, departments reference users.archived_by
-- ============================================================================

-- ============================================================================
-- Sample Departments (created after users exist)
-- ============================================================================

INSERT INTO `departments` (`department_code`, `department_name`, `is_active`, `is_archived`, `archived_by`, `archived_at`, `archive_reason`, `created_at`) VALUES
('BSHM', 'Hospitality Management', 1, 0, NULL, NULL, NULL, NOW()),
('BEED', 'Elementary Education', 1, 0, NULL, NULL, NULL, NOW()),
('BSED', 'Secondary Education', 1, 0, NULL, NULL, NULL, NOW()),
('OLD-DEPT', 'Old Department (Archived)', 0, 1, 1, '2024-02-10 14:20:00', 'Department merged with Computer Studies', '2019-01-01 00:00:00');

-- ============================================================================
-- Sample User-Department Assignments
-- ============================================================================

-- Assign dean user to multiple departments (CS from database.sql + new departments)
INSERT INTO `user_departments` (`user_id`, `department_id`, `created_at`) VALUES
(2, 2, NOW()),  -- Dean also assigned to BSHM
(2, 3, NOW());  -- Dean also assigned to BEED

-- ============================================================================
-- Sample Buildings
-- ============================================================================

INSERT INTO `buildings` (`building_name`, `is_active`, `created_at`) VALUES
('Main Building', 1, NOW()),
('Science Building', 1, NOW()),
('IT Building', 1, NOW()),
('Admin Building', 1, NOW());

-- ============================================================================
-- Sample Rooms
-- ============================================================================

INSERT INTO `rooms` (`building_id`, `room_number`, `is_available`, `created_at`) VALUES
-- Main Building (ID: 1)
(1, '101', 1, NOW()),
(1, '102', 1, NOW()),
(1, '103', 1, NOW()),
(1, '104', 1, NOW()),
(1, '105', 1, NOW()),
-- Science Building (ID: 2)
(2, '201', 1, NOW()),
(2, '202', 1, NOW()),
(2, '203', 1, NOW()),
(2, 'Lab 1', 1, NOW()),
(2, 'Lab 2', 1, NOW()),
-- IT Building (ID: 3)
(3, '301', 1, NOW()),
(3, '302', 1, NOW()),
(3, 'Comp Lab 1', 1, NOW()),
(3, 'Comp Lab 2', 1, NOW()),
(3, 'Comp Lab 3', 1, NOW()),
-- Admin Building (ID: 4)
(4, 'Conference Room', 1, NOW()),
(4, 'Faculty Room', 1, NOW());

-- ============================================================================
-- Sample Faculty
-- ============================================================================

INSERT INTO `faculty` (`full_name`, `department_id`, `is_active`, `created_at`) VALUES
-- Computer Studies Faculty (dept_id: 1)
('Dr. Maria Santos', 1, 1, NOW()),
('Prof. Juan Dela Cruz', 1, 1, NOW()),
('Prof. Anna Reyes', 1, 1, NOW()),
('Dr. Roberto Garcia', 1, 1, NOW()),
-- Hospitality Management Faculty (dept_id: 2)
('Prof. Lisa Fernandez', 2, 1, NOW()),
('Dr. Carlos Martinez', 2, 1, NOW()),
('Prof. Sarah Johnson', 2, 1, NOW()),
-- Elementary Education Faculty (dept_id: 3)
('Prof. Elena Villanueva', 3, 1, NOW()),
('Dr. Miguel Torres', 3, 1, NOW()),
('Prof. Carmen Lopez', 3, 1, NOW()),
-- Secondary Education Faculty (dept_id: 4)
('Dr. Antonio Ramos', 4, 1, NOW()),
('Prof. Sofia Gonzales', 4, 1, NOW());

-- ============================================================================
-- Sample Sections
-- ============================================================================

INSERT INTO `sections` (`department_id`, `section_name`, `year_level`, `is_active`, `created_at`) VALUES
-- Computer Studies Sections (dept_id: 1)
(1, 'CS 1-A', 1, 1, NOW()),
(1, 'CS 1-B', 1, 1, NOW()),
(1, 'CS 2-A', 2, 1, NOW()),
(1, 'CS 2-B', 2, 1, NOW()),
(1, 'CS 3-A', 3, 1, NOW()),
(1, 'CS 4-A', 4, 1, NOW()),
-- Hospitality Management Sections (dept_id: 2)
(2, 'BSHM 1-A', 1, 1, NOW()),
(2, 'BSHM 2-A', 2, 1, NOW()),
(2, 'BSHM 3-A', 3, 1, NOW()),
(2, 'BSHM 4-A', 4, 1, NOW()),
-- Elementary Education Sections (dept_id: 3)
(3, 'BEED 1-A', 1, 1, NOW()),
(3, 'BEED 2-A', 2, 1, NOW()),
(3, 'BEED 3-A', 3, 1, NOW()),
(3, 'BEED 4-A', 4, 1, NOW());

-- ============================================================================
-- Sample Curricula
-- ============================================================================

INSERT INTO `curricula` (`curriculum_code`, `department_id`, `degree_program`, `is_active`, `is_archived`, `archived_by`, `archived_at`, `archive_reason`, `created_by`, `created_at`) VALUES
('BSHM-2024', 2, 'Bachelor of Science in Hospitality Management', 1, 0, NULL, NULL, NULL, 1, NOW()),
('CS-2024', 1, 'Bachelor of Science in Computer Science', 1, 0, NULL, NULL, NULL, 1, NOW()),
('BEED-2024', 3, 'Bachelor of Elementary Education', 1, 0, NULL, NULL, NULL, 1, NOW()),
('CS-2020', 1, 'Bachelor of Science in Computer Science', 0, 1, 1, '2024-01-15 10:30:00', 'Outdated curriculum replaced by 2024 version', 1, '2020-06-01 00:00:00');

-- ============================================================================
-- Year Levels and Semesters for BSHM 2024
-- ============================================================================

-- BSHM 1st Year
INSERT INTO `year_levels` (`curriculum_id`, `year_number`, `year_name`, `created_at`) VALUES
(1, 1, '1st Year', NOW());

INSERT INTO `semesters` (`year_level_id`, `semester_number`, `semester_name`, `created_at`) VALUES
(1, 1, '1st Semester', NOW()),
(1, 2, '2nd Semester', NOW());

-- BSHM 2nd Year
INSERT INTO `year_levels` (`curriculum_id`, `year_number`, `year_name`, `created_at`) VALUES
(1, 2, '2nd Year', NOW());

INSERT INTO `semesters` (`year_level_id`, `semester_number`, `semester_name`, `created_at`) VALUES
(2, 1, '1st Semester', NOW()),
(2, 2, '2nd Semester', NOW());

-- BSHM 3rd Year
INSERT INTO `year_levels` (`curriculum_id`, `year_number`, `year_name`, `created_at`) VALUES
(1, 3, '3rd Year', NOW());

INSERT INTO `semesters` (`year_level_id`, `semester_number`, `semester_name`, `created_at`) VALUES
(3, 1, '1st Semester', NOW()),
(3, 2, '2nd Semester', NOW());

-- BSHM 4th Year
INSERT INTO `year_levels` (`curriculum_id`, `year_number`, `year_name`, `created_at`) VALUES
(1, 4, '4th Year', NOW());

INSERT INTO `semesters` (`year_level_id`, `semester_number`, `semester_name`, `created_at`) VALUES
(4, 1, '1st Semester', NOW()),
(4, 2, '2nd Semester', NOW());

-- ============================================================================
-- Year Levels and Semesters for CS 2024
-- ============================================================================

-- CS 1st Year
INSERT INTO `year_levels` (`curriculum_id`, `year_number`, `year_name`, `created_at`) VALUES
(2, 1, '1st Year', NOW());

INSERT INTO `semesters` (`year_level_id`, `semester_number`, `semester_name`, `created_at`) VALUES
(5, 1, '1st Semester', NOW()),
(5, 2, '2nd Semester', NOW());

-- CS 2nd Year
INSERT INTO `year_levels` (`curriculum_id`, `year_number`, `year_name`, `created_at`) VALUES
(2, 2, '2nd Year', NOW());

INSERT INTO `semesters` (`year_level_id`, `semester_number`, `semester_name`, `created_at`) VALUES
(6, 1, '1st Semester', NOW()),
(6, 2, '2nd Semester', NOW());

-- CS 3rd Year
INSERT INTO `year_levels` (`curriculum_id`, `year_number`, `year_name`, `created_at`) VALUES
(2, 3, '3rd Year', NOW());

INSERT INTO `semesters` (`year_level_id`, `semester_number`, `semester_name`, `created_at`) VALUES
(7, 1, '1st Semester', NOW()),
(7, 2, '2nd Semester', NOW());

-- CS 4th Year
INSERT INTO `year_levels` (`curriculum_id`, `year_number`, `year_name`, `created_at`) VALUES
(2, 4, '4th Year', NOW());

INSERT INTO `semesters` (`year_level_id`, `semester_number`, `semester_name`, `created_at`) VALUES
(8, 1, '1st Semester', NOW()),
(8, 2, '2nd Semester', NOW());

-- ============================================================================
-- Year Levels and Semesters for BEED 2024
-- ============================================================================

-- BEED 1st Year
INSERT INTO `year_levels` (`curriculum_id`, `year_number`, `year_name`, `created_at`) VALUES
(3, 1, '1st Year', NOW());

INSERT INTO `semesters` (`year_level_id`, `semester_number`, `semester_name`, `created_at`) VALUES
(9, 1, '1st Semester', NOW()),
(9, 2, '2nd Semester', NOW());

-- BEED 2nd Year
INSERT INTO `year_levels` (`curriculum_id`, `year_number`, `year_name`, `created_at`) VALUES
(3, 2, '2nd Year', NOW());

INSERT INTO `semesters` (`year_level_id`, `semester_number`, `semester_name`, `created_at`) VALUES
(10, 1, '1st Semester', NOW()),
(10, 2, '2nd Semester', NOW());

-- ============================================================================
-- Sample Subjects for BSHM 2024 - 1st Year, 1st Semester
-- ============================================================================

INSERT INTO `subjects` (`semester_id`, `subject_code`, `course_description`, `lec_units`, `lab_units`, `prerequisite`, `created_at`) VALUES
-- BSHM 1st Year, 1st Semester (semester_id: 1)
(1, 'GE1', 'Understanding the Self', 3.0, 0.0, 'None', NOW()),
(1, 'GE2', 'Readings in Philippine History', 3.0, 0.0, 'None', NOW()),
(1, 'GE3', 'Mathematics in the Modern World', 3.0, 0.0, 'None', NOW()),
(1, 'GE4', 'Purposive Communication', 3.0, 0.0, 'None', NOW()),
(1, 'PE1', 'Physical Education 1', 2.0, 0.0, 'None', NOW()),
(1, 'NSTP1', 'National Service Training Program 1', 3.0, 0.0, 'None', NOW()),
(1, 'THC1', 'Macro Perspective of Tourism and Hospitality', 3.0, 0.0, 'None', NOW()),

-- BSHM 1st Year, 2nd Semester (semester_id: 2)
(2, 'GE5', 'Art Appreciation', 3.0, 0.0, 'None', NOW()),
(2, 'GE6', 'Science, Technology and Society', 3.0, 0.0, 'None', NOW()),
(2, 'GE7', 'Ethics', 3.0, 0.0, 'None', NOW()),
(2, 'GE8', 'The Contemporary World', 3.0, 0.0, 'GE2', NOW()),
(2, 'PE2', 'Physical Education 2', 2.0, 0.0, 'PE1', NOW()),
(2, 'NSTP2', 'National Service Training Program 2', 3.0, 0.0, 'NSTP1', NOW()),
(2, 'THC2', 'Micro Perspective of Tourism and Hospitality', 3.0, 0.0, 'THC1', NOW());

-- ============================================================================
-- Sample Subjects for CS 2024 - 1st Year
-- ============================================================================

INSERT INTO `subjects` (`semester_id`, `subject_code`, `course_description`, `lec_units`, `lab_units`, `prerequisite`, `created_at`) VALUES
-- CS 1st Year, 1st Semester (semester_id: 9)
(9, 'CS101', 'Introduction to Computing', 2.0, 1.0, 'None', NOW()),
(9, 'CS102', 'Computer Programming 1', 2.0, 1.0, 'None', NOW()),
(9, 'MATH101', 'College Algebra', 3.0, 0.0, 'None', NOW()),
(9, 'ENGL101', 'Communication Skills 1', 3.0, 0.0, 'None', NOW()),
(9, 'PE101', 'Physical Education 1', 2.0, 0.0, 'None', NOW()),
(9, 'NSTP101', 'NSTP 1', 3.0, 0.0, 'None', NOW()),

-- CS 1st Year, 2nd Semester (semester_id: 10)
(10, 'CS103', 'Computer Programming 2', 2.0, 1.0, 'CS102', NOW()),
(10, 'CS104', 'Discrete Mathematics', 3.0, 0.0, 'MATH101', NOW()),
(10, 'MATH102', 'Trigonometry', 3.0, 0.0, 'MATH101', NOW()),
(10, 'ENGL102', 'Communication Skills 2', 3.0, 0.0, 'ENGL101', NOW()),
(10, 'PE102', 'Physical Education 2', 2.0, 0.0, 'PE101', NOW()),
(10, 'NSTP102', 'NSTP 2', 3.0, 0.0, 'NSTP101', NOW());

-- ============================================================================
-- Sample Subjects for CS 2024 - 2nd Year
-- ============================================================================

INSERT INTO `subjects` (`semester_id`, `subject_code`, `course_description`, `lec_units`, `lab_units`, `prerequisite`, `created_at`) VALUES
-- CS 2nd Year, 1st Semester (semester_id: 11)
(11, 'CS201', 'Data Structures and Algorithms', 2.0, 1.0, 'CS103', NOW()),
(11, 'CS202', 'Object-Oriented Programming', 2.0, 1.0, 'CS103', NOW()),
(11, 'CS203', 'Database Management Systems', 2.0, 1.0, 'CS104', NOW()),
(11, 'MATH201', 'Statistics and Probability', 3.0, 0.0, 'MATH102', NOW()),
(11, 'PE201', 'Physical Education 3', 2.0, 0.0, 'PE102', NOW()),

-- CS 2nd Year, 2nd Semester (semester_id: 12)
(12, 'CS204', 'Web Development', 2.0, 1.0, 'CS202', NOW()),
(12, 'CS205', 'Computer Architecture', 3.0, 0.0, 'CS101', NOW()),
(12, 'CS206', 'Software Engineering', 3.0, 0.0, 'CS201', NOW()),
(12, 'MATH202', 'Linear Algebra', 3.0, 0.0, 'MATH201', NOW()),
(12, 'PE202', 'Physical Education 4', 2.0, 0.0, 'PE201', NOW());

-- ============================================================================
-- Sample Subjects for BEED 2024 - 1st Year
-- ============================================================================

INSERT INTO `subjects` (`semester_id`, `subject_code`, `course_description`, `lec_units`, `lab_units`, `prerequisite`, `created_at`) VALUES
-- BEED 1st Year, 1st Semester (semester_id: 17)
(17, 'ED101', 'The Child and Adolescent Learners', 3.0, 0.0, 'None', NOW()),
(17, 'ED102', 'The Teaching Profession', 3.0, 0.0, 'None', NOW()),
(17, 'FIL101', 'Komunikasyon sa Akademikong Filipino', 3.0, 0.0, 'None', NOW()),
(17, 'MATH-ED101', 'Mathematics in the Modern World', 3.0, 0.0, 'None', NOW()),
(17, 'SCI-ED101', 'Science, Technology and Society', 3.0, 0.0, 'None', NOW()),
(17, 'PE-ED101', 'Physical Education 1', 2.0, 0.0, 'None', NOW()),

-- BEED 1st Year, 2nd Semester (semester_id: 18)
(18, 'ED103', 'Facilitating Learner-Centered Teaching', 3.0, 0.0, 'ED101', NOW()),
(18, 'ED104', 'Foundation of Special and Inclusive Education', 3.0, 0.0, 'ED101', NOW()),
(18, 'FIL102', 'Pagbasa at Pagsusuri ng Iba\'t Ibang Teksto', 3.0, 0.0, 'FIL101', NOW()),
(18, 'ENG-ED101', 'Purposive Communication', 3.0, 0.0, 'None', NOW()),
(18, 'SOC-ED101', 'Understanding the Self', 3.0, 0.0, 'None', NOW()),
(18, 'PE-ED102', 'Physical Education 2', 2.0, 0.0, 'PE-ED101', NOW());

-- ============================================================================
-- Sample Faculty Subject Assignments
-- ============================================================================

INSERT INTO `faculty_subject_assignments` (`faculty_id`, `subject_id`, `academic_year`, `semester`, `created_at`) VALUES
-- Dr. Maria Santos (CS) - assigned to CS subjects
(1, 13, '2024-2025', '1st Semester', NOW()),  -- CS101
(1, 14, '2024-2025', '1st Semester', NOW()),  -- CS102

-- Prof. Juan Dela Cruz (CS) - assigned to CS subjects
(2, 19, '2024-2025', '2nd Semester', NOW()),  -- CS103
(2, 25, '2024-2025', '1st Semester', NOW()),  -- CS201

-- Prof. Anna Reyes (CS) - assigned to CS subjects
(3, 26, '2024-2025', '1st Semester', NOW()),  -- CS202
(3, 30, '2024-2025', '2nd Semester', NOW()),  -- CS204

-- Prof. Lisa Fernandez (BSHM) - assigned to BSHM subjects
(5, 1, '2024-2025', '1st Semester', NOW()),   -- GE1
(5, 7, '2024-2025', '1st Semester', NOW()),   -- THC1

-- Dr. Carlos Martinez (BSHM) - assigned to BSHM subjects
(6, 8, '2024-2025', '2nd Semester', NOW()),   -- GE5
(6, 14, '2024-2025', '2nd Semester', NOW()),  -- THC2

-- Prof. Elena Villanueva (BEED) - assigned to BEED subjects
(8, 37, '2024-2025', '1st Semester', NOW()),  -- ED101
(8, 38, '2024-2025', '1st Semester', NOW()),  -- ED102

-- Dr. Miguel Torres (BEED) - assigned to BEED subjects
(9, 43, '2024-2025', '2nd Semester', NOW()),  -- ED103
(9, 44, '2024-2025', '2nd Semester', NOW());  -- ED104

-- ============================================================================
-- Sample Class Schedules
-- ============================================================================

INSERT INTO `schedules` (`section_id`, `subject_id`, `faculty_id`, `room_id`, `day_of_week`, `start_time`, `end_time`, `semester`, `academic_year`, `schedule_type`, `is_active`, `created_at`) VALUES
-- CS 1-A Schedule (section_id: 1)
(1, 13, 1, 13, 'Monday', '08:00:00', '10:00:00', '1st Semester', '2024-2025', 'lecture', 1, NOW()),    -- CS101
(1, 14, 1, 13, 'Tuesday', '08:00:00', '10:00:00', '1st Semester', '2024-2025', 'lecture', 1, NOW()),   -- CS102
(1, 15, NULL, 1, 'Wednesday', '08:00:00', '11:00:00', '1st Semester', '2024-2025', 'lecture', 1, NOW()), -- MATH101
(1, 16, NULL, 1, 'Thursday', '08:00:00', '11:00:00', '1st Semester', '2024-2025', 'lecture', 1, NOW()),  -- ENGL101

-- BSHM 1-A Schedule (section_id: 7)
(7, 1, 5, 1, 'Monday', '10:00:00', '12:00:00', '1st Semester', '2024-2025', 'lecture', 1, NOW()),  -- GE1
(7, 2, NULL, 1, 'Tuesday', '10:00:00', '13:00:00', '1st Semester', '2024-2025', 'lecture', 1, NOW()), -- GE2
(7, 3, NULL, 2, 'Wednesday', '10:00:00', '13:00:00', '1st Semester', '2024-2025', 'lecture', 1, NOW()), -- GE3
(7, 7, 5, 2, 'Thursday', '10:00:00', '13:00:00', '1st Semester', '2024-2025', 'lecture', 1, NOW()), -- THC1

-- BEED 1-A Schedule (section_id: 11)
(11, 37, 8, 3, 'Monday', '13:00:00', '16:00:00', '1st Semester', '2024-2025', 'lecture', 1, NOW()),  -- ED101
(11, 38, 8, 3, 'Tuesday', '13:00:00', '16:00:00', '1st Semester', '2024-2025', 'lecture', 1, NOW()),  -- ED102
(11, 39, NULL, 4, 'Wednesday', '13:00:00', '16:00:00', '1st Semester', '2024-2025', 'lecture', 1, NOW()); -- FIL101

-- ============================================================================
-- Sample Exam Schedules
-- ============================================================================

INSERT INTO `exam_schedules` (`section_id`, `subject_id`, `faculty_id`, `room_id`, `exam_date`, `start_time`, `end_time`, `semester`, `academic_year`, `exam_period`, `is_active`, `created_at`) VALUES
-- CS 1-A Prelim Exams
(1, 13, 1, 13, '2024-10-15', '08:00:00', '10:00:00', '1st Semester', '2024-2025', 'Prelim', 1, NOW()),  -- CS101
(1, 14, 1, 13, '2024-10-16', '08:00:00', '10:00:00', '1st Semester', '2024-2025', 'Prelim', 1, NOW()),  -- CS102
(1, 15, NULL, 1, '2024-10-17', '08:00:00', '10:00:00', '1st Semester', '2024-2025', 'Prelim', 1, NOW()), -- MATH101

-- BSHM 1-A Prelim Exams
(7, 1, 5, 1, '2024-10-18', '10:00:00', '12:00:00', '1st Semester', '2024-2025', 'Prelim', 1, NOW()),   -- GE1
(7, 2, NULL, 1, '2024-10-19', '10:00:00', '12:00:00', '1st Semester', '2024-2025', 'Prelim', 1, NOW()), -- GE2
(7, 7, 5, 2, '2024-10-20', '10:00:00', '12:00:00', '1st Semester', '2024-2025', 'Prelim', 1, NOW());   -- THC1

-- ============================================================================
-- Sample Data Import Complete!
-- ============================================================================
-- 
-- Summary of imported data:
-- - 4 Departments (CS, BSHM, BEED, BSED)
-- - 4 Buildings with 17 Rooms
-- - 12 Faculty members
-- - 14 Sections (various year levels)
-- - 3 Curricula (BSHM 2024, CS 2024, BEED 2024)
-- - 12 Year Levels (4 per curriculum)
-- - 24 Semesters (2 per year level)
-- - 48+ Subjects (distributed across curricula)
-- - 11 Faculty Subject Assignments
-- - 11 Class Schedules
-- - 6 Exam Schedules
-- 
-- You can now:
-- 1. Login to the application
-- 2. View curricula and subjects
-- 3. Manage schedules
-- 4. Assign faculty to subjects
-- 5. Create exam schedules
-- 
-- Default Login:
-- - Admin: username=admin, password=admin123
-- - Dean: username=dean, password=dean123
-- 
-- ============================================================================
