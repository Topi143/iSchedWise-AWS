# Profile Page Department Information Management

**Date**: 2024-02-10  
**Feature**: Department Information Management in Profile Page  
**Status**: ✅ Implemented

## 📋 Overview

This feature allows users (especially Deans) to manage their department's metadata directly from their profile page. Users can update the official full department name, secretary name, and view logo information for departments they have access to.

---

## 🎯 Business Requirements

### User Story
> As a **Dean**, I want to **manage my department's information** from my profile page, so that **I can keep official department details up-to-date** without needing admin assistance for reports and documents.

### Acceptance Criteria
- ✅ Dean users see department information sections for their assigned departments
- ✅ Admin users can update information for all departments
- ✅ Fields include: Full Department Name, Secretary Name, and Logo placeholder
- ✅ Changes are saved to the database with proper validation
- ✅ Activity logging tracks who made changes and when
- ✅ Success/error feedback provided via toast notifications
- ✅ UI is fully responsive (mobile, tablet, desktop)

---

## 🏗️ Technical Implementation

### Database Schema (Already Exists)

**Table**: `departments`

```sql
ALTER TABLE `departments`
ADD COLUMN `full_department_name` VARCHAR(255) NULL DEFAULT NULL COMMENT 'Official full department name',
ADD COLUMN `department_logo` VARCHAR(255) NULL DEFAULT NULL COMMENT 'Path to department logo file',
ADD COLUMN `secretary_name` VARCHAR(100) NULL DEFAULT NULL COMMENT 'Name of department secretary';
```

**Migration Script**: `scripts/add_department_info_columns.sql`

### Backend Changes

#### 1. Model Update: `app/models/department.py`

```python
class Department(db.Model):
    __tablename__ = 'departments'
    
    # ... existing fields ...
    
    # Department metadata fields
    full_department_name = db.Column(db.String(255), nullable=True)
    department_logo = db.Column(db.String(255), nullable=True)
    secretary_name = db.Column(db.String(100), nullable=True)
```

#### 2. Route: `app/routes/profile.py`

**New Endpoint**: `POST /account/update-department`

```python
from app.models.department import Department

@account_bp.route('/update-department', methods=['POST'])
@login_required
def update_department():
    """Update department information from profile page."""
    try:
        data = request.get_json()
        department_id = data.get('department_id')
        
        # Validate department_id
        if not department_id:
            return jsonify({'success': False, 'message': 'Department ID is required'}), 400
        
        department = Department.query.get(department_id)
        if not department:
            return jsonify({'success': False, 'message': 'Department not found'}), 404
        
        # Access control: Admins can update all, Deans only their assigned departments
        if current_user.role != 'admin':
            user_dept_ids = [dept.id for dept in current_user.departments]
            if department_id not in user_dept_ids:
                return jsonify({'success': False, 'message': 'You do not have access to this department'}), 403
        
        # Track changes for activity log
        changes = []
        
        # Update full_department_name
        new_full_name = data.get('full_department_name', '').strip() or None
        if department.full_department_name != new_full_name:
            old_val = department.full_department_name or 'None'
            new_val = new_full_name or 'None'
            changes.append(f"Full Name: {old_val} → {new_val}")
            department.full_department_name = new_full_name
        
        # Update secretary_name
        new_secretary = data.get('secretary_name', '').strip() or None
        if department.secretary_name != new_secretary:
            old_val = department.secretary_name or 'None'
            new_val = new_secretary or 'None'
            changes.append(f"Secretary: {old_val} → {new_val}")
            department.secretary_name = new_secretary
        
        db.session.commit()
        
        # Log activity if changes were made
        if changes:
            from app.utils.activity_logger import log_activity
            change_summary = "; ".join(changes)
            log_activity(
                user_id=current_user.id,
                action='update',
                module='department',
                record_id=department.id,
                description=f"Updated department info for {department.department_code}: {change_summary}"
            )
        
        return jsonify({
            'success': True,
            'message': 'Department information updated successfully',
            'department': {
                'id': department.id,
                'full_department_name': department.full_department_name,
                'secretary_name': department.secretary_name
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
```

