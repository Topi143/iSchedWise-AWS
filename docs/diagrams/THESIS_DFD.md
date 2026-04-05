# iSchedWise V4 — Data Flow Diagrams

> **Thesis Appendix C — Section 3.2: Data Flow Diagram (DFD)**
>
> Diagrams are presented at three levels: **Context Diagram (Level 0)**, **Level 1 DFD** (main processes), and **Level 2 DFDs** (process decompositions). The visual style follows the thesis reference format: external entities are **tagged rectangles**, processes are **numbered process cards** (number, action, owner lane), data stores are **ID-labeled repositories**, and flows are labeled arrows.

> **See also:** [THESIS_ARCHITECTURE.md](THESIS_ARCHITECTURE.md) for client-server and container architecture views.

---

## Data Stores Reference

| ID | Name | Description |
|----|------|-------------|
| D1 | Users | User accounts, roles, credentials, program access, and trusted-device auth state |
| D2 | Schedules | Class and exam schedules, including schedule snapshot state |
| D3 | Faculty | Faculty profiles, availability, and subject assignments |
| D4 | Buildings & Rooms | Building info, room types and capacities |
| D5 | Programs & Sections | Programs, sections, and departments |
| D6 | Curriculum & Subjects | Curricula, year levels, semesters, and subjects |
| D7 | Settings | Academic config, institution profile, system configuration, and user preferences |
| D8 | Activity Logs | Audit trail and system event logs |
| D9 | Archive Records | Archived schedules, faculty, programs, curricula, buildings |
| D10 | Login History | Login sessions, logout records, and access history |

---

## Process Reference

| # | Process | Description |
|---|---------|-------------|
| 1 | User Authentication | Login, session management, first-login setup |
| 2 | Schedule Management | Class & exam schedule create/edit/delete/export |
| 3 | Faculty Management | Faculty CRUD, assignments, availability, archive |
| 4 | Building & Room Management | Building and room CRUD, archive |
| 5 | Program & Section Management | Programs, sections, and department CRUD |
| 6 | Curriculum Management | Curricula, subjects, year levels, bulk import |
| 7 | Report Generation | All report types, filters, PDF/Excel export |
| 8 | System Settings & Operations | Academic/institution settings, department config, maintenance, security sessions, and database tools |
| 9 | User Management | User CRUD, roles, access control, bulk operations |
| 10 | Archive Management | View, restore, delete, export archived entities |
| 11 | Profile Management | Self-service profile update and password change for all roles |

---

## Context Diagram (Level 0)

```mermaid
flowchart LR
    SA["sa<br/>Super Admin"]
    AD["ad<br/>Admin"]
    DN["dn<br/>Dean"]
    GEMINI["g<br/>Google Gemini API"]
    EMAIL["e<br/>Email Server"]
    SYS["0.0<br/>iSchedWise V4<br/><i>Scheduling System</i>"]

    SA -->|"Credentials, System Settings,\nMaintenance Commands, Security Operations"| SYS
    AD -->|"Credentials, Schedule / Faculty /\nBuilding / Program / Curriculum Data"| SYS
    DN -->|"Credentials, Schedule / Faculty /\nBuilding / Curriculum Data"| SYS

    SYS -->|"Reports, Audit Logs,\nSystem Operation Status, Confirmations"| SA
    SYS -->|"Schedules, Reports,\nConfirmations"| AD
    SYS -->|"Filtered Schedules,\nFiltered Reports, Confirmations"| DN

    SYS -->|"Schedule / Conflict\nData Request"| GEMINI
    GEMINI -->|"AI Recommendations\n& Explanations"| SYS

    SYS -->|"Password Reset\nEmail Request"| EMAIL
    EMAIL -->|"Delivery Status"| SYS

    classDef entity fill:#f7d58c,stroke:#333,stroke-width:2px,color:#111;
    classDef system fill:#d6ebff,stroke:#333,stroke-width:3px,color:#111;

    class SA,AD,DN,GEMINI,EMAIL entity;
    class SYS system;
```

---

## Level 1 DFD

> *Simplified overview showing primary data flows. All write-capable processes also log to D8 (Activity Logs) upon completion.*

