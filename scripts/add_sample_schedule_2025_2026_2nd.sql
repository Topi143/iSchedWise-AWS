-- Script to add sample data for 2nd Semester 2025-2026
-- Focuses on testing "Suggest Room" feature with PE, Lab, and Lecture subjects

-- 1. Deactivate all current academic settings
UPDATE `academic_settings` SET `is_active` = 0;

-- 2. Insert/Activate 2nd Semester 2025-2026
INSERT INTO `academic_settings` (`academic_year`, `semester`, `exam_period`, `is_active`)
VALUES ('2025-2026', '2nd Semester', 'Prelim', 1);

-- Get the ID of the newly inserted setting (conceptually, we just know it's active now)

-- 3. Ensure Buildings exist (using INSERT IGNORE or checking existence)
-- We need a Sports Complex for PE testing
INSERT INTO `buildings` (`building_name`, `is_active`)
SELECT 'Sports Complex', 1 WHERE NOT EXISTS (SELECT 1 FROM `buildings` WHERE `building_name` = 'Sports Complex');

INSERT INTO `buildings` (`building_name`, `is_active`)
SELECT 'Science Building', 1 WHERE NOT EXISTS (SELECT 1 FROM `buildings` WHERE `building_name` = 'Science Building');

-- 4. Ensure Rooms exist with specific keywords for the AI logic
-- PE Rooms
INSERT INTO `rooms` (`building_id`, `room_number`, `is_available`)
SELECT id, 'Gymnasium', 1 FROM `buildings` WHERE `building_name` = 'Sports Complex'
AND NOT EXISTS (SELECT 1 FROM `rooms` WHERE `room_number` = 'Gymnasium');

INSERT INTO `rooms` (`building_id`, `room_number`, `is_available`)
SELECT id, 'Basketball Court', 1 FROM `buildings` WHERE `building_name` = 'Sports Complex'
AND NOT EXISTS (SELECT 1 FROM `rooms` WHERE `room_number` = 'Basketball Court');

INSERT INTO `rooms` (`building_id`, `room_number`, `is_available`)
SELECT id, 'Open Field', 1 FROM `buildings` WHERE `building_name` = 'Sports Complex'
AND NOT EXISTS (SELECT 1 FROM `rooms` WHERE `room_number` = 'Open Field');

-- Lab Rooms
INSERT INTO `rooms` (`building_id`, `room_number`, `is_available`)
SELECT id, 'Computer Lab 1', 1 FROM `buildings` WHERE `building_name` = 'COMSCIE Building'
AND NOT EXISTS (SELECT 1 FROM `rooms` WHERE `room_number` = 'Computer Lab 1');

INSERT INTO `rooms` (`building_id`, `room_number`, `is_available`)
SELECT id, 'Science Lab A', 1 FROM `buildings` WHERE `building_name` = 'Science Building'
AND NOT EXISTS (SELECT 1 FROM `rooms` WHERE `room_number` = 'Science Lab A');

-- Lecture Rooms
INSERT INTO `rooms` (`building_id`, `room_number`, `is_available`)
SELECT id, 'Lecture Hall 101', 1 FROM `buildings` WHERE `building_name` = 'Main Building'
AND NOT EXISTS (SELECT 1 FROM `rooms` WHERE `room_number` = 'Lecture Hall 101');

-- 5. Ensure Subjects exist (PE, Lab, Lecture)
-- We need to find a valid semester_id. 
-- Let's assume we are adding to '2nd Semester' of some Year Level.
-- We'll pick Year Level 1, 2nd Semester (id 2 in `semesters` table based on dump, but let's be safe)

-- PE Subject
INSERT INTO `subjects` (`semester_id`, `subject_code`, `course_description`, `lec_units`, `lab_units`)
SELECT 2, 'PATHFit 2', 'Fitness Exercises', 2.0, 0.0
WHERE NOT EXISTS (SELECT 1 FROM `subjects` WHERE `subject_code` = 'PATHFit 2');

INSERT INTO `subjects` (`semester_id`, `subject_code`, `course_description`, `lec_units`, `lab_units`)
SELECT 2, 'PE 4', 'Team Sports', 2.0, 0.0
WHERE NOT EXISTS (SELECT 1 FROM `subjects` WHERE `subject_code` = 'PE 4');

-- Lab Subject
INSERT INTO `subjects` (`semester_id`, `subject_code`, `course_description`, `lec_units`, `lab_units`)
SELECT 2, 'CS 102', 'Computer Programming 1', 2.0, 1.0
WHERE NOT EXISTS (SELECT 1 FROM `subjects` WHERE `subject_code` = 'CS 102');