**Key Features**:
- ✅ **Access Control**: Admins can update all departments, Deans only their assigned ones
- ✅ **Change Tracking**: Logs what changed (before → after) for audit trail
- ✅ **Validation**: Checks department exists and user has access
- ✅ **Empty String Handling**: Converts empty strings to NULL
- ✅ **Activity Logging**: Records all changes with user ID and timestamp

### Frontend Changes

#### 3. Template: `app/templates/profile.html`

**New Section** (Added after Password Change Form):

```html
<!-- Department Information Form (for users with department access) -->
{% if user.departments %}
{% for dept in user.departments %}
<div class="profile-card p-3 sm:p-4 shadow-sm form-section">
    <h2 class="text-xs sm:text-sm font-bold text-gray-800 mb-3 sm:mb-4 flex items-center">
        <div class="w-6 h-6 sm:w-7 sm:h-7 bg-gradient-to-br from-indigo-600 to-indigo-800 rounded-lg flex items-center justify-center mr-2 section-icon">
            <svg class="w-3 h-3 sm:w-4 sm:h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
            </svg>
        </div>
        Department Information - {{ dept.department_code }}
    </h2>

    <form id="departmentForm{{ dept.id }}" class="space-y-2 sm:space-y-3 form-grid" data-dept-id="{{ dept.id }}">
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-2.5 sm:p-3 mb-3">
            <p class="text-xs text-blue-800 flex items-center">
                <svg class="w-4 h-4 mr-1.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                Update official department information for reports and documents
            </p>
        </div>

        <div>
            <label for="fullDeptName{{ dept.id }}" class="block text-xs font-semibold text-gray-700 mb-1 sm:mb-1.5 form-label">
                Full Department Name
            </label>
            <input type="text" id="fullDeptName{{ dept.id }}" 
                   value="{{ dept.full_department_name or '' }}"
                   class="form-input"
                   placeholder="e.g., Department of Computing Studies">
            <p class="text-xs text-gray-500 mt-1">Official full name for {{ dept.department_code }}</p>
        </div>

        <div>
            <label for="secretaryName{{ dept.id }}" class="block text-xs font-semibold text-gray-700 mb-1 sm:mb-1.5 form-label">
                Department Secretary
            </label>
            <input type="text" id="secretaryName{{ dept.id }}" 
                   value="{{ dept.secretary_name or '' }}"
                   class="form-input"
                   placeholder="e.g., Jane Smith">
            <p class="text-xs text-gray-500 mt-1">Secretary name for {{ dept.department_code }}</p>
        </div>

        <div>
            <label class="block text-xs font-semibold text-gray-700 mb-1 sm:mb-1.5 form-label">
                Department Logo
            </label>
            <div class="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-indigo-400 transition-colors">
                {% if dept.department_logo %}
                <div class="mb-2">
                    <img src="{{ dept.department_logo }}" alt="Department Logo" class="h-16 w-16 mx-auto object-contain">
                </div>
                {% endif %}
                <div class="text-gray-500">
                    <svg class="w-8 h-8 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                    </svg>
                    <p class="text-xs">Logo upload coming soon</p>
                </div>
            </div>
        </div>

        <div class="flex justify-end pt-1 sm:pt-2">
            <button type="submit" class="btn-primary text-white px-3 sm:px-4 py-1.5 sm:py-2 rounded-lg font-semibold text-xs sm:text-sm transition-all duration-200 shadow-md hover:shadow-lg flex items-center save-dept-btn">
                <svg class="w-3 h-3 sm:w-4 sm:h-4 inline-block mr-1 sm:mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                Save Department Info
            </button>
        </div>
    </form>
</div>
{% endfor %}
{% endif %}
```

