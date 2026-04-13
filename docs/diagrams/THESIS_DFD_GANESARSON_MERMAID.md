# iSchedWise V4 - Gane-Sarson DFD in Mermaid

This file provides Mermaid equivalents for your Gane-Sarson DFD notation and system-level diagrams.

## Gane-Sarson to Mermaid Legend

| Gane-Sarson Element | Mermaid Syntax | Visual Description |
|---|---|---|
| External Entity | `ID[Name]` | Square corner box |
| Process | `ID[[1.0 Name]]` | Rounded/subroutine box |
| Data Store | `ID[(Name)]` | Cylindrical/database shape |
| Data Flow | `-->|Data Label|` | Labeled directional arrow |

## Level 0 Context Diagram

```mermaid
flowchart LR
    EXT1[Super Admin]
    EXT2[Admin]
    EXT3[Dean]
    EXT4[Google Gemini API]
    EXT5[Email Server]

    P0[[0.0 iSchedWise V4 Integrated Scheduling System]]

    EXT1 -->|System configuration and governance requests| P0
    EXT2 -->|Scheduling, faculty, curriculum, and report requests| P0
    EXT3 -->|Department-scoped management and reporting requests| P0

    P0 -->|Conflict context for AI assistance| EXT4
    EXT4 -->|Scheduling recommendations and rationale| P0

    P0 -->|Password reset and OTP delivery requests| EXT5
    EXT5 -->|Delivery status and failure notifications| P0

    P0 -->|Dashboards, confirmations, and exports| EXT1
    P0 -->|Schedules, records, and reports| EXT2
    P0 -->|Scoped schedules and department reports| EXT3
```

## Level 1 Diagram (Split Views for Readability)

The full Level 1 model is split into focused views so each diagram stays readable while preserving the same thesis-aligned process IDs (1.0 to 12.0).

### Level 1A - Access, Identity, and Governance

```mermaid
flowchart LR
    EXT1[Super Admin]
    EXT2[Admin]
    EXT3[Dean]
    EXT5[Email Server]

    P1[[1.0 User Authentication and Access Control]]
    P8[[8.0 System Settings and Configuration]]
    P9[[9.0 User Management]]
    P10[[10.0 Archive Management]]
    P11[[11.0 Admin Tools]]
    P12[[12.0 Profile and Account Management]]

    D1[(D1 User and Auth)]
    D2[(D2 Session and Audit)]
    D3[(D3 Organization and Access Scope)]
    D8[(D8 Schedule Config)]
    D9[(D9 Class Schedules)]
    D10[(D10 Exam Schedules)]
    D12[(D12 Archives and System History)]

    EXT1 -->|Credentials and admin policy actions| P1
    EXT2 -->|Credentials| P1
    EXT3 -->|Credentials| P1
    P1 -->|Session and role access| EXT1
    P1 -->|Session and role access| EXT2
    P1 -->|Session and role access| EXT3
    P1 -->|OTP and reset messages| EXT5
    EXT5 -->|Delivery result| P1

    EXT1 -->|Configuration updates| P8
    EXT2 -->|Configuration updates| P8
    EXT3 -->|Configuration updates| P8
    EXT1 -->|User governance actions| P9
    EXT2 -->|User governance actions| P9
    EXT1 -->|Maintenance and backup actions| P11
    EXT1 -->|Archive and restore requests| P10
    EXT2 -->|Archive and restore requests| P10
    EXT3 -->|Archive and restore requests| P10
    EXT1 -->|Profile and security preferences| P12
    EXT2 -->|Profile and security preferences| P12
    EXT3 -->|Profile and security preferences| P12

    P1 -->|Read and update accounts| D1
    P1 -->|Write login and trusted device activity| D2
    P8 -->|Manage active term and limits| D8
    P8 -->|Read and update system settings| D12
    P9 -->|Manage users and roles| D1
    P9 -->|Manage dean program grants| D3
    P9 -->|Write user activity trail| D2
    P10 -->|Archive and restore records| D12
    P10 -->|Archive class schedule artifacts| D9
    P10 -->|Archive exam schedule artifacts| D10
    P11 -->|Write backup and maintenance logs| D12
    P11 -->|Write operational audit records| D2
    P12 -->|Update profile preferences| D1
    P12 -->|Write profile activity logs| D2
```

### Level 1B - Academic Master Data Management

```mermaid
flowchart LR
    EXT1[Super Admin]
    EXT2[Admin]
    EXT3[Dean]

    P3[[3.0 Faculty Management]]
    P4[[4.0 Building and Room Management]]
    P5[[5.0 Program and Section Management]]
    P6[[6.0 Curriculum and Subject Management]]

    D3[(D3 Organization and Access Scope)]
    D4[(D4 Curriculum and Subjects)]
    D5[(D5 Sections)]
    D6[(D6 Faculty)]
    D7[(D7 Facilities)]

    EXT1 -->|Faculty operations| P3
    EXT1 -->|Building and room operations| P4
    EXT1 -->|Program and section operations| P5
    EXT1 -->|Curriculum and subject operations| P6

    EXT2 -->|Faculty operations| P3
    EXT2 -->|Building and room operations| P4
    EXT2 -->|Program and section operations| P5
    EXT2 -->|Curriculum and subject operations| P6

    EXT3 -->|Department-scoped faculty actions| P3
    EXT3 -->|Department-scoped room actions| P4
    EXT3 -->|Department-scoped program actions| P5
    EXT3 -->|Department-scoped curriculum actions| P6

    P3 -->|Manage faculty and assignments| D6
    P3 -->|Resolve department and program ownership| D3

    P4 -->|Manage buildings and rooms| D7

    P5 -->|Manage programs| D3
    P5 -->|Manage sections| D5

    P6 -->|Manage curricula and subjects| D4
    P6 -->|Read program context and scope| D3
```