```mermaid
flowchart TD
    SA["sa<br/>Super Admin"]
    AD["ad<br/>Admin"]
    DN["dn<br/>Dean"]

    P1["1.0<br/>User Authentication<br/><i>Authentication</i>"]
    P2["2.0<br/>Schedule Management<br/><i>Scheduling</i>"]
    P3["3.0<br/>Faculty Management<br/><i>Faculty</i>"]
    P4["4.0<br/>Building & Room Management<br/><i>Facilities</i>"]
    P5["5.0<br/>Program & Section Management<br/><i>Programs</i>"]
    P6["6.0<br/>Curriculum Management<br/><i>Curriculum</i>"]
    P7["7.0<br/>Report Generation<br/><i>Reporting</i>"]
    P8["8.0<br/>System Settings & Operations<br/><i>Operations</i>"]
    P9["9.0<br/>User Management<br/><i>Administration</i>"]
    P10["10.0<br/>Archive Management<br/><i>Archive</i>"]
    P11["11.0<br/>Profile Management<br/><i>User Profile</i>"]

    D1["D1<br/>Users"]
    D2["D2<br/>Schedules"]
    D3["D3<br/>Faculty"]
    D4["D4<br/>Buildings & Rooms"]
    D5["D5<br/>Programs & Sections"]
    D6["D6<br/>Curriculum & Subjects"]
    D7["D7<br/>Settings"]
    D8["D8<br/>Activity Logs"]
    D9["D9<br/>Archive Records"]
    D10["D10<br/>Login History"]

    SA --> P1 & P2 & P3 & P4 & P5 & P6 & P7 & P8 & P9 & P10 & P11
    AD --> P1 & P2 & P3 & P4 & P5 & P6 & P7 & P8 & P9 & P10 & P11
    DN --> P1 & P2 & P3 & P4 & P5 & P6 & P7 & P8 & P10 & P11

    P1 & P7 & P8 & P9 & P11 --- D1
    P1 & P8 --- D10

    P2 & P3 & P4 & P5 & P6 & P7 & P8 & P10 --- D2
    P2 & P3 & P7 & P8 & P10 --- D3
    P2 & P4 & P7 & P10 --- D4
    P2 & P3 & P5 & P6 & P7 & P8 & P9 & P10 --- D5
    P2 & P3 & P5 & P6 & P7 & P10 --- D6
    P2 & P3 & P6 & P7 & P8 --- D7

    P8 & P10 --- D9
    P1 & P2 & P3 & P4 & P5 & P6 & P7 & P8 & P9 & P10 & P11 --- D8

    classDef entity fill:#f7d58c,stroke:#333,stroke-width:2px,color:#111;
    classDef process fill:#f5f5f5,stroke:#333,stroke-width:2px,color:#111;
    classDef store fill:#ffffff,stroke:#333,stroke-width:2px,color:#111;

    class SA,AD,DN entity;
    class P1,P2,P3,P4,P5,P6,P7,P8,P9,P10,P11 process;
    class D1,D2,D3,D4,D5,D6,D7,D8,D9,D10 store;
```

---

## Level 2 — Process 1: User Authentication