-- Lecture Subject
INSERT INTO `subjects` (`semester_id`, `subject_code`, `course_description`, `lec_units`, `lab_units`)
SELECT 2, 'GEC 105', 'Purposive Communication', 3.0, 0.0
WHERE NOT EXISTS (SELECT 1 FROM `subjects` WHERE `subject_code` = 'GEC 105');

-- 6. Ensure Sections exist for 2nd Sem
INSERT INTO `sections` (`department_id`, `section_name`, `year_level`)
SELECT 1, 'BSCS 1-A', 1
WHERE NOT EXISTS (SELECT 1 FROM `sections` WHERE `section_name` = 'BSCS 1-A');

INSERT INTO `sections` (`department_id`, `section_name`, `year_level`)
SELECT 1, 'BSCS 1-B', 1
WHERE NOT EXISTS (SELECT 1 FROM `sections` WHERE `section_name` = 'BSCS 1-B');

-- 7. Insert Sample Schedules
-- We need IDs. Since we can't easily use variables in a simple SQL script without stored procedures,
-- we will use subqueries to look up IDs.

-- Schedule 1: PE Class in Gym (Monday 8-10 AM)
INSERT INTO `schedules` (`section_id`, `subject_id`, `faculty_id`, `room_id`, `day_of_week`, `start_time`, `end_time`, `semester`, `academic_year`, `schedule_type`, `is_active`)
SELECT 
    (SELECT id FROM `sections` WHERE `section_name` = 'BSCS 1-A' LIMIT 1),
    (SELECT id FROM `subjects` WHERE `subject_code` = 'PATHFit 2' LIMIT 1),
    (SELECT id FROM `faculty` LIMIT 1), -- Just pick first faculty
    (SELECT id FROM `rooms` WHERE `room_number` = 'Gymnasium' LIMIT 1),
    'Monday', '08:00:00', '10:00:00', '2nd Semester', '2025-2026', 'lecture', 1;

-- Schedule 2: Lab Class in Computer Lab (Tuesday 1-4 PM)
INSERT INTO `schedules` (`section_id`, `subject_id`, `faculty_id`, `room_id`, `day_of_week`, `start_time`, `end_time`, `semester`, `academic_year`, `schedule_type`, `is_active`)
SELECT 
    (SELECT id FROM `sections` WHERE `section_name` = 'BSCS 1-A' LIMIT 1),
    (SELECT id FROM `subjects` WHERE `subject_code` = 'CS 102' LIMIT 1),
    (SELECT id FROM `faculty` LIMIT 1),
    (SELECT id FROM `rooms` WHERE `room_number` = 'Computer Lab 1' LIMIT 1),
    'Tuesday', '13:00:00', '16:00:00', '2nd Semester', '2025-2026', 'lab', 1;

-- Schedule 3: Lecture Class in Lecture Hall (Wednesday 9-12 AM)
INSERT INTO `schedules` (`section_id`, `subject_id`, `faculty_id`, `room_id`, `day_of_week`, `start_time`, `end_time`, `semester`, `academic_year`, `schedule_type`, `is_active`)
SELECT 
    (SELECT id FROM `sections` WHERE `section_name` = 'BSCS 1-A' LIMIT 1),
    (SELECT id FROM `subjects` WHERE `subject_code` = 'GEC 105' LIMIT 1),
    (SELECT id FROM `faculty` LIMIT 1),
    (SELECT id FROM `rooms` WHERE `room_number` = 'Lecture Hall 101' LIMIT 1),
    'Wednesday', '09:00:00', '12:00:00', '2nd Semester', '2025-2026', 'lecture', 1;

-- Schedule 4: Another PE Class (Conflict Test) - Same time as Schedule 1 but different section
INSERT INTO `schedules` (`section_id`, `subject_id`, `faculty_id`, `room_id`, `day_of_week`, `start_time`, `end_time`, `semester`, `academic_year`, `schedule_type`, `is_active`)
SELECT 
    (SELECT id FROM `sections` WHERE `section_name` = 'BSCS 1-B' LIMIT 1),
    (SELECT id FROM `subjects` WHERE `subject_code` = 'PE 4' LIMIT 1),
    (SELECT id FROM `faculty` LIMIT 1),
    (SELECT id FROM `rooms` WHERE `room_number` = 'Basketball Court' LIMIT 1), -- Different room
    'Monday', '08:00:00', '10:00:00', '2nd Semester', '2025-2026', 'lecture', 1;

