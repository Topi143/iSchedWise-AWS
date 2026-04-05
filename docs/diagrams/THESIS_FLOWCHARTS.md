# iSchedWise V4 — System Flowcharts

> **Thesis Appendix C — Section 3.1: Flow Chart**
>
> Each flowchart represents one part of the system. Connector labels **(A1)**, **(A2)**, **(B)**, and **(C)** through **(K)** link flowcharts together — a connector output in one chart is the entry point of another.

---

## Table of Contents

| # | Flowchart | Connector |
|---|-----------|-----------|
| 1 | [Main Login Flow](#1-main-login-flow) | → **(A1)** Super Admin, **(A2)** Admin, **(B)** Dean |
| 2 | [Super Admin Dashboard](#2-super-admin-dashboard-connector-a1) | **(A1)** → **(C–K)** |
| 3 | [Admin Dashboard](#3-admin-dashboard-connector-a2) | **(A2)** → **(C–K)** |
| 4 | [Dean Dashboard](#4-dean-dashboard-connector-b) | **(B)** → **(C, D, E, F, G, H, I, K)** |
| 5 | [Schedule Management](#5-schedule-management-connector-c) | **(C)** |
| 6 | [Faculty Management](#6-faculty-management-connector-d) | **(D)** |
| 7 | [Building & Room Management](#7-building--room-management-connector-e) | **(E)** |
| 8 | [Programs & Sections Management](#8-programs--sections-management-connector-f) | **(F)** |
| 9 | [Curriculum & Subject Management](#9-curriculum--subject-management-connector-g) | **(G)** |
| 10 | [Reports Generation](#10-reports-generation-connector-h) | **(H)** |
| 11 | [System Settings](#11-system-settings-connector-i) | **(I)** |
| 12 | [User Management](#12-user-management-connector-j) | **(J)** |
| 13 | [Archive Management](#13-archive-management-connector-k) | **(K)** |
| 14 | [Password Reset](#14-password-reset-flow) | *(standalone)* |

---

## Connector Map

```
                        ┌─────────┐
                        │  LOGIN  │
                        └────┬────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
            (A1)           (A2)           (B)
         Super Admin      Admin          Dean
                            │              │              │
        (C,D,E,F,G,H,I,J,K) (C,D,E,F,G,H,I,J,K) (C,D,E,F,G,H,I,K)
```

| Connector | Module | Super Admin | Admin | Dean |
|-----------|--------|:-----------:|:-----:|:----:|
| **(A1)** | Super Admin Dashboard | ✅ | — | — |
| **(A2)** | Admin Dashboard | — | ✅ | — |
| **(B)** | Dean Dashboard | — | — | ✅ |
| **(C)** | Schedule Management | ✅ | ✅ | ✅ |
| **(D)** | Faculty Management | ✅ | ✅ | ✅ |
| **(E)** | Building & Room Management | ✅ | ✅ | ✅ |
| **(F)** | Programs & Sections | ✅ | ✅ | ✅ |
| **(G)** | Curriculum & Subjects | ✅ | ✅ | ✅ |
| **(H)** | Reports Generation | ✅ | ✅ | ✅ |
| **(I)** | System Settings | ✅ | ✅ | ✅ |
| **(J)** | User Management | ✅ | ✅ | — |
| **(K)** | Archive Management | ✅ | ✅ | ✅ |

> Access table is entry-level access. Some modules include action-level restrictions (for example dean restrictions in selected Settings, Curriculum, Reports, and Archive actions). Super-admin system administration actions are now handled inside **Settings (I)**.

---

## 1. Main Login Flow

```mermaid
flowchart TD
    START([START]) --> A[Access iSchedWise\nLogin Page]
    A --> B[Enter Email/Username\n& Password]
    B --> C{Credentials\nValid?}
    C -->|NO| C1[Display Error:\nInvalid Credentials] --> B
    C -->|YES| D{Temporary Account\nExpired?}
    D -->|YES| D1[Auto-Disable Account\nDisplay Expiry Error] --> B
    D -->|NO| E{Account\nActive?}
    E -->|NO| E1[Display Error:\nAccount Deactivated] --> B
    E -->|YES| F{2FA\nEnabled?}

    F -->|NO| G[Finalize Login:\nCreate Session & Log History]
    F -->|YES| H{Trusted Device\nToken Valid?}

    H -->|YES| H1[Bypass OTP\nContinue Login] --> G
    H -->|NO| I1[Generate OTP\nStore Pending 2FA Session]
    I1 --> I2[Send Verification Code\nvia Email]
    I2 --> I3[Open Verify-2FA Page\nEnter Code or Resend]
    I3 --> I4{Code Valid\nBefore Max Attempts?}
    I4 -->|NO| I5{Attempts\nRemaining?}
    I5 -->|YES| I6[Show Error\nReturn to Verify-2FA] --> I3
    I5 -->|NO| I7[Clear Pending 2FA\nReturn to Login] --> B
    I4 -->|YES| I8[Issue Trusted Device\nCookie & Record Audit] --> G

    G --> J1{Needs First-Login\nSetup?}
    J1 -->|YES| J2[Redirect to Setup:\nSet Valid Email\nProfile + New Password]
    J2 --> J3{Password Change\nStill Required?}
    J1 -->|NO| J3

    J3 -->|YES| J4[Redirect to Account\nSecurity/Profile] --> END4([END])
    J3 -->|NO| K{Check\nUser Role}

    K -->|Super Admin| I((A1))
    K -->|Admin| J((A2))
    K -->|Dean| L((B))
    I --> END1([END])
    J --> END2([END])
    L --> END3([END])

    style START fill:#f9f,stroke:#333,stroke-width:2px
    style END1 fill:#f9f,stroke:#333,stroke-width:2px
    style END2 fill:#f9f,stroke:#333,stroke-width:2px
    style END3 fill:#f9f,stroke:#333,stroke-width:2px
    style END4 fill:#f9f,stroke:#333,stroke-width:2px
    style I fill:#90EE90,stroke:#333,stroke-width:2px
    style J fill:#90EE90,stroke:#333,stroke-width:2px
    style L fill:#90EE90,stroke:#333,stroke-width:2px
```

---

## 2. Super Admin Dashboard (Connector A1)

> **Super Admin implementation flow**: `/dashboard` immediately redirects to the dedicated superadmin command dashboard.

```mermaid
flowchart TD
    A1((A1)) --> SA0[Open Dashboard Route]
    SA0 --> SA1[Role Check: super_admin]
    SA1 --> SA2[Redirect to Superadmin Command Dashboard]
    SA2 --> SA3[Load KPIs, Recent Activity,\nBackup Snapshot, Login Trend]
    SA3 --> SA4{Choose Entry Point}

    SA4 -->|Sidebar Modules| SA5{Navigate To}
    SA5 -->|Schedules| C((C))
    SA5 -->|Faculty| D((D))
    SA5 -->|Buildings| E((E))
    SA5 -->|Programs| F((F))
    SA5 -->|Curriculum| G((G))
    SA5 -->|Reports| H((H))
    SA5 -->|Settings| I((I))
    SA5 -->|Users| J((J))
    SA5 -->|Archives| K((K))

    SA4 -->|Quick Action: System Settings| I
    SA4 -->|Quick Action: Activity Report| H
    SA4 -->|Quick Action: User Management| J
    SA4 -->|Quick Action: Open System and Database Settings| I

    SA4 -->|Logout| SA6[End Session and Return to Login] --> SAEND([END])

    style A1 fill:#90EE90,stroke:#333,stroke-width:2px
    style C fill:#87CEEB,stroke:#333,stroke-width:2px
    style D fill:#87CEEB,stroke:#333,stroke-width:2px
    style E fill:#87CEEB,stroke:#333,stroke-width:2px
    style F fill:#87CEEB,stroke:#333,stroke-width:2px
    style G fill:#87CEEB,stroke:#333,stroke-width:2px
    style H fill:#87CEEB,stroke:#333,stroke-width:2px
    style I fill:#87CEEB,stroke:#333,stroke-width:2px
    style J fill:#87CEEB,stroke:#333,stroke-width:2px
    style K fill:#87CEEB,stroke:#333,stroke-width:2px
    style SAEND fill:#f9f,stroke:#333,stroke-width:2px
```

---

## 3. Admin Dashboard (Connector A2)

```mermaid
flowchart TD
    A2((A2)) --> AD0[Open Admin Dashboard]
    AD0 --> AD1[Load Active Academic Settings]
    AD1 --> AD2[Resolve Scope: All Programs\nor Selected Program]
    AD2 --> AD3[Build Dashboard Cards, Trends,\nSmart Actions, Upcoming Exams]
    AD3 --> AD4{Use Smart Action?}
    AD4 -->|New Schedule| C((C))
    AD4 -->|View Reports| H((H))
    AD4 -->|Skip| AD5{Select Module}

    AD5 -->|Schedules| C
    AD5 -->|Faculty| D((D))
    AD5 -->|Buildings| E((E))
    AD5 -->|Programs| F((F))
    AD5 -->|Curriculum| G((G))
    AD5 -->|Reports| H
    AD5 -->|Settings| I((I))
    AD5 -->|Users| J((J))
    AD5 -->|Archives| K((K))
    AD5 -->|Logout| AD6[End Session and Return to Login] --> ADEND([END])

    style A2 fill:#90EE90,stroke:#333,stroke-width:2px
    style C fill:#87CEEB,stroke:#333,stroke-width:2px
    style D fill:#87CEEB,stroke:#333,stroke-width:2px
    style E fill:#87CEEB,stroke:#333,stroke-width:2px
    style F fill:#87CEEB,stroke:#333,stroke-width:2px
    style G fill:#87CEEB,stroke:#333,stroke-width:2px
    style H fill:#87CEEB,stroke:#333,stroke-width:2px
    style I fill:#87CEEB,stroke:#333,stroke-width:2px
    style J fill:#87CEEB,stroke:#333,stroke-width:2px
    style K fill:#87CEEB,stroke:#333,stroke-width:2px
    style ADEND fill:#f9f,stroke:#333,stroke-width:2px
```

---

## 4. Dean Dashboard (Connector B)

```mermaid
flowchart TD
    B((B)) --> DE0[Open Dean Dashboard]
    DE0 --> DE1[Resolve Assigned Program IDs]
    DE1 --> DE2{Requested Program Allowed?}
    DE2 -->|No| DE3[Reset Filter to Allowed Scope]
    DE2 -->|Yes| DE4[Use Selected Program]
    DE3 --> DE5[Build Scoped Metrics,\nActivities, and Trends]
    DE4 --> DE5

    DE5 --> DE6{Select Module}
    DE6 -->|Schedules| C((C))
    DE6 -->|Faculty| D((D))
    DE6 -->|Buildings| E((E))
    DE6 -->|Programs| F((F))
    DE6 -->|Curriculum| G((G))
    DE6 -->|Reports| H((H))
    DE6 -->|Settings| I((I))
    DE6 -->|Archives| K((K))
    DE6 -->|Logout| DE7[End Session and Return to Login] --> DEEND([END])

    style B fill:#90EE90,stroke:#333,stroke-width:2px
    style C fill:#87CEEB,stroke:#333,stroke-width:2px
    style D fill:#87CEEB,stroke:#333,stroke-width:2px
    style E fill:#87CEEB,stroke:#333,stroke-width:2px
    style F fill:#87CEEB,stroke:#333,stroke-width:2px
    style G fill:#87CEEB,stroke:#333,stroke-width:2px
    style H fill:#87CEEB,stroke:#333,stroke-width:2px
    style I fill:#87CEEB,stroke:#333,stroke-width:2px
    style K fill:#87CEEB,stroke:#333,stroke-width:2px
    style DEEND fill:#f9f,stroke:#333,stroke-width:2px
```

---

## 5. Schedule Management (Connector C)

```mermaid
flowchart TD
    C((C)) --> SC0[Open Schedule Workspace]
    SC0 --> SC1{Select Action}

    SC1 -->|View Timetables| VW1[Open Class, Faculty, Room,\nor Exam Timetable]
    SC1 -->|Create or Edit| ED1[Open Unified Create/Edit Form]
    SC1 -->|Delete| DL1[Single or Batch Delete]
    SC1 -->|AI and Batch Tools| AU1[Run AI Conflict Tools\nor Batch Builder]
    SC1 -->|Snapshots and Clear| BK1[Create or Restore Snapshot,\nor Clear Schedules\nwith Auto Backup]
    SC1 -->|Export| XP1[Generate Class/Faculty/Room/Exam\nExcel, PDF, or Posting File]
    SC1 -->|Cleanup Archived| CLN[Admin-Only Cleanup Endpoint]

    ED1 --> ED2{Class or Exam?}
    ED2 -->|Class| CL1[Validate + Conflict Check\nSection/Faculty/Room]
    ED2 -->|Exam| EX1[Validate + Conflict Check\nSection/Faculty/Room/Proctor]
    CL1 -->|Conflict| ER1[Return Conflict Error]
    EX1 -->|Conflict| ER1
    CL1 -->|No Conflict| SV1[Save or Reactivate\nClass Schedule]
    EX1 -->|No Conflict| SV2[Save or Reactivate\nExam Schedule]

    DL1 --> DL2[Apply Lock and Scope Checks:\nClass Delete = Soft,\nExam Delete = Hard]

    XP1 --> XP2[Download Export File]
    ER1 --> ED1

    VW1 --> SC9[Refresh Schedule Views]
    SV1 --> SC9
    SV2 --> SC9
    DL2 --> SC9
    AU1 --> SC9
    BK1 --> SC9
    XP2 --> SC9
    CLN --> SC9

    style C fill:#87CEEB,stroke:#333,stroke-width:2px
```

---

## 6. Faculty Management (Connector D)

```mermaid
flowchart TD
    D((D)) --> FC0[Open Faculty Module]
    FC0 --> FC1[Load Active Term, Faculty List,\nAssignments, and Workloads]
    FC1 --> FC2{Select Action Group}

    FC2 -->|Faculty Profile| P0{Add or Edit}
    FC2 -->|Subject Assignments| S0{Assign or Unassign}
    FC2 -->|Availability| A0[Manage Weekly Availability\nWithin Schedule Hours]
    FC2 -->|Archive or Delete| D0{Archive or Permanent Delete}
    FC2 -->|Export| X0[Generate Faculty Lineup Export\nwith Program Scope Check]

    P0 --> V1[Validate Faculty Data]
    S0 --> V2[Validate Assignment Update]
    A0 --> V3[Validate Availability Slots]

    D0 --> G1{Permanent Delete Requires\nArchived Faculty?}
    G1 -->|No| ER1[Show Guardrail Error]
    G1 -->|Yes or Archive Action| SV1[Apply Archive/Delete\nwith Related Schedule Handling]

    V1 --> SV2[Save Faculty Profile]
    V2 --> SV3[Apply Assignment Change]
    V3 --> SV4[Save Availability]
    X0 --> X1[Download Export File]

    SV1 --> OK1[Refresh Faculty View]
    SV2 --> OK1
    SV3 --> OK1
    SV4 --> OK1
    X1 --> OK1
    ER1 --> OK1

    style D fill:#87CEEB,stroke:#333,stroke-width:2px
```

---

## 7. Building & Room Management (Connector E)

```mermaid
flowchart TD
    E((E)) --> BL0[Open Building Module]
    BL0 --> BL1[Load Active Buildings\nand Selected Building Rooms]
    BL1 --> BL2{Select Action Group}

    BL2 -->|Building| B0{Add/Edit, Archive, or Delete}
    BL2 -->|Room| R0{Add/Edit, Delete,\nor Bulk Delete}

    B0 --> V1[Validate Building Operation]
    R0 --> V2[Validate Room Operation]

    V1 --> G1{Permanent Delete Requires\nArchived Building?}
    G1 -->|No| ER1[Show Guardrail Error]
    G1 -->|Yes or Non-Delete| SV1[Apply Building Change\nand Related Schedule Handling]

    V2 --> SV2[Apply Room Change\nand Related Schedule Handling]

    SV1 --> OK1[Refresh Building and Room View]
    SV2 --> OK1
    ER1 --> OK1

    style E fill:#87CEEB,stroke:#333,stroke-width:2px
```

---

## 8. Programs & Sections Management (Connector F)

```mermaid
flowchart TD
    F((F)) --> PR0[Open Programs Module]
    PR0 --> PR1[Load Role-Scoped Program List\nand Selected Program Sections]
    PR1 --> PR2{Select Action}

    PR2 -->|Program Add or Edit| PG1[Validate Program Fields\nand Save]
    PR2 -->|Program Status| PG2[Activate or Deactivate Program]
    PR2 -->|Program Archive| PG3[Archive Program and Related\nSchedules/Curricula]
    PR2 -->|Program Delete| PG4{Archived and No Curricula?}
    PG4 -->|No| ER1[Reject Permanent Delete]
    PG4 -->|Yes| PG5[Hard Delete Program]

    PR2 -->|Section Management| SC0{Add, Edit, or Delete?}
    SC0 -->|Add Bulk| SC1[Create Year-Level + Section\nCombinations]
    SC0 -->|Edit| SC2[Validate and Update Section]
    SC0 -->|Delete Single or Bulk| SC3[Delete Sections and Related\nClass/Exam Schedules]

    PG1 --> OK1[Refresh Program and Section View]
    PG2 --> OK1
    PG3 --> OK1
    ER1 --> OK1
    PG5 --> OK1
    SC1 --> OK1
    SC2 --> OK1
    SC3 --> OK1

    style F fill:#87CEEB,stroke:#333,stroke-width:2px
```

---

## 9. Curriculum & Subject Management (Connector G)

```mermaid
flowchart TD
    G((G)) --> C0[Open Curriculum Module]
    C0 --> C1[Load Curricula by Program Access]
    C1 --> C2{Select Action Group}

    C2 -->|Curriculum| CU0{Add, Edit, Archive, or Delete}
    C2 -->|Year Level / Semester| YL0{Add/Edit or Delete Structure}
    C2 -->|Subject| SU0{Add/Edit, Delete,\nor Bulk Import/Delete}

    CU0 --> P1{Add Action by Admin/Super Admin?}
    P1 -->|No Permission| ER1[Show Permission Error]
    P1 -->|Allowed| V1[Validate Curriculum Payload]
    CU0 -->|Non-Add Action| V1

    YL0 --> V2[Validate Structure Update]
    SU0 --> V3[Validate Subject Operation\nand Import File if Provided]

    V1 --> CH1{Valid?}
    V2 --> CH1
    V3 --> CH1
    CH1 -->|NO| ER2[Show Validation Error]
    CH1 -->|YES| SV1[Save Changes]

    SV1 --> LG1[Log Activity and Refresh Module View]
    ER1 --> C1
    ER2 --> C1
    LG1 --> C1

    style G fill:#87CEEB,stroke:#333,stroke-width:2px
```

---

## 10. Reports Generation (Connector H)

```mermaid
flowchart TD
    H((H)) --> RP0[Open Reports Module]
    RP0 --> RP1{Select Report Area}

    RP1 -->|Analytics Pages| AN0[Overview, Faculty Workload,\nRoom Utilization, Weekly Distribution,\nSemester Comparison]
    RP1 -->|Activity Logs| AC0[Admin/Super Admin Activity Logs]

    AN0 --> F1[Apply Program Scope Filter]
    F1 --> D1[Load Charts and Tables]
    D1 --> O1{Optional Action}
    O1 -->|AI Summary| O2[Generate AI Summary]
    O1 -->|Export| O3[Download Excel, PDF,\nor Faculty Daily Export]
    O1 -->|Stay on Page| O4[Refresh Report View]

    AC0 --> P1{Admin or Super Admin?}
    P1 -->|No| ER1[Show Permission Error]
    P1 -->|Yes| A1[Apply Activity Filters\nand Load Activity Data]
    A1 --> A2{List, Stats, or Export?}
    A2 -->|List or Stats| O4
    A2 -->|Export| O5[Download Activity Export]

    O2 --> O4
    O3 --> O4
    O5 --> O4
    ER1 --> RP1

    style H fill:#87CEEB,stroke:#333,stroke-width:2px
```

---

## 11. System Settings (Connector I)

> **All Authenticated Users Can Open Settings**
>
> **Admin/Super Admin:** full academic, institution, and department management actions
>
> **Super Admin:** additional system tab actions (maintenance mode, global branding, database tools, and security controls)
>
> **Dean:** department edit only (for assigned departments) plus personal preference updates

```mermaid
flowchart TD
    I((I)) --> S0[Open Settings Module]
    S0 --> S1[Load Tabs by Role]
    S1 --> S2{Select Action}

    S2 -->|Academic or Institution| A0[Update Academic or Institution Configuration]
    S2 -->|Departments| D0[Add, Edit, or Delete Department]
    S2 -->|User Preferences| U0[Update Text Size or Dark Mode]
    S2 -->|System Tools| T0[Run Maintenance, Branding,\nDatabase, or Security Action]

    A0 --> P1{Admin or Super Admin?}
    P1 -->|No| ER1[Show Permission Error]
    P1 -->|Yes| A1[Validate and Save Academic Changes]
    A1 --> A2{Term or Exam Period Changed?}
    A2 -->|Yes| A3[Archive Current Data and\nRestore Matching Archived Data]
    A2 -->|No| OK1[Show Success]

    D0 --> P2{Admin/Super Admin\nor Dean with Assigned Department?}
    P2 -->|No| ER1
    P2 -->|Yes| D1[Validate and Save Department]

    U0 --> U1{Payload Valid?}
    U1 -->|No| ER2[Show Validation Error]
    U1 -->|Yes| U2[Save Preference]

    T0 --> P3{Super Admin?}
    P3 -->|No| ER1
    P3 -->|Yes| T1[Execute Selected System Tool]

    A3 --> OK1
    D1 --> OK1
    U2 --> OK1
    T1 --> OK1
    ER1 --> S1
    ER2 --> S1
    OK1 --> S1

    style I fill:#87CEEB,stroke:#333,stroke-width:2px
```

---

## 12. User Management (Connector J)

> **Admin & Super Admin** (selected actions are super-admin only)

```mermaid
flowchart TD
    J((J)) --> U0[Open Users Module]
    U0 --> U1[Run Expired Temporary Account Check]
    U1 --> U2{Select User Action}

    U2 -->|Create or Quick Generate| C0[Build New User Payload]
    U2 -->|Edit| E0[Build Profile or Role Update]
    U2 -->|Reset Password| R0[Build Temporary Password Reset]
    U2 -->|Toggle, Archive, or Bulk| M0[Build Lifecycle Request]
    U2 -->|Permanent Delete| D0[Build Delete Request]
    U2 -->|Export| X0[Build Export Request]

    C0 --> P1{Requires Super Admin Permission}
    P1 -->|No| ER1[Show Permission Error]
    P1 -->|Yes| SV1[Create User and Apply Scope]

    E0 --> P2{Breaks Guardrails}
    R0 --> P2
    M0 --> P2
    P2 -->|Yes| ER2[Show Guardrail Error]
    P2 -->|No| SV2[Apply Update]

    D0 --> P3{Super Admin and Archived Target}
    P3 -->|No| ER1
    P3 -->|Yes| SV3[Delete User]

    X0 --> X1[Download Export File]

    SV1 --> OK1[Save, Log Activity, Refresh User List]
    SV2 --> OK1
    SV3 --> OK1
    X1 --> OK1
    ER1 --> U1
    ER2 --> U1
    OK1 --> U1

    style J fill:#87CEEB,stroke:#333,stroke-width:2px
```

---

## 13. Archive Management (Connector K)

```mermaid
flowchart TD
    K((K)) --> AR0[Open Archive Module]
    AR0 --> AR1{Select Archive Area}

    AR1 -->|Schedules| SC0[Load Schedule Archives\nwith Role-Scoped Filters]
    AR1 -->|Curriculum, Programs, Faculty, Buildings| EN0[Load Archived Entities]

    SC0 --> SC1{Select Schedule Action}
    SC1 -->|View or Archive| SC2[View Detail or Archive\nSingle/Bulk Schedules]
    SC1 -->|Restore/Delete/Bulk Manage| PM1{Admin or Super Admin?}
    SC1 -->|Export| EX1[Export Schedule Data]

    EN0 --> EN1{Select Entity Action}
    EN1 -->|Restore/Delete/Bulk Manage| PM1
    EN1 -->|Export| EX2[Export Entity Data]

    PM1 -->|No| ER1[Show Permission Error]
    PM1 -->|Yes| SV1[Execute Action and Log Activity]

    SC2 --> OK1[Refresh Archive Views]
    SV1 --> OK1
    ER1 --> OK1
    EX1 --> EX3[Download Export File]
    EX2 --> EX3
    EX3 --> OK1

    style K fill:#87CEEB,stroke:#333,stroke-width:2px
```

---

## 14. Password Reset Flow

> *(Standalone — accessible from Login page without authentication)*

```mermaid
flowchart TD
    START([START]) --> FP0[Open Forgot Password Page]
    FP0 --> FP1{Already Authenticated}
    FP1 -->|Yes| RD0[Redirect to Dashboard]
    FP1 -->|No| FP2[Enter Account Email]
    FP2 --> FP3{Email Exists}

    FP3 -->|No| ER1[Show Account Not Found Error]
    ER1 --> FP2
    FP3 -->|Yes| TK1[Generate Reset Token]
    TK1 --> EM1[Send Password Reset Email]
    EM1 --> EM2{Email Sent Successfully}
    EM2 -->|No| ER2[Show Email Delivery Error]
    ER2 --> FP2
    EM2 -->|Yes| LG1[Redirect to Login]

    LG1 --> LK1[User Opens Reset Link]
    LK1 --> RS0[Open Reset Password Page]
    RS0 --> RS1{Already Authenticated}
    RS1 -->|Yes| RD0
    RS1 -->|No| RS2{Token Valid and Not Expired}

    RS2 -->|No| ER3[Show Invalid or Expired Link]
    ER3 --> FP0
    RS2 -->|Yes| RF1[Show Reset Password Form]

    RF1 --> RF2[Enter and Confirm New Password]
    RF2 --> RF3{Password Form Valid}
    RF3 -->|No| RF1
    RF3 -->|Yes| SV1[Set New Password]
    SV1 --> SV2[Clear Password Change Required Flag]
    SV2 --> LG2[Redirect to Login with Success Message]
    LG2 --> END3([END])

    style START fill:#f9f,stroke:#333,stroke-width:2px
    style END3 fill:#f9f,stroke:#333,stroke-width:2px
```

---

## Color Legend

| Shape / Color | Meaning |
|---------------|---------|
| 🟢 Green circle `(( ))` | Connector — links to another flowchart |
| 🔵 Blue circle `(( ))` | Connector — destination module |
| 🟪 Pink rounded `([ ])` | START / END terminal |
| ⬜ Rectangle `[ ]` | Process step |
| 🔷 Diamond `{ }` | Decision point |

---

*Generated for iSchedWise V4 — Thesis Appendix C, Section 3.1*
