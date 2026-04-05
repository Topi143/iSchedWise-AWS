# Appendix D
# USER MANUAL

## Table of Contents
1. System Overview
2. System Requirements
3. User Roles and Access Levels
4. Login and Authentication
5. System Dashboard and Navigation
6. Features and Modules
7. Role-Based User Guide
8. Common Tasks
9. Troubleshooting
10. Logout Procedure

---

## 1. System Overview

### 1.1 Introduction
iSchedWise V4 is a web-based school scheduling system designed to manage class and exam scheduling in a centralized, role-based platform. The system is built for institutional scheduling operations such as program setup, curriculum management, faculty assignment, room utilization, reporting, archiving, and administrative controls.

It helps institutions organize scheduling workflows, reduce manual errors, enforce conflict checks, and generate reliable reports for planning and compliance.

**Figure 1. System Login Page**  
[Insert screenshot here: Login page with username/email and password fields]

### 1.2 Purpose of the System
The system was developed to:
1. Improve class and exam scheduling processes.
2. Reduce scheduling conflicts involving sections, faculty, and rooms.
3. Provide secure role-based access for school personnel.
4. Improve visibility of faculty workload and room utilization.
5. Generate exportable reports for academic planning.
6. Preserve historical records through archives and activity logs.

### 1.3 Objectives
1. Provide a digital platform for end-to-end scheduling operations.
2. Support department-scoped access for dean-level users.
3. Enable administrative setup for programs, curriculum, faculty, rooms, and schedule parameters.
4. Deliver role-appropriate dashboards and analytics.
5. Maintain organized and auditable scheduling data.

---

## 2. System Requirements

### 2.1 Hardware Requirements
#### Client Computer
1. Processor: Dual-core 2.0 GHz or higher
2. RAM: 4 GB minimum
3. Storage: At least 500 MB free space
4. Display: 1366 x 768 or higher
5. Input devices: Keyboard and mouse or touch-enabled device

#### Server or Host Computer
1. Processor: Quad-core 2.4 GHz or higher
2. RAM: 8 GB or higher
3. Storage: At least 20 GB free space
4. Stable local network or internet connection
5. MySQL-capable environment

### 2.2 Software Requirements
1. Operating System: Windows 10 or Windows 11 (development and deployment commonly tested)
2. Python: 3.8 or higher (project environment currently uses Python 3.x)
3. Database: MySQL 8.0 or higher
4. Application Framework: Flask 3.x
5. Required Python dependencies installed from project requirements file

### 2.3 Browser Requirements
The system can be accessed using:
1. Google Chrome
2. Microsoft Edge
3. Mozilla Firefox
4. Safari

### 2.4 Recommended Browser
Google Chrome or Microsoft Edge is recommended for best compatibility and performance.

---

## 3. User Roles and Access Levels

iSchedWise V4 uses role-based access control. Users can only access modules allowed by their assigned role.

### 3.1 Super Admin
The Super Admin handles top-level administration, monitoring, and protected maintenance operations.

Access Rights:
1. Access Super Admin dashboard
2. View system monitoring and activity logs
3. Manage global branding and maintenance controls
4. Access protected database tools and backup controls
5. Perform controlled cleanup/reset operations with typed confirmation
6. Manage and monitor users at a system level

### 3.2 Admin
The Admin manages day-to-day scheduling and academic setup.

Access Rights:
1. Manage programs and sections
2. Manage curriculum and subjects
3. Manage faculty and assignments
4. Manage buildings and rooms
5. Create and manage class schedules
6. Create and manage exam schedules
7. Access reports and exports
8. Access archives and restore workflows
9. Manage user accounts
10. Configure institution and scheduling settings

### 3.3 Dean
The Dean manages scheduling operations within assigned program or department scope.

Access Rights:
1. Access Dean-filtered dashboard
2. View and manage assigned programs
3. Manage curriculum and schedules within assigned scope
4. View faculty, workload, and room usage in assigned scope
5. Access reports and exports within assigned scope
6. Access archive views relevant to allowed data scope