```mermaid
flowchart LR
    USR["u<br/>User (Admin / Dean / Super Admin)"]
    P11["1.1<br/>Validate Credentials<br/><i>Authentication</i>"]
    P12["1.2<br/>Check Account Status<br/><i>Authentication</i>"]
    P13["1.3<br/>Verify 2FA / Trusted Device<br/><i>Authentication</i>"]
    P14["1.4<br/>Create Session<br/><i>Authentication</i>"]
    P15["1.5<br/>First-Login Setup<br/><i>Authentication</i>"]
    ERR1["E1<br/>Invalid Credentials"]
    ERR2["E2<br/>Account Deactivated"]
    ERR3["E3<br/>Verification Failed"]
    D1["D1<br/>Users"]
    D8["D8<br/>Activity Logs"]
    D10["D10<br/>Login History"]

    USR -->|"Login Credentials"| P11
    P11 <-->|"Read"| D1
    P11 -->|"Validate"| P12
    P11 -->|"Invalid"| ERR1 --> USR
    P12 <-->|"Read"| D1
    P12 -->|"Active"| P13
    P12 -->|"Inactive"| ERR2 --> USR
    P13 <-->|"Read 2FA / Trusted State"| D1
    P13 -->|"Verified / Trusted"| P14
    P13 -->|"Invalid / Expired"| ERR3 --> USR
    P14 -->|"Write Session"| D10
    P14 -->|"Log"| D8
    P14 -->|"First Login?"| P15
    P14 -->|"Dashboard Redirect"| USR
    P15 <-->|"Read / Write"| D1
    P15 -->|"Log"| D8
    P15 -->|"Setup Complete\n& Dashboard Redirect"| USR

    classDef entity fill:#f7d58c,stroke:#333,stroke-width:2px,color:#111;
    classDef process fill:#f5f5f5,stroke:#333,stroke-width:2px,color:#111;
    classDef store fill:#ffffff,stroke:#333,stroke-width:2px,color:#111;
    classDef error fill:#ffe8e8,stroke:#991b1b,stroke-width:1.5px,color:#7f1d1d;

    class USR entity;
    class P11,P12,P13,P14,P15 process;
    class D1,D8,D10 store;
    class ERR1,ERR2,ERR3 error;
```

---

## Level 2 — Process 2: Schedule Management

```mermaid
flowchart LR
    USR["u<br/>User (Admin / Dean)"]
    P21["2.1<br/>Retrieve Scheduling Context<br/><i>Scheduling</i>"]
    P22["2.2<br/>Validate Constraints & Conflicts<br/><i>Scheduling</i>"]
    P23["2.3<br/>Save Schedule Changes<br/><i>Scheduling</i>"]
    ERR["E1<br/>Conflict Detected"]
    D2["D2<br/>Schedules"]
    D3["D3<br/>Faculty"]
    D4["D4<br/>Buildings & Rooms"]
    D5["D5<br/>Programs & Sections"]
    D6["D6<br/>Curriculum & Subjects"]
    D7["D7<br/>Settings"]
    D8["D8<br/>Activity Logs"]

    USR -->|"Schedule Data\n(Add / Edit / Delete / Export)"| P21
    P21 <-->|"Read / Write"| D2
    P21 -->|"Read Faculty &\nAvailability"| D3
    P21 -->|"Read Rooms"| D4
    P21 -->|"Read Sections\n& Programs"| D5
    P21 -->|"Read Subjects"| D6
    P21 -->|"Read Time Range\n& Settings"| D7
    P21 -->|"Validate"| P22
    P22 -->|"Conflict\nDetected"| ERR --> USR
    P22 -->|"No Conflict"| P23
    P23 -->|"Write Schedule"| D2
    P23 -->|"Write Faculty\nAssignment"| D3
    P23 -->|"Log"| D8
    P23 -->|"Confirmation /\nFile Download"| USR

    classDef entity fill:#f7d58c,stroke:#333,stroke-width:2px,color:#111;
    classDef process fill:#f5f5f5,stroke:#333,stroke-width:2px,color:#111;
    classDef store fill:#ffffff,stroke:#333,stroke-width:2px,color:#111;
    classDef error fill:#ffe8e8,stroke:#991b1b,stroke-width:1.5px,color:#7f1d1d;

    class USR entity;
    class P21,P22,P23 process;
    class D2,D3,D4,D5,D6,D7,D8 store;
    class ERR error;
```

---

## Level 2 — Process 3: Faculty Management

