# Export for Posting - Template Update

## Overview
Updated the "Export for Posting" functionality to match the official `BSCS_4A_schedule_posting.xlsx` template format.

## Changes Made

### Template Format
The new export format follows this structure:

```
Row 1: NORZAGARAY COLLEGE (Bold, Size 14, Centered across A1:H1)
Row 2: Municipal Compound, Norzagaray, Bulacan (Size 11, Centered across A2:H2)
Row 3: [SEMESTER], AY [YEAR] (Size 11, Centered across A3:H3)
Row 4: CLASS SCHEDULE (Bold, Size 12, Centered across A4:H4)
Row 5: [DEPARTMENT NAME] (Size 11, Centered across A5:H5)
Row 6: Course - Section: [DEPT CODE] [YEAR][SECTION] (Size 11, Centered across A6:H6)
Rows 7-9: Empty spacing
Row 10: "Units" label (Bold, Size 11, Centered across C10:D10)
Row 11: Column Headers (Bold, Size 11, Centered)
Row 12+: Schedule data
```

### Column Structure

| Column | Header | Content | Width |
|--------|--------|---------|-------|
| A | Subject Code | Subject code with type suffix (-Lec/-Lab) | 12.71 |
| B | Description | Full course description | 22.14 |
| C | Lec | Lecture units (center aligned) | 18.71 |
| D | Lab | Lab units (center aligned) | 13.0 |
| E | Day | Day of week | 13.0 |
| F | Time | Start time - End time | 13.0 |
| G | Room | Room number | 12.71 |
| H | Professor | Faculty full name | 13.0 |

### Key Features

1. **Subject Code with Type Suffix**
   - Lecture schedules: `SE 102-Lec`
   - Lab schedules: `NC 102-Lab`

2. **Unit Tracking**
   - Separate columns for lecture and lab units
   - Only shows units for the corresponding schedule type
   - Total units displayed at bottom (merged across C:D)

3. **Time Format**
   - 12-hour format with AM/PM
   - Example: `2:00 PM-4:00 PM`

4. **Professional Layout**
   - Institutional header with official formatting
   - Clean table structure (no borders, calendar grid removed)
   - Easy to read and print

## Implementation Details

### File: `app/routes/schedule.py`

#### Function: `export_class_schedule_for_posting(section_id)`

**Route:** `/schedule/export/class/<section_id>/posting`

**Template Matching:**
- Header rows match official template exactly
- Column widths match pixel-perfect with template
- Font sizes and styles match template specifications
- Merged cells follow template structure

**Unit Calculation:**
- Lecture schedules contribute to Lec column
- Lab schedules contribute to Lab column
- Total units summed at bottom

**Example Output:**
```
NORZAGARAY COLLEGE
Municipal Compound, Norzagaray, Bulacan
1ST SEMESTER, AY 2025-2026
CLASS SCHEDULE
COLLEGE OF COMPUTING STUDIES
Course - Section: BSCS 4A

                          Units
Subject Code | Description | Lec | Lab | Day | Time | Room | Professor
SE 102-Lec | Software Engineering 2 | 2 | 0 | Monday | 2:00 PM-4:00 PM | NB 401 | Lumibao, Jerimy S.
AL 102 | Automata Theory | 3 | 0 | Monday | 10:00 AM-1:00 PM | NB 401 | Lapig, Richter A.
...
Total Units: 24
```

## Differences from Normal Export

| Feature | Normal Export | Export for Posting |
|---------|--------------|-------------------|
| **Format** | Weekly calendar grid | Simple table list |
| **Layout** | Time slots (7 AM - 8 PM) | Row per schedule |
| **Headers** | Institution + Logos | Institution only (no logos) |
| **Columns** | Calendar days | Subject details |
| **Units** | Not shown | Separate Lec/Lab columns |
| **Signatures** | Dean + President | None |
| **Purpose** | Official records | Student bulletin boards |
| **File suffix** | `_Schedule.xlsx` | `_Posting.xlsx` |

## Testing

To test the export:

1. **Via UI:**
   - Go to Schedule Management
   - Select a section with schedules
   - Click "Export for Posting" (purple button)
   - Verify Excel file matches template

2. **Manual Test:**
   ```python
   # In Flask shell
   from app import create_app
   from app.routes.schedule import export_class_schedule_for_posting
   
   app = create_app()
   with app.test_request_context():
       response = export_class_schedule_for_posting(section_id=1)
       # Save and verify output
   ```

3. **Comparison:**
   - Open generated file
   - Open `BSCS_4A_schedule_posting.xlsx` template
   - Compare structure, formatting, and layout

## Benefits

1. ✅ **Consistency** - Matches official institutional template
2. ✅ **Print-Friendly** - Simple layout, less ink usage
3. ✅ **Student-Focused** - Clear, easy-to-read format
4. ✅ **Unit Tracking** - Shows lecture and lab units separately
5. ✅ **Professional** - Official header and formatting
6. ✅ **Standardized** - Same format across all sections

## Related Files

- **Template:** `app/static/templates/BSCS_4A_schedule_posting.xlsx`
- **Route Handler:** `app/routes/schedule.py` (line ~1699)
- **UI Buttons:** 
  - `app/templates/schedule/_class_tab.html` (line ~89)
  - `app/templates/schedule/_exam_tab.html` (line ~85)
  - `app/templates/schedule/_faculty_tab.html` (line ~82)

## Future Enhancements

- [ ] Add option to include/exclude total units row
- [ ] Support for custom column order
- [ ] Optional borders for better printing
- [ ] Export to PDF format
- [ ] Batch export for multiple sections

---

**Updated:** October 21, 2025
**Template Source:** `BSCS_4A_schedule_posting.xlsx`
**Status:** ✅ Implemented and Working