Important Notes:
1. Dean views are filtered to assigned programs or departments.
2. Features not assigned to the role are hidden or blocked.

### 3.4 Roles Not Active in Current Release
1. Student portal is not an active role in this release.
2. Faculty self-service login portal is not an active role in this release.
3. Guidance-specific role is not part of the current implemented role set.

**Figure 2. Example Role Access Matrix (Implemented Roles)**  
[Insert screenshot here: Single permissions matrix example for Super Admin, Admin, and Dean]

Sample matrix format:

| Module | Super Admin | Admin | Dean |
|---|---|---|---|
| Dashboard | Full | Full | Filtered |
| Users | Full | Full | No |
| Schedules | Full | Full | Scope-limited |
| Reports | Full | Full | Scope-limited |
| Database Tools | Full | No | No |

---

## 4. Login and Authentication

### 4.1 Login Procedure
1. Open the iSchedWise V4 web application in your browser.
2. Wait for the Login page to load.
3. Enter your username or registered email.
4. Enter your password.
5. Click Login.
6. If two-factor authentication is enabled for your account, complete verification.
7. After successful login, the system redirects you to your role-appropriate dashboard.

**Figure 3. Login Interface**  
[Insert screenshot here: Completed login form before submit]

### 4.2 Forgot Password Procedure
1. Click Forgot Password on the Login page.
2. Enter your registered email address.
3. Submit the request.
4. Open the reset email.
5. Click the reset link.
6. Enter and confirm a new password.
7. Submit the reset form.
8. Return to Login and sign in.

**Figure 4. Forgot Password Page**  
[Insert screenshot here: Forgot password email input form]

**Figure 5. Reset Password Page**  
[Insert screenshot here: New password and confirm password form]

### 4.3 Password Requirements
A valid password must:
1. Have at least 8 characters
2. Include at least one uppercase letter
3. Include at least one number
4. Include at least one special character

### 4.4 First Login Setup (If Required)
Some accounts generated by administrators may require first-time setup.

1. Sign in using initial credentials.
2. Complete required profile and password setup fields.
3. Save and continue to dashboard.

### 4.5 Important Authentication Notes
1. Access is role-protected and enforced server-side.
2. Inactive or archived accounts cannot proceed to normal modules.
3. Session protection and CSRF controls are enforced for sensitive actions.

---

## 5. System Dashboard and Navigation

### 5.1 Dashboard Overview
After login, each user is redirected to a role-specific dashboard.

Common Dashboard Elements:
1. Summary cards
2. Academic term context
3. Quick navigation actions
4. Charts and trend indicators
5. Recent activity and status snippets

### 5.2 Navigation Menu
The sidebar provides module access based on role and permissions.

General Navigation Procedure:
1. Click a menu item to open a module.
2. The active page is highlighted.
3. Use submenu entries for specialized views.
4. Use profile menu for account actions and logout.

**Figure 6. Example Sidebar Navigation**  
[Insert screenshot here: Sidebar with expanded Scheduling and Reports menus]

### 5.3 Dashboard Screens by Role
1. Super Admin Dashboard: System-level monitoring and controls
2. Admin Dashboard: Full operational scheduling and management summary
3. Dean Dashboard: Filtered summary for assigned program or department scope

**Figure 7. Super Admin Dashboard**  
[Insert screenshot here: Super Admin dashboard overview cards]

**Figure 8. Admin Dashboard**  
[Insert screenshot here: Admin dashboard with scheduling summary]

**Figure 9. Dean Dashboard**  
[Insert screenshot here: Dean dashboard filtered by assigned programs]

---

## 6. Features and Modules

### 6.1 Program Management
Purpose: Manage programs and related section organization.

Procedure:
1. Log in as Admin or authorized Dean.
2. Open Programs.
3. Add or select a program.
4. Update details as needed.
5. Save changes.

Expected Result: Program records are available for curriculum and scheduling.

**Figure 10. Program Management Page**  
[Insert screenshot here: Program list with detail panel]

### 6.2 Curriculum Management
Purpose: Organize year levels, semesters, and subjects under each program.