```mermaid
flowchart LR
    USR["u<br/>User (Admin / Dean)"]
    P31["3.1<br/>Retrieve Faculty Data<br/><i>Faculty</i>"]
    P32["3.2<br/>Validate Faculty Inputs<br/><i>Faculty</i>"]
    P33["3.3<br/>Save Faculty Changes<br/><i>Faculty</i>"]
    ERR["E1<br/>Validation Failed"]
    D2["D2<br/>Schedules"]
    D3["D3<br/>Faculty"]
    D5["D5<br/>Programs & Sections"]
    D6["D6<br/>Curriculum & Subjects"]
    D7["D7<br/>Settings"]
    D8["D8<br/>Activity Logs"]

    USR -->|"Faculty Data\n(Add / Edit / Archive /\nAssign / Set Availability / Export)"| P31
    P31 <-->|"Read / Write"| D3
    P31 -->|"Read Subjects"| D6
    P31 -->|"Read Programs\n& Departments"| D5
    P31 -->|"Read Active\nAcademic Year"| D7
    P31 -->|"Validate"| P32
    P32 -->|"Invalid"| ERR --> USR
    P32 -->|"Valid"| P33
    P33 -->|"Write"| D3
    P33 -->|"Delete Linked\nSchedules"| D2
    P33 -->|"Log"| D8
    P33 -->|"Confirmation"| USR

    classDef entity fill:#f7d58c,stroke:#333,stroke-width:2px,color:#111;
    classDef process fill:#f5f5f5,stroke:#333,stroke-width:2px,color:#111;
    classDef store fill:#ffffff,stroke:#333,stroke-width:2px,color:#111;
    classDef error fill:#ffe8e8,stroke:#991b1b,stroke-width:1.5px,color:#7f1d1d;

    class USR entity;
    class P31,P32,P33 process;
    class D2,D3,D5,D6,D7,D8 store;
    class ERR error;
```

---

## Level 2 — Process 4: Building & Room Management

```mermaid
flowchart LR
    USR["u<br/>User (Admin / Dean)"]
    P41["4.1<br/>Retrieve Building / Room Data<br/><i>Facilities</i>"]
    P42["4.2<br/>Validate Facility Inputs<br/><i>Facilities</i>"]
    P43["4.3<br/>Save Building / Room Changes<br/><i>Facilities</i>"]
    ERR["E1<br/>Validation Failed"]
    D2["D2<br/>Schedules"]
    D4["D4<br/>Buildings & Rooms"]
    D8["D8<br/>Activity Logs"]

    USR -->|"Building / Room Data\n(Add / Edit / Archive / Delete)"| P41
    P41 <-->|"Read / Write"| D4
    P41 -->|"Check Linked\nSchedules"| D2
    P41 -->|"Validate"| P42
    P42 -->|"Invalid"| ERR --> USR
    P42 -->|"Valid"| P43
    P43 -->|"Write"| D4
    P43 -->|"Delete Linked\nSchedules"| D2
    P43 -->|"Log"| D8
    P43 -->|"Confirmation"| USR

    classDef entity fill:#f7d58c,stroke:#333,stroke-width:2px,color:#111;
    classDef process fill:#f5f5f5,stroke:#333,stroke-width:2px,color:#111;
    classDef store fill:#ffffff,stroke:#333,stroke-width:2px,color:#111;
    classDef error fill:#ffe8e8,stroke:#991b1b,stroke-width:1.5px,color:#7f1d1d;

    class USR entity;
    class P41,P42,P43 process;
    class D2,D4,D8 store;
    class ERR error;
```

---

## Level 2 — Process 5: Program & Section Management

```mermaid
flowchart LR
    USR["u<br/>Admin / Super Admin / Dean"]
    P51["5.1<br/>Retrieve Program / Section Data<br/><i>Programs</i>"]
    P52["5.2<br/>Validate Program Rules<br/><i>Programs</i>"]
    P53["5.3<br/>Save Program / Section Changes<br/><i>Programs</i>"]
    ERR["E1<br/>Validation Failed"]
    D2["D2<br/>Schedules"]
    D5["D5<br/>Programs & Sections"]
    D6["D6<br/>Curriculum & Subjects"]
    D8["D8<br/>Activity Logs"]

    USR -->|"Program / Section Data\n(Add / Edit / Toggle /\nArchive / Delete)"| P51
    P51 <-->|"Read / Write"| D5
    P51 -->|"Validate"| P52
    P52 -->|"Invalid"| ERR --> USR
    P52 -->|"Valid"| P53
    P53 -->|"Write"| D5
    P53 -->|"Archive Linked\nCurricula"| D6
    P53 -->|"Delete Linked\nSchedules"| D2
    P53 -->|"Log"| D8
    P53 -->|"Confirmation"| USR

    classDef entity fill:#f7d58c,stroke:#333,stroke-width:2px,color:#111;
    classDef process fill:#f5f5f5,stroke:#333,stroke-width:2px,color:#111;
    classDef store fill:#ffffff,stroke:#333,stroke-width:2px,color:#111;
    classDef error fill:#ffe8e8,stroke:#991b1b,stroke-width:1.5px,color:#7f1d1d;

    class USR entity;
    class P51,P52,P53 process;
    class D2,D5,D6,D8 store;
    class ERR error;
```