### Level 1C - Scheduling, AI Assistance, and Reporting

```mermaid
flowchart LR
    EXT1[Super Admin]
    EXT2[Admin]
    EXT3[Dean]
    EXT4[Google Gemini API]

    P2[[2.0 Schedule Management]]
    P7[[7.0 Report Generation]]

    P3[[3.0 Faculty Management]]
    P4[[4.0 Building and Room Management]]
    P5[[5.0 Program and Section Management]]
    P6[[6.0 Curriculum and Subject Management]]
    P8[[8.0 System Settings and Configuration]]
    P9[[9.0 User Management]]
    P10[[10.0 Archive Management]]

    D3[(D3 Organization and Access Scope)]
    D4[(D4 Curriculum and Subjects)]
    D5[(D5 Sections)]
    D6[(D6 Faculty)]
    D7[(D7 Facilities)]
    D8[(D8 Schedule Config)]
    D9[(D9 Class Schedules)]
    D10[(D10 Exam Schedules)]
    D11[(D11 Schedule Snapshots)]

    EXT1 -->|Class and exam operations| P2
    EXT1 -->|Reporting requests| P7
    EXT2 -->|Class and exam operations| P2
    EXT2 -->|Reporting requests| P7
    EXT3 -->|Department-scoped scheduling actions| P2
    EXT3 -->|Department-scoped reporting requests| P7

    P2 -->|Conflict context| EXT4
    EXT4 -->|AI scheduling suggestions| P2

    P8 -->|Active term and scheduling rules| P2
    P3 -->|Faculty availability and load| P2
    P4 -->|Room availability| P2
    P5 -->|Section structure| P2
    P6 -->|Subject catalog| P2
    P9 -->|Role and scope grants| P2
    P10 -->|Restore actions| P2

    P2 -->|Read and write class schedule entries| D9
    P2 -->|Read and write exam schedule entries| D10
    P2 -->|Create and restore snapshots| D11
    P2 -->|Read schedule constraints| D8
    P2 -->|Read section assignments| D5
    P2 -->|Read faculty assignments| D6
    P2 -->|Read room inventory| D7

    P7 -->|Read class schedule data| D9
    P7 -->|Read exam schedule data| D10
    P7 -->|Read faculty data| D6
    P7 -->|Read room utilization data| D7
    P7 -->|Read organization scope| D3
    P7 -->|Read curriculum context| D4
```

## Connector-to-Process Coverage Check

The table below documents parity between the thesis connector matrix in THESIS_FLOWCHARTS.md and this split Level 1 DFD.

| Connector | Thesis Module | DFD Process | Expected Role Access | Modeled Role Access | Status |
|---|---|---|---|---|---|
| C | Schedule Management | 2.0 Schedule Management | Super Admin, Admin, Dean | Super Admin, Admin, Dean | Aligned |
| D | Faculty Management | 3.0 Faculty Management | Super Admin, Admin, Dean | Super Admin, Admin, Dean | Aligned |
| E | Building and Room Management | 4.0 Building and Room Management | Super Admin, Admin, Dean | Super Admin, Admin, Dean | Aligned |
| F | Programs and Sections | 5.0 Program and Section Management | Super Admin, Admin, Dean | Super Admin, Admin, Dean | Aligned |
| G | Curriculum and Subjects | 6.0 Curriculum and Subject Management | Super Admin, Admin, Dean | Super Admin, Admin, Dean | Aligned |
| H | Reports Generation | 7.0 Report Generation | Super Admin, Admin, Dean | Super Admin, Admin, Dean | Aligned |
| I | System Settings | 8.0 System Settings and Configuration | Super Admin, Admin, Dean | Super Admin, Admin, Dean | Aligned |
| J | User Management | 9.0 User Management | Super Admin, Admin | Super Admin, Admin | Aligned |
| K | Archive Management | 10.0 Archive Management | Super Admin, Admin, Dean | Super Admin, Admin, Dean | Aligned |

Action-level restrictions still apply inside modules even when entry-level connector access is shared.

## Process-to-Route Traceability

| Process ID | Process Name | Primary Route Module |
|---|---|---|
| 1.0 | User Authentication and Access Control | `app/routes/auth.py` |
| 2.0 | Schedule Management | `app/routes/schedule.py`, `app/routes/exam_schedule.py` |
| 3.0 | Faculty Management | `app/routes/faculty.py` |
| 4.0 | Building and Room Management | `app/routes/building.py` |
| 5.0 | Program and Section Management | `app/routes/program.py` |
| 6.0 | Curriculum and Subject Management | `app/routes/curriculum.py` |
| 7.0 | Report Generation | `app/routes/reports.py` |
| 8.0 | System Settings and Configuration | `app/routes/settings.py` |
| 9.0 | User Management | `app/routes/user.py` |
| 10.0 | Archive Management | `app/routes/archive.py` |
| 11.0 | Admin Tools | `app/routes/admin_tools.py` |
| 12.0 | Profile and Account Management | `app/routes/profile.py` |