Procedure:
1. Open Curriculum.
2. Add or edit curriculum.
3. Add year levels and semesters.
4. Add or import subjects.
5. Save and verify structure.

Expected Result: Curriculum is ready for faculty assignment and schedule creation.

**Figure 11. Curriculum Management Page**  
[Insert screenshot here: Curriculum hierarchy with subjects table]

### 6.3 Faculty Management
Purpose: Manage faculty records, assignments, workload, and availability.

Procedure:
1. Open Faculty.
2. Add or edit faculty profile.
3. Assign subjects for active term.
4. Configure availability if required.
5. Review workload indicators.

Expected Result: Faculty records are schedulable and visible in reports.

**Figure 12. Faculty Management Page**  
[Insert screenshot here: Faculty master-detail panel with assignments tab]

### 6.4 Building and Room Management
Purpose: Maintain building and room inventory for scheduling.

Procedure:
1. Open Buildings.
2. Add or edit building records.
3. Add rooms and define attributes.
4. Save updates.

Expected Result: Rooms are available in class and exam schedule forms.

**Figure 13. Building and Room Management Page**  
[Insert screenshot here: Building list with room panel]

### 6.5 Class Scheduling Module
Purpose: Create and maintain class timetables with conflict checks.

Procedure:
1. Open Schedules and choose Create New or Class View.
2. Select section, subject, faculty, room, day, and time.
3. Run conflict checks and review warnings.
4. Save schedule.
5. Edit or remove entries as needed.

Expected Result: Schedule is stored and reflected in Class, Faculty, and Room views.

**Figure 14. Class Scheduling Form**  
[Insert screenshot here: Add class schedule modal/form]

**Figure 15. Class Schedule View**  
[Insert screenshot here: Class schedules table grouped by section]

### 6.6 Exam Scheduling Module
Purpose: Manage exam schedules by term and exam period.

Procedure:
1. Open Schedules and select Exam View.
2. Create exam entries with section, subject, room, date, and time.
3. Validate conflicts.
4. Save and review entries.

Expected Result: Exam schedule is available in exam views and reports.

**Figure 16. Exam Scheduling Page**  
[Insert screenshot here: Exam schedule table with add/edit actions]

### 6.7 Reports and Export
Purpose: Generate operational and analytical reports.

Procedure:
1. Open Reports.
2. Select report type (Overview, Faculty, Rooms, Weekly, Compare, Activity as permitted).
3. Apply filters.
4. Export to available file format.

Expected Result: Downloadable report is generated based on selected filters.

**Figure 17. Reports Overview Page**  
[Insert screenshot here: Reports dashboard with cards and charts]

**Figure 18. Faculty Workload Report**  
[Insert screenshot here: Faculty report table with utilization indicators]

### 6.8 Archive and Activity Logs
Purpose: Preserve historical records and audit actions.

Procedure:
1. Open Archives or Activity modules.
2. Filter archived schedules, curriculum, programs, faculty, or buildings.
3. Restore records where applicable.
4. Permanently delete only when authorized.

Expected Result: Historical records remain traceable and manageable.

**Figure 19. Archives Overview Page**  
[Insert screenshot here: Archive module summary and category links]

**Figure 20. Activity Logs Page**  
[Insert screenshot here: Activity log table with filters]

### 6.9 User Management
Purpose: Manage Admin and Dean accounts.

Procedure:
1. Open Users (Admin and Super Admin access).
2. Add user with role and required details.
3. Edit role, assignments, and status.
4. Activate/deactivate or archive user as needed.
5. Reset passwords when necessary.

Expected Result: User account lifecycle is managed securely.

**Figure 21. User Management Page**  
[Insert screenshot here: Users table with role and status controls]

### 6.10 Settings Module
Purpose: Configure institution and academic scheduling parameters.

Procedure:
1. Open Settings.
2. Review or update Academic Settings.
3. Configure class schedule windows and exam settings.
4. Configure faculty load thresholds.
5. Save and apply changes.

Expected Result: Active settings are applied in scheduling and validation logic.