---

## Level 2 — Process 6: Curriculum Management

```mermaid
flowchart LR
    USR["u<br/>User (Admin / Dean)"]
    P61["6.1<br/>Retrieve Curriculum Data<br/><i>Curriculum</i>"]
    P62["6.2<br/>Validate Curriculum Rules<br/><i>Curriculum</i>"]
    P63["6.3<br/>Save Curriculum Changes<br/><i>Curriculum</i>"]
    ERR["E1<br/>Validation Failed"]
    D2["D2<br/>Schedules"]
    D5["D5<br/>Programs & Sections"]
    D6["D6<br/>Curriculum & Subjects"]
    D7["D7<br/>Settings"]
    D8["D8<br/>Activity Logs"]

    USR -->|"Curriculum / Subject Data\n(Add / Edit / Archive /\nDelete / Bulk Import)"| P61
    P61 <-->|"Read / Write"| D6
    P61 -->|"Read Programs"| D5
    P61 -->|"Read Available\nSemesters"| D7
    P61 -->|"Validate"| P62
    P62 -->|"Invalid"| ERR --> USR
    P62 -->|"Valid"| P63
    P63 -->|"Write"| D6
    P63 -->|"Delete Linked\nSchedules"| D2
    P63 -->|"Log"| D8
    P63 -->|"Confirmation"| USR

    classDef entity fill:#f7d58c,stroke:#333,stroke-width:2px,color:#111;
    classDef process fill:#f5f5f5,stroke:#333,stroke-width:2px,color:#111;
    classDef store fill:#ffffff,stroke:#333,stroke-width:2px,color:#111;
    classDef error fill:#ffe8e8,stroke:#991b1b,stroke-width:1.5px,color:#7f1d1d;

    class USR entity;
    class P61,P62,P63 process;
    class D2,D5,D6,D7,D8 store;
    class ERR error;
```

---

## Level 2 — Process 7: Report Generation

```mermaid
flowchart LR
    USR["u<br/>User (Admin / Dean)"]
    GEMINI["g<br/>Google Gemini API"]
    P71["7.1<br/>Retrieve Report Inputs<br/><i>Reporting</i>"]
    P72["7.2<br/>Aggregate & Analyze Data<br/><i>Reporting</i>"]
    P73["7.3<br/>Generate Export Output<br/><i>Reporting</i>"]
    D1["D1<br/>Users"]
    D2["D2<br/>Schedules"]
    D3["D3<br/>Faculty"]
    D4["D4<br/>Buildings & Rooms"]
    D5["D5<br/>Programs & Sections"]
    D6["D6<br/>Curriculum & Subjects"]
    D7["D7<br/>Settings"]
    D8["D8<br/>Activity Logs"]

    USR -->|"Report Request\n& Filter Parameters"| P71
    P71 -->|"Read Schedules"| D2
    P71 -->|"Read Faculty"| D3
    P71 -->|"Read Rooms"| D4
    P71 -->|"Read Programs"| D5
    P71 -->|"Read Subjects"| D6
    P71 -->|"Read Settings"| D7
    P71 -->|"Read Activity Logs"| D8
    P71 -->|"Read Users"| D1
    P71 -->|"Aggregated Data"| P72
    P72 -->|"AI Analysis\nRequest"| GEMINI
    GEMINI -->|"AI Summary"| P72
    P72 -->|"Formatted Data"| P73
    P73 -->|"PDF / Excel\nFile Download"| USR

    classDef entity fill:#f7d58c,stroke:#333,stroke-width:2px,color:#111;
    classDef process fill:#f5f5f5,stroke:#333,stroke-width:2px,color:#111;
    classDef store fill:#ffffff,stroke:#333,stroke-width:2px,color:#111;

    class USR,GEMINI entity;
    class P71,P72,P73 process;
    class D1,D2,D3,D4,D5,D6,D7,D8 store;
```