**Key Features**:
- ✅ **Conditional Rendering**: Only shows for users with assigned departments
- ✅ **Multiple Departments**: Loops through all user departments (useful for future multi-department support)
- ✅ **Pre-filled Values**: Shows current values from database
- ✅ **Responsive Design**: Mobile-first with Tailwind classes
- ✅ **Visual Feedback**: Info banner, loading states, success/error toasts

#### 4. JavaScript Handler (Added to profile.html)

```javascript
// Department Forms Submission (handle all department forms)
document.querySelectorAll('[id^="departmentForm"]').forEach(form => {
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const deptId = this.dataset.deptId;
        const saveBtn = this.querySelector('.save-dept-btn');
        const originalBtnContent = saveBtn.innerHTML;
        
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<svg class="w-3 h-3 sm:w-4 sm:h-4 animate-spin inline-block" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> <span class="ml-1">Saving...</span>';
        
        const formData = {
            department_id: parseInt(deptId),
            full_department_name: document.getElementById('fullDeptName' + deptId).value,
            secretary_name: document.getElementById('secretaryName' + deptId).value
        };
        
        fetch('/account/update-department', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast(data.message, 'success');
                // Update the displayed values if returned
                if (data.department) {
                    if (data.department.full_department_name !== null) {
                        document.getElementById('fullDeptName' + deptId).value = data.department.full_department_name;
                    }
                    if (data.department.secretary_name !== null) {
                        document.getElementById('secretaryName' + deptId).value = data.department.secretary_name;
                    }
                }
            } else {
                showToast(data.message, 'error');
            }
        })
        .catch(error => {
            showToast('Error updating department: ' + error.message, 'error');
        })
        .finally(() => {
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalBtnContent;
        });
    });
});
```

**Key Features**:
- ✅ **Multi-form Support**: Handles multiple department forms on same page
- ✅ **Loading States**: Button shows spinner during save
- ✅ **Error Handling**: Catches network errors and displays user-friendly messages
- ✅ **Value Sync**: Updates form fields with server response
- ✅ **Toast Notifications**: Success/error feedback

---

## 🔐 Security & Validation

### Access Control
1. **Admin Users**: Can update any department
2. **Dean Users**: Can only update their assigned departments
3. **Validation**: Backend checks if user has access before allowing updates

### Data Validation
- ✅ Department ID is required and validated
- ✅ Department must exist in database
- ✅ Empty strings converted to NULL (database consistency)
- ✅ Field length limits enforced by database schema

### Activity Logging
Every department information update is logged:
```
Action: update
Module: department
Record ID: <department_id>
Description: Updated department info for CS: Full Name: None → Department of Computing Studies; Secretary: None → Jane Smith
```

---

## 📱 Responsive Design

### Mobile (320px - 640px)
- Stacked form fields
- Full-width inputs (min 42px height for touch)
- Compact spacing
- Touch-friendly buttons

### Tablet (768px - 1024px)
- Two-column layout for some fields
- Optimized spacing
- Comfortable form interaction

### Desktop (1024px+)
- Full two-column profile layout
- Side-by-side forms
- Enhanced visual hierarchy

---

## 🧪 Testing Checklist

### Manual Testing
- [ ] Dean user logs in and sees their department form
- [ ] Dean can update full department name
- [ ] Dean can update secretary name
- [ ] Dean CANNOT update departments they're not assigned to
- [ ] Admin user can see and update all departments
- [ ] Empty fields save as NULL in database
- [ ] Changes are logged in activity_logs table
- [ ] Success toast appears on successful save
- [ ] Error toast appears on validation failure
- [ ] Form works on mobile, tablet, and desktop
- [ ] Page reload shows updated values

### Database Testing
```sql
-- Check department info after update
SELECT id, department_code, full_department_name, secretary_name, department_logo
FROM departments
WHERE id = 1;

-- Verify activity logging
SELECT * FROM activity_logs
WHERE module = 'department' AND action = 'update'
ORDER BY timestamp DESC
LIMIT 5;
```