**Figure 22. Settings Page**  
[Insert screenshot here: Settings tabs with academic and schedule controls]

### 6.11 Super Admin Database and Maintenance Tools
Purpose: Provide controlled high-risk operations and backup workflows.

Procedure:
1. Open Super Admin tools pages.
2. Review database health and backup status.
3. Create manual backup if needed.
4. Configure automatic backup settings.
5. Execute cleanup/reset operations only after confirmation prompts.

Expected Result: System maintenance is performed with audit visibility and safeguards.

**Figure 23. Database Management Tools**  
[Insert screenshot here: Database tab with backup and cleanup panels]

**Figure 24. Super Admin Monitoring Page**  
[Insert screenshot here: Super Admin dashboard monitoring widgets]

---

## 7. Role-Based User Guide

### 7.1 Super Admin User Guide

Accessing the Dashboard:
1. Log in with Super Admin credentials.
2. Open Super Admin dashboard.
3. Review system status cards and activity trends.

Using System Features:
1. Monitor system-level activity.
2. Access protected database management tools.
3. Create and manage backups.
4. Execute approved maintenance actions.

Managing Data:
1. Oversee user lifecycle and account security.
2. Review archives and activity logs.
3. Verify system settings and global controls.

Generating Reports:
1. Open Reports module.
2. Apply required filters.
3. Export reports for audit and operational review.

**Figure 25. Super Admin Operational Workflow**  
[Insert screenshot here: Sequence of monitoring, backup, and maintenance actions]

### 7.2 Admin User Guide

Accessing the Dashboard:
1. Log in with Admin credentials.
2. Open Admin dashboard and review summary cards.

Using System Features:
1. Manage programs, curriculum, and subjects.
2. Manage faculty, rooms, and buildings.
3. Create and maintain class and exam schedules.
4. Access reports and archives.
5. Manage user accounts.

Managing Data:
1. Create and update institutional records.
2. Archive obsolete records when needed.
3. Keep active term data accurate and consistent.

Generating Reports:
1. Open Reports.
2. Select report type and filter scope.
3. Export for printing or sharing.

**Figure 26. Admin Main Modules**  
[Insert screenshot here: Admin sidebar with key modules expanded]

### 7.3 Dean User Guide

Accessing the Dashboard:
1. Log in with Dean credentials.
2. Open Dean dashboard filtered to assigned programs.

Using System Features:
1. View and manage schedules within allowed scope.
2. Review faculty workload and room usage in assigned scope.
3. Access reports and archive views relevant to assigned scope.

Managing Data:
1. Maintain schedule quality in assigned programs.
2. Coordinate faculty-room-time alignment within authorized scope.

Generating Reports:
1. Open Reports.
2. Apply program-level filters.
3. Export results for department use.

**Figure 27. Dean Filtered Views**  
[Insert screenshot here: Dean view showing filtered programs or schedules]

---

## 8. Common Tasks

### 8.1 Creating a User Account
1. Open Users.
2. Click Add User.
3. Enter username, email, full name, role, and password.
4. For Dean accounts, assign programs if required.
5. Save.

Expected Result: User account is created and can log in based on role.

**Figure 28. Add User Process**  
[Insert screenshot here: Add user modal with role selector]

### 8.2 Adding a Faculty Record
1. Open Faculty.
2. Click Add Faculty.
3. Enter required faculty details.
4. Save.
5. Assign subjects if needed.

Expected Result: Faculty appears in faculty list and schedule forms.

**Figure 29. Add Faculty Process**  
[Insert screenshot here: Faculty form submission]

### 8.3 Creating a Class Schedule
1. Open Schedules and choose Create New.
2. Select section and subject.
3. Assign faculty and room.
4. Set day and time.
5. Run conflict checks.
6. Save schedule.

Expected Result: Schedule entry is stored and visible in related views.

**Figure 30. Create Class Schedule Process**  
[Insert screenshot here: Filled schedule form with conflict check results]

### 8.4 Creating an Exam Schedule
1. Open Schedules and choose Exam View.
2. Click Add Exam Schedule.
3. Select section, subject, date, room, and time.
4. Save and verify.