---

## Level 2 — Process 8: System Settings & Operations

```mermaid
flowchart LR
    USR["u<br/>User (Admin / Dean / Super Admin)"]
    P81["8.1<br/>Load Scope & Current Settings<br/><i>Operations</i>"]
    P82["8.2<br/>Validate Role and Request<br/><i>Operations</i>"]
    P83["8.3<br/>Execute System Operation<br/><i>Operations</i>"]
    ERR["E1<br/>Unauthorized or Invalid Request"]
    D1["D1<br/>Users"]
    D2["D2<br/>Schedules"]
    D3["D3<br/>Faculty"]
    D5["D5<br/>Programs & Sections"]
    D7["D7<br/>Settings"]
    D8["D8<br/>Activity Logs"]
    D9["D9<br/>Archive Records"]
    D10["D10<br/>Login History"]

    USR -->|"Settings / System\nOperation Request"| P81
    P81 <-->|"Read / Write"| D7
    P81 <-->|"Read Departments"| D5
    P81 -->|"Validate"| P82
    P82 -->|"Invalid"| ERR --> USR
    P82 -->|"Valid"| P83
    P83 -->|"Store Academic /\nInstitution / Preference Data"| D7
    P83 -->|"Write Departments"| D5
    P83 -->|"Maintenance / DB Ops\nAffecting Schedules"| D2
    P83 -->|"Restore / Sync\nFaculty Assignments"| D3
    P83 -->|"Archive / Restore\nRecords"| D9
    P83 -->|"Security Ops\n(Session / Logout / Reset)"| D1
    P83 -->|"Read / Write\nSession History"| D10
    P83 -->|"Log"| D8
    P83 -->|"Confirmation /\nSystem Status"| USR

    classDef entity fill:#f7d58c,stroke:#333,stroke-width:2px,color:#111;
    classDef process fill:#f5f5f5,stroke:#333,stroke-width:2px,color:#111;
    classDef store fill:#ffffff,stroke:#333,stroke-width:2px,color:#111;
    classDef error fill:#ffe8e8,stroke:#991b1b,stroke-width:1.5px,color:#7f1d1d;

    class USR entity;
    class P81,P82,P83 process;
    class D1,D2,D3,D5,D7,D8,D9,D10 store;
    class ERR error;
```

---

## Level 2 — Process 9: User Management

```mermaid
flowchart LR
    ADM["a<br/>Admin / Super Admin"]
    P91["9.1<br/>Retrieve User Data<br/><i>Administration</i>"]
    P92["9.2<br/>Validate Access & Inputs<br/><i>Administration</i>"]
    P93["9.3<br/>Save User Changes<br/><i>Administration</i>"]
    ERR["E1<br/>Validation Failed"]
    D1["D1<br/>Users"]
    D5["D5<br/>Programs & Sections"]
    D8["D8<br/>Activity Logs"]

    ADM -->|"User Data\n(Add / Edit / Toggle /\nArchive / Bulk / Export)"| P91
    P91 <-->|"Read / Write"| D1
    P91 -->|"Read Activity Logs"| D8
    P91 -->|"Validate"| P92
    P92 <-->|"Read / Assign\nPrograms"| D5
    P92 -->|"Invalid"| ERR --> ADM
    P92 -->|"Valid"| P93
    P93 -->|"Write"| D1
    P93 -->|"Log"| D8
    P93 -->|"Confirmation"| ADM

    classDef entity fill:#f7d58c,stroke:#333,stroke-width:2px,color:#111;
    classDef process fill:#f5f5f5,stroke:#333,stroke-width:2px,color:#111;
    classDef store fill:#ffffff,stroke:#333,stroke-width:2px,color:#111;
    classDef error fill:#ffe8e8,stroke:#991b1b,stroke-width:1.5px,color:#7f1d1d;

    class ADM entity;
    class P91,P92,P93 process;
    class D1,D5,D8 store;
    class ERR error;
```

