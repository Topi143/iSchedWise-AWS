# Appendix B

## PROJECT COST ESTIMATION REPORT

## 1. Introduction

This section presents the estimated cost for the development and deployment of iSchedWise  , a web-based school scheduling and decision support system designed for administrators and deans. The estimate covers the resources required to build, host, access, and maintain the system in an academic environment.

The costing includes software tools, cloud server services, client workstations, and peripheral devices. The estimates are based on typical 2026 Philippine market prices and may vary depending on the supplier, institutional procurement process, and final deployment scale.

For this estimate, the proposed deployment assumes a pilot-to-small institutional implementation using cloud hosting, four dedicated client workstations for key academic users, and shared access for other authorized users through existing institutional devices and web browsers.

## 2. Software Cost Estimation

iSchedWise   was developed primarily using open-source software and community-supported tools. This greatly reduces the initial software licensing cost of the project.

| Software / Tool | Purpose | License Type | Estimated Cost (PHP) |
|---|---|---:|---:|
| Python | Core backend programming language | Open-source | 0 |
| Flask | Web application framework | Open-source | 0 |
| SQLAlchemy | ORM and database access | Open-source | 0 |
| MySQL Community Server / XAMPP | Database management and local development | Open-source | 0 |
| Tailwind CSS | Frontend styling and responsive UI | Open-source | 0 |
| Jinja2 | Server-side templating | Open-source | 0 |
| Flask-WTF / WTForms | Form handling and CSRF protection | Open-source | 0 |
| Flask-Login | Authentication and session management | Open-source | 0 |
| openpyxl | Excel export generation | Open-source | 0 |
| ReportLab | PDF report generation | Open-source | 0 |
| Visual Studio Code | Development environment | Free | 0 |
| Git / GitHub | Version control and repository hosting | Free tier | 0 |
| Google Gemini API | Optional AI-powered scheduling assistance | Optional / usage-based | 0* |

**Total Software Cost: PHP 0**

*The Google Gemini integration is optional and can operate under a free or low-usage tier during development and pilot deployment. If the institution enables heavy AI usage in production, a separate operating budget may be allocated later.*

## 3. Hardware Cost Estimation

Since iSchedWise   is a web-based system, most of the project cost is allocated to infrastructure and user access devices rather than software licensing. The estimated hardware and infrastructure-related costs are summarized below.

| Category | Estimated Cost (PHP) |
|---|---:|
| Server / Cloud Infrastructure | 34,000 |
| Client / User Hardware | 128,000 |
| Peripheral Devices | 27,500 |

**Total Hardware and Infrastructure Cost: PHP 189,500**

## 4. Server Cost Estimation (Web-Based System)

For a web-based deployment, iSchedWise may be hosted using cloud infrastructure such as Amazon Web Services (AWS). This setup supports remote access, centralized database management, and easier maintenance.

The following table presents an estimated one-year deployment cost for a small-to-medium academic implementation.

| Server Component | Description | Estimated Annual Cost (PHP) |
|---|---|---:|
| AWS EC2 Instance | Application hosting for the Flask web server | 12,000 |
| AWS RDS MySQL Instance | Managed relational database service | 16,000 |
| Storage, Snapshots, and Backups | Database backup retention and server storage | 4,000 |
| Domain / DNS / SSL Allowance | Domain registration and deployment-related network services | 2,000 |

**Total Server Cost: PHP 34,000**

This estimate assumes a modest production environment suitable for institutional use. If the number of users, departments, or concurrent requests increases significantly, the cloud subscription cost may also increase.

## 5. Client/User Hardware Cost Estimation

Client devices are needed by system users such as the administrator, dean, and scheduling staff. Because the system is browser-based, these machines do not require specialized software beyond a modern web browser and internet connectivity.

The following estimate assumes four dedicated desktop workstations: one unit for the administrator and three units for the deans. Other authorized users may access the system using existing school-owned computers, which are not charged separately in this estimate.

| Client Hardware | Quantity | Unit Cost (PHP) | Subtotal (PHP) |
|---|---:|---:|---:|
| Desktop Computer Set (Intel Core i5 / Ryzen 5, 8-16GB RAM, SSD, monitor, keyboard, mouse) | 4 | 32,000 | 128,000 |

**Total Client/User Hardware Cost: PHP 128,000**

These workstations may be assigned to one administrator and three dean offices responsible for schedule preparation, monitoring, review, and approval.

## 6. Peripheral Devices (If Applicable)

Peripheral devices support report printing, power protection, and offline backup of critical files and database exports.

| Peripheral Device | Quantity | Unit Cost (PHP) | Subtotal (PHP) |
|---|---:|---:|---:|
| UPS (Uninterruptible Power Supply) | 4 | 3,500 | 14,000 |
| Network Printer | 1 | 9,000 | 9,000 |
| External Backup Drive | 1 | 4,500 | 4,500 |

**Total Peripheral Devices Cost: PHP 27,500**

These peripherals are recommended to improve operational reliability, provide power protection for the four dedicated workstations, support printed scheduling reports, and provide backup storage for exported system data.

## 7. Summary of Project Cost

The overall project cost for iSchedWise   is summarized below.

| Cost Category | Amount (PHP) |
|---|---:|
| Software Cost | 0 |
| Server / Cloud Infrastructure Cost | 34,000 |
| Client / User Hardware Cost | 128,000 |
| Peripheral Devices Cost | 27,500 |

**Estimated Total Project Cost: PHP 189,500**

## 8. Conclusion

The estimated total project cost for the development and deployment of iSchedWise   is approximately **PHP 189,500**. The largest share of the budget is allocated to client hardware and cloud infrastructure, particularly the dedicated workstations for one administrator and three deans, together with the annual hosting resources required for online deployment.

The use of open-source technologies such as Python, Flask, MySQL Community Server, Tailwind CSS, SQLAlchemy, and related libraries significantly reduces software licensing expenses. As a result, the project remains financially feasible for academic institutions while still providing a modern, scalable, and maintainable web-based scheduling system.

If the institution already owns suitable computers, printers, and backup devices, the actual additional deployment cost may be lower than the estimate presented in this appendix. In that case, the primary recurring cost would mainly come from cloud hosting and server maintenance.