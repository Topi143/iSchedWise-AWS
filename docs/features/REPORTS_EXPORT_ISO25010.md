# Reports Export with ISO 25010 Compliance

## Overview

The Reports module now includes comprehensive export functionality that generates Excel and PDF reports with ISO 25010-compliant formatting. This ensures high-quality, professional, and accessible report outputs.

## Features

### 1. Excel Export (`.xlsx`)
- **Multiple Worksheets**: Summary, Faculty Workload, Room Utilization, Weekly Distribution
- **Professional Formatting**: Clear headers, alternating row colors, proper borders
- **Embedded Charts**: Bar charts and pie charts for visual data representation
- **Responsive Column Widths**: Optimized for readability
- **Metadata Headers**: Institution name, academic period, department, generation timestamp

### 2. PDF Export (`.pdf`)
- **Landscape Layout**: Optimized for tabular data
- **Structured Content**: Overview statistics, faculty workload, room utilization, weekly distribution
- **Professional Typography**: Consistent fonts, colors, and spacing
- **Page Headers**: Institution branding and report context
- **ISO 25010 Compliance Footer**: Indicates adherence to software quality standards

## ISO 25010 Compliance

The export functionality adheres to ISO/IEC 25010:2011 Software Quality Standards:

### 1. **Usability**
- Clear visual hierarchy with distinct headers, subheaders, and data sections
- Consistent color scheme (blue headers, alternating row backgrounds)
- Readable font sizes and styles (Arial, Helvetica)
- Intuitive layout with logical information flow

### 2. **Accessibility**
- High contrast ratios for text readability
- Clear table structures with borders
- Descriptive headers and labels
- Proper spacing and padding for visual clarity

### 3. **Maintainability**
- Modular code structure with separate functions for each sheet/section
- Reusable helper functions
- Clear comments and documentation
- Consistent naming conventions

### 4. **Performance Efficiency**
- Efficient data processing using SQLAlchemy queries
- BytesIO for in-memory file generation (no disk I/O)
- Optimized chart rendering (limited to top 15 items)
- Minimal memory footprint

### 5. **Reliability**
- Comprehensive error handling with try-except blocks
- Graceful degradation (continues without logos if files not found)
- Validation of data before rendering
- Clear error messages for debugging

## Usage

### From the Reports Page

1. **Navigate to Reports & Analytics**
   - Click "Reports & Analytics" in the sidebar

2. **Apply Filters (Optional)**
   - Select department filter if needed
   - Statistics will update automatically

3. **Export Reports**
   - Click the "Export Report" dropdown button
   - Choose "Export to Excel" or "Export to PDF"
   - File will download automatically

### Filter Behavior

- **All Departments**: Exports data for all accessible departments
- **Specific Department**: Exports data filtered to selected department only
- **Dean Users**: Only see data for their assigned departments
- **Admin Users**: Can export data for all departments

## File Naming Convention

Exported files follow this pattern:
```
Reports_{AcademicYear}_{Semester}_{DepartmentCode}_{Timestamp}.{extension}

Examples:
- Reports_2025-2026_1st Semester_CS_20250125_143052.xlsx
- Reports_2025-2026_1st Semester_20250125_143052.pdf
```

## Export Contents

### Summary Sheet/Section
- Academic information header
- Overview statistics grid:
  - Class Schedules, Exam Schedules
  - Active Faculty, Active Sections
  - Total Rooms, Rooms in Use
  - Faculty with Schedules
  - Lecture Classes, Lab Classes

### Faculty Workload Sheet/Section
- Table with columns:
  - #, Faculty Name, Department
  - Schedules Count
  - Lecture Units, Lab Units, Total Units
- Bar chart showing top 15 faculty by total units

### Room Utilization Sheet/Section
- Table with columns:
  - #, Room, Building
  - Classes Count, Exams Count
  - Total Usage, Status
- Bar chart showing top 15 rooms by usage

### Weekly Distribution Sheet/Section
- Table with columns:
  - Day of Week, Schedule Count
- Bar chart showing distribution across days

## Technical Implementation

### Routes
- `GET /reports/export/excel` - Generate Excel file
- `GET /reports/export/pdf` - Generate PDF file

### Dependencies
- **openpyxl** 3.1.5 - Excel file generation
- **reportlab** 4.4.4 - PDF generation
- **pillow** 12.0.0 - Image processing

### Key Functions

#### Excel Export
- `export_excel()` - Main export route handler
- `create_summary_sheet()` - Summary worksheet
- `create_faculty_workload_sheet()` - Faculty data and chart
- `create_room_utilization_sheet()` - Room data and chart
- `create_weekly_distribution_sheet()` - Weekly data and chart

#### PDF Export
- `export_pdf()` - Main PDF generation route
- Uses ReportLab's `SimpleDocTemplate` and `Table` classes
- Custom paragraph styles for headers and content
- Landscape orientation for better table display

## Best Practices

### For Administrators
1. Export reports regularly for record-keeping
2. Use department filters for targeted reports
3. Share PDF versions for presentations
4. Keep Excel versions for further analysis

### For Deans
1. Export department-specific reports
2. Use faculty workload data for assignment planning
3. Monitor room utilization for resource optimization
4. Track weekly distribution for balanced scheduling

## ISO 25010 Quality Attributes

### Document Structure
- **Header**: Institution info, academic period, filters, timestamp
- **Body**: Organized sections with clear headings
- **Footer**: ISO 25010 compliance statement

### Visual Design
- **Colors**: Professional blue (#1F4788) for headers
- **Typography**: Clear hierarchy with varied font sizes
- **Spacing**: Adequate padding and margins
- **Borders**: Subtle but clear table boundaries

### Data Presentation
- **Tables**: Clear headers, alternating rows, proper alignment
- **Charts**: Limited to top 15 items for clarity
- **Labels**: Descriptive and concise
- **Values**: Properly formatted (numbers, decimals, dates)

## Troubleshooting

### Export Button Not Working
- Check browser console for JavaScript errors
- Verify user has permission to access reports
- Ensure academic settings are configured

### Empty Report
- Verify data exists for selected filters
- Check academic year and semester settings
- Ensure schedules are not archived

### Chart Not Displaying (Excel)
- Charts only appear when data exists
- Limited to top 15 items to avoid clutter
- Requires at least 1 data point

### PDF Layout Issues
- Landscape orientation is default for tables
- Long names are truncated to fit (30 chars for faculty)
- Use Excel export for full details

## Future Enhancements

Potential improvements:
- Custom date range filters
- Additional chart types (line, stacked bar)
- Comparison reports (year-over-year)
- Email delivery of reports
- Scheduled automatic exports
- More granular filtering options

## References

- **ISO/IEC 25010:2011**: Systems and software Quality Requirements and Evaluation (SQuaRE)
- **OpenPyXL Documentation**: https://openpyxl.readthedocs.io/
- **ReportLab Documentation**: https://www.reportlab.com/docs/
- **Flask Documentation**: https://flask.palletsprojects.com/

---

**Last Updated**: January 25, 2025  
**Version**: 1.0  
**Maintained By**: iSchedWise Development Team