---

## Level 2 — Process 10: Archive Management

```mermaid
flowchart LR
    USR["u<br/>Admin / Dean / Super Admin"]
    P101["10.1<br/>Retrieve Archive Scope<br/><i>Archive</i>"]
    P102["10.2<br/>Process Archive Action<br/><i>Archive</i>"]
    P103["10.3<br/>Update Archive Records<br/><i>Archive</i>"]
    D2["D2<br/>Schedules"]
    D9["D9<br/>Archive Records"]
    DST["D3-D6<br/>Target Active Data Store"]
    D8["D8<br/>Activity Logs"]

    USR -->|"Archive Request\n(View / Unarchive /\nDelete / Export)"| P101
    P101 <-->|"Read"| D9
    P101 -->|"Read\n(Flag-based\nArchives)"| DST
    P101 -->|"Action"| P102
    P102 -->|"Read / Delete\n(Schedule Archiving)"| D2
    P102 <-->|"Restore / Remove\nfrom Active Store"| DST
    P102 -->|"Update"| P103
    P103 -->|"Write Archive\nRecord"| D9
    P103 -->|"Log\n(Unarchive /\nPermanent Delete)"| D8
    P103 -->|"Confirmation /\nFile Download"| USR

    classDef entity fill:#f7d58c,stroke:#333,stroke-width:2px,color:#111;
    classDef process fill:#f5f5f5,stroke:#333,stroke-width:2px,color:#111;
    classDef store fill:#ffffff,stroke:#333,stroke-width:2px,color:#111;

    class USR entity;
    class P101,P102,P103 process;
    class D2,D9,DST,D8 store;
```

---

## Level 2 — Process 11: Profile Management

> All roles (Super Admin, Admin, Dean) can update their own profile and change their password.

```mermaid
flowchart LR
    USR["u<br/>User (Admin / Dean / Super Admin)"]
    P111["11.1<br/>Retrieve Profile Data<br/><i>User Profile</i>"]
    P112["11.2<br/>Validate Profile Request<br/><i>User Profile</i>"]
    P113["11.3<br/>Save Profile Changes<br/><i>User Profile</i>"]
    ERR["E1<br/>Validation Failed"]
    D1["D1<br/>Users"]
    D8["D8<br/>Activity Logs"]

    USR -->|"Profile Data\n(Update Info /\nChange Password)"| P111
    P111 <-->|"Read"| D1
    P111 -->|"Validate"| P112
    P112 -->|"Invalid"| ERR --> USR
    P112 -->|"Valid"| P113
    P113 -->|"Write"| D1
    P113 -->|"Log"| D8
    P113 -->|"Confirmation"| USR

    classDef entity fill:#f7d58c,stroke:#333,stroke-width:2px,color:#111;
    classDef process fill:#f5f5f5,stroke:#333,stroke-width:2px,color:#111;
    classDef store fill:#ffffff,stroke:#333,stroke-width:2px,color:#111;
    classDef error fill:#ffe8e8,stroke:#991b1b,stroke-width:1.5px,color:#7f1d1d;

    class USR entity;
    class P111,P112,P113 process;
    class D1,D8 store;
    class ERR error;
```

---

## Notation Legend

| Shape | Notation | Meaning |
|-------|----------|---------|
| Tagged Rectangle | `["id<br/>Entity Name"]` | External Entity — actor or system outside the iSchedWise process boundary |
| Process Card | `["1.x<br/>Process Action<br/><i>Owner Lane</i>"]` | Process — numbered operation with responsible module/lane |
| Repository Block | `["D#<br/>Store Name"]` | Data Store — persistent repository (Mermaid approximation of open-ended store) |
| Rectangle | `[...]` | Data Element / Error Output |
| Labeled Arrow | `-->` | Data Flow — movement of data between elements |

> Note: Mermaid does not fully support the split-tab and open-ended store glyphs from the thesis image, so this document uses a close visual approximation while preserving the same DFD semantics.

---

*Generated for iSchedWise V4 — Thesis Appendix C, Section 3.2*