Expected Result: Exam schedule entry appears in exam table and reports.

**Figure 31. Create Exam Schedule Process**  
[Insert screenshot here: Add exam schedule workflow]

### 8.5 Generating a Report
1. Open Reports.
2. Choose report type.
3. Apply filters.
4. Click Export.

Expected Result: Report is downloaded successfully.

**Figure 32. Report Generation Process**  
[Insert screenshot here: Reports page with applied filters and export action]

### 8.6 Restoring an Archived Record
1. Open Archives.
2. Select archive category.
3. Filter target record.
4. Click Restore.

Expected Result: Restored record becomes active in corresponding module.

**Figure 33. Archive Restore Process**  
[Insert screenshot here: Archive table restore action]

### 8.7 Creating a Manual Database Backup (Super Admin)
1. Open Super Admin database tools.
2. Click Create Backup.
3. Wait for completion confirmation.
4. Verify backup appears in backup list.

Expected Result: New backup file is listed and downloadable.

**Figure 34. Manual Backup Process**  
[Insert screenshot here: Database tools backup panel after successful backup]

---

## 9. Troubleshooting

### 9.1 Invalid Username or Password
Possible Cause: Incorrect credentials.

Solution:
1. Re-enter username/email and password.
2. Check for typing errors and keyboard state.
3. Use Forgot Password if needed.
4. Contact an administrator if issue persists.

**Figure 35. Invalid Login Message**  
[Insert screenshot here: Login error notification]

### 9.2 No Active Academic Settings or Term Mismatch
Possible Cause: Academic settings are not active or selected data does not match active term.

Solution:
1. Verify active academic settings in Settings.
2. Confirm semester and academic year alignment.
3. Refresh module and retry operation.

### 9.3 Schedule Conflict Prevents Save
Possible Cause: Section, faculty, or room is already booked in the selected time slot.

Solution:
1. Check conflict details shown by system.
2. Change time, room, or faculty assignment.
3. Re-run conflict check.
4. Save after conflict-free validation.

**Figure 36. Conflict Warning Example**  
[Insert screenshot here: Schedule conflict feedback panel]

### 9.4 Dean Cannot View Expected Data
Possible Cause: Data belongs to programs outside assigned dean scope.

Solution:
1. Confirm assigned program access.
2. Ask Admin to update dean assignments if needed.
3. Refresh and retry.

### 9.5 Password Reset Email Not Received
Possible Cause: Email delay, filter, or address mismatch.

Solution:
1. Check spam or junk folder.
2. Confirm registered email.
3. Submit reset request again.
4. Contact system administrator if unresolved.

### 9.6 Backup or Maintenance Action Failed
Possible Cause: Missing permissions, invalid confirmation phrase, or server/database issue.

Solution:
1. Confirm Super Admin access.
2. Re-enter required typed confirmation exactly.
3. Check database health panel.
4. Retry after creating a fresh backup.

### 9.7 Page Not Displaying Properly
Possible Cause: Browser cache, extension conflict, or unstable connection.

Solution:
1. Refresh page.
2. Clear browser cache.
3. Use updated Chrome or Edge browser.
4. Re-login if session expired.

**Figure 37. Example System Warning or Error Toast**  
[Insert screenshot here: In-app error toast or warning message]

---

## 10. Logout Procedure

### Proper Logout Steps
1. Open the profile menu in the sidebar or top navigation.
2. Click Logout.
3. Wait for session termination.
4. Confirm redirection to Login page.

**Figure 38. Logout Option**  
[Insert screenshot here: Profile menu with logout action]

### Importance of Proper Logout
1. Protects account access on shared devices.
2. Prevents unauthorized use of active sessions.
3. Ensures secure completion of user activity.

---

## Conclusion

iSchedWise V4 provides a centralized and role-based platform for school scheduling operations, from academic setup and scheduling to reporting, archives, and controlled administration tools. This manual is structured for operational onboarding, thesis documentation, and user training.

To complete this appendix for final submission, insert the required screenshots at each Figure placeholder listed above.