---

## 📊 Use Cases

### Use Case 1: Dean Updates Department Name
**Actor**: Dean User (assigned to CS department)

1. Dean navigates to Profile page (`/account/`)
2. Sees "Department Information - CS" section
3. Enters "Department of Computing Studies" in Full Department Name field
4. Clicks "Save Department Info"
5. Success toast: "Department information updated successfully"
6. Activity log created: "Updated department info for CS: Full Name: None → Department of Computing Studies"

### Use Case 2: Dean Updates Secretary
**Actor**: Dean User (assigned to IT department)

1. Dean navigates to Profile page
2. Sees "Department Information - IT" section
3. Enters "Maria Garcia" in Department Secretary field
4. Clicks "Save Department Info"
5. Success toast displays
6. Secretary name saved and visible on next page load

### Use Case 3: Admin Manages Multiple Departments
**Actor**: Admin User

1. Admin navigates to Programs page (`/programs/`)
2. Uses existing department management UI
3. Can add/edit departments with full name and secretary
4. OR navigates to Profile page if assigned to departments (rare for admins)

---

## 🚀 Future Enhancements

### Phase 2: Logo Upload
- [ ] Add file upload functionality
- [ ] Image validation (size, format)
- [ ] Store in `static/uploads/department_logos/`
- [ ] Display logo in reports and documents

### Phase 3: Additional Metadata
- [ ] Department head/dean name
- [ ] Department contact email
- [ ] Department phone number
- [ ] Building/office location

### Phase 4: Bulk Management
- [ ] Admin page to update all department info at once
- [ ] Import from CSV/Excel
- [ ] Export department roster with full names

---

## 📝 Deployment Steps

1. **Backup Database**:
   ```bash
   mysqldump -u root ischedwise_db > backup_before_dept_info.sql
   ```

2. **Run Migration Script**:
   ```sql
   -- In phpMyAdmin or MySQL CLI
   SOURCE scripts/add_department_info_columns.sql;
   ```

3. **Verify Columns Added**:
   ```sql
   DESCRIBE departments;
   ```

4. **Test Application**:
   - Login as Dean user
   - Navigate to Profile page
   - Update department info
   - Verify changes saved

5. **Check Activity Logs**:
   ```sql
   SELECT * FROM activity_logs WHERE module = 'department' ORDER BY timestamp DESC LIMIT 10;
   ```

---

## 📄 Related Files

### Modified Files
1. `app/models/department.py` - Added three new fields
2. `app/routes/profile.py` - Added `update_department()` route
3. `app/templates/profile.html` - Added department info form and JavaScript handler

### New Files
1. `scripts/add_department_info_columns.sql` - Database migration script
2. `docs/features/PROFILE_DEPARTMENT_INFO_MANAGEMENT.md` - This documentation

### Dependencies
- `app/models/department.py` - Department model
- `app/utils/activity_logger.py` - Activity logging
- `app/extensions.py` - Database session

---

## ✅ Completion Status

- ✅ Database schema updated with new columns
- ✅ Migration script created and tested
- ✅ Model updated with new fields
- ✅ Backend route implemented with access control
- ✅ Frontend UI added to profile page
- ✅ JavaScript handler for AJAX submission
- ✅ Activity logging for audit trail
- ✅ Toast notifications for user feedback
- ✅ Responsive design (mobile, tablet, desktop)
- ✅ Documentation created

**Status**: ✅ **Feature Complete and Ready for Testing**

---

## 👥 User Impact

**Deans**: Can now manage their department's official information independently, reducing reliance on admins for simple metadata updates.

**Admins**: Less burden for updating department information; can still manage via Programs page or assign Dean access.

**Reports**: Future reports and documents will display official department names and secretary information from database.

---

**End of Document**
