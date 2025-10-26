# Department Logo Upload Feature

**Date**: 2024-02-10  
**Feature**: Department Logo Upload & Management  
**Status**: ✅ Implemented

---

## 📋 Overview

This feature allows users (Deans and Admins) to upload, view, and remove department logos directly from their profile page. Logos are stored in the file system and displayed throughout the application.

---

## 🎯 Features

- ✅ **Upload Logo**: Click-to-upload interface with drag-and-drop-like feel
- ✅ **Preview**: Instant preview of uploaded logo
- ✅ **Remove Logo**: One-click logo removal with confirmation
- ✅ **File Validation**: Type and size validation
- ✅ **Security**: Access control (Admins and assigned Deans only)
- ✅ **Activity Logging**: All uploads/removals tracked in audit log
- ✅ **Responsive**: Works on mobile, tablet, and desktop

---

## 🔧 Technical Implementation

### Backend Routes

#### 1. Upload Logo - `POST /account/upload-department-logo`

**Route**: `app/routes/profile.py`

**Features**:
- Accepts multipart/form-data with file and department_id
- Validates file type (PNG, JPG, JPEG, GIF, SVG)
- Validates file size (max 5MB)
- Generates secure filename with timestamp
- Deletes old logo if exists
- Stores file in `app/static/uploads/department_logos/`
- Updates database with file path
- Logs activity for audit trail

**Request**:
```
POST /account/upload-department-logo
Content-Type: multipart/form-data

logo: [file]
department_id: 1
```

**Response**:
```json
{
  "success": true,
  "message": "Logo uploaded successfully",
  "logo_url": "/static/uploads/department_logos/dept_CS_20240210_143025.png"
}
```

**Security**:
- ✅ `@login_required` - User must be logged in
- ✅ Access control - Admins can upload for any department, Deans only for assigned departments
- ✅ File validation - Type and size checks
- ✅ Secure filename - Uses `secure_filename()` to prevent path traversal

#### 2. Remove Logo - `POST /account/remove-department-logo`

**Route**: `app/routes/profile.py`

**Features**:
- Accepts JSON with department_id
- Deletes file from file system
- Clears logo path from database
- Logs activity for audit trail

**Request**:
```json
POST /account/remove-department-logo
Content-Type: application/json

{
  "department_id": 1
}
```

**Response**:
```json
{
  "success": true,
  "message": "Logo removed successfully"
}
```

**Security**:
- ✅ `@login_required` - User must be logged in
- ✅ Access control - Same as upload route
- ✅ Confirmation dialog - JavaScript confirms before sending request

---

### Frontend Implementation

#### Template Changes - `app/templates/profile.html`

**Logo Upload Area**:
```html
<div class="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-indigo-400 transition-colors cursor-pointer" 
     id="logoUploadArea{{ dept.id }}" 
     onclick="document.getElementById('logoInput{{ dept.id }}').click()">
    
    <!-- Logo Preview (if exists) -->
    <div class="mb-2" id="logoPreview{{ dept.id }}">
        {% if dept.department_logo %}
        <img src="{{ dept.department_logo }}" alt="Department Logo" class="h-20 w-20 mx-auto object-contain">
        {% endif %}
    </div>
    
    <!-- Upload Placeholder -->
    <div class="text-gray-500" id="logoPlaceholder{{ dept.id }}">
        <svg class="w-8 h-8 mx-auto mb-2 text-gray-400">...</svg>
        <p class="text-xs font-medium">Click to upload logo</p>
        <p class="text-xs text-gray-400 mt-1">PNG, JPG, GIF, SVG (Max 5MB)</p>
    </div>
    
    <!-- Hidden File Input -->
    <input type="file" id="logoInput{{ dept.id }}" class="hidden" 
           accept="image/png,image/jpeg,image/jpg,image/gif,image/svg+xml" 
           data-dept-id="{{ dept.id }}">
</div>

<!-- Remove Logo Button (if logo exists) -->
{% if dept.department_logo %}
<div class="mt-2 flex justify-center">
    <button type="button" class="remove-logo-btn text-xs text-red-600 hover:text-red-800 font-medium flex items-center" 
            data-dept-id="{{ dept.id }}">
        <svg>...</svg>
        Remove Logo
    </button>
</div>
{% endif %}
```

**JavaScript Handlers**:

1. **Logo Upload Handler**:
```javascript
document.querySelectorAll('[id^="logoInput"]').forEach(input => {
    input.addEventListener('change', function(e) {
        const file = e.target.files[0];
        const deptId = this.dataset.deptId;
        
        // Validate file size
        if (file.size > 5 * 1024 * 1024) {
            showToast('File too large. Maximum size is 5MB', 'error');
            return;
        }
        
        // Validate file type
        const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/svg+xml'];
        if (!allowedTypes.includes(file.type)) {
            showToast('Invalid file type. Please upload PNG, JPG, GIF, or SVG', 'error');
            return;
        }
        
        // Show preview
        const reader = new FileReader();
        reader.onload = function(e) {
            const preview = document.getElementById('logoPreview' + deptId);
            preview.innerHTML = '<img src="' + e.target.result + '" alt="Logo Preview" class="h-20 w-20 mx-auto object-contain">';
        };
        reader.readAsDataURL(file);
        
        // Upload file via FormData
        const formData = new FormData();
        formData.append('logo', file);
        formData.append('department_id', deptId);
        
        fetch('/account/upload-department-logo', {
            method: 'POST',
            headers: {'X-CSRFToken': getCSRFToken()},
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast(data.message, 'success');
                setTimeout(() => location.reload(), 1500);
            } else {
                showToast(data.message, 'error');
            }
        });
    });
});
```

2. **Remove Logo Handler**:
```javascript
document.querySelectorAll('.remove-logo-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const deptId = this.dataset.deptId;
        
        if (!confirm('Are you sure you want to remove this logo?')) {
            return;
        }
        
        fetch('/account/remove-department-logo', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ department_id: parseInt(deptId) })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast(data.message, 'success');
                setTimeout(() => location.reload(), 1500);
            }
        });
    });
});
```

---

## 📁 File Structure

### New Files/Directories Created

```
app/
├── static/
│   └── uploads/
│       └── department_logos/
│           ├── .gitkeep                    # Ensures directory is tracked by Git
│           └── dept_CS_20240210_143025.png # Example uploaded logo (gitignored)
└── routes/
    └── profile.py                          # Updated with upload/remove routes
```

### Updated Files

1. **`app/routes/profile.py`**:
   - Added imports: `secure_filename`, `os`
   - Added constants: `ALLOWED_EXTENSIONS`, `MAX_FILE_SIZE`
   - Added function: `allowed_file(filename)`
   - Added route: `upload_department_logo()`
   - Added route: `remove_department_logo()`

2. **`app/templates/profile.html`**:
   - Updated logo upload area with clickable interface
   - Added hidden file input with proper attributes
   - Added Remove Logo button (conditional)
   - Added JavaScript handlers for upload/remove

3. **`.gitignore`**:
   - Added rules to ignore uploaded logos but keep directory

---

## 🔐 Security Features

### 1. File Validation

**File Type Whitelist**:
```python
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
```

**File Size Limit**:
```python
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
```

**Validation Function**:
```python
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
```

### 2. Secure Filename

Uses `werkzeug.utils.secure_filename()` to prevent:
- Path traversal attacks (e.g., `../../etc/passwd`)
- Special characters in filename
- Cross-platform filename issues

**Filename Format**:
```
dept_{department_code}_{timestamp}.{extension}
```

**Example**:
```
dept_CS_20240210_143025.png
```

### 3. Access Control

**Upload/Remove Rules**:
- ✅ Admin users can manage logos for any department
- ✅ Dean users can only manage logos for assigned departments
- ❌ Dean users cannot manage logos for other departments
- ❌ Unauthenticated users cannot access these routes

**Implementation**:
```python
# Check if user has access to this department
user_department_ids = current_user.get_department_ids()
if user_department_ids is not None:  # Dean user
    if department.id not in user_department_ids:
        return jsonify({'success': False, 'message': 'You do not have access to this department'}), 403
```

### 4. CSRF Protection

All POST requests include CSRF token:
```javascript
headers: {
    'X-CSRFToken': getCSRFToken()
}
```

---

## 📊 User Flows

### Flow 1: Upload Logo

```
1. Dean navigates to Profile page
   ↓
2. Sees Department Information section with logo upload area
   ↓
3. Clicks on upload area (or drag-and-drop placeholder)
   ↓
4. Browser file picker opens
   ↓
5. User selects image file (PNG, JPG, GIF, SVG)
   ↓
6. JavaScript validates file type and size
   ↓
7. If valid:
   - Show instant preview (FileReader API)
   - Upload starts (FormData + fetch)
   - Show "Uploading..." spinner
   ↓
8. Server receives file:
   - Validates file type and size
   - Generates secure filename
   - Saves to disk
   - Updates database
   - Logs activity
   ↓
9. Success response returns logo URL
   ↓
10. JavaScript shows success toast
    ↓
11. Page reloads after 1.5s to show Remove button
    ↓
12. Logo now displayed in profile
```

### Flow 2: Remove Logo

```
1. Dean sees uploaded logo with "Remove Logo" button
   ↓
2. Clicks "Remove Logo" button
   ↓
3. Confirmation dialog appears:
   "Are you sure you want to remove this logo?"
   ↓
4. User clicks OK
   ↓
5. JavaScript sends DELETE request
   ↓
6. Server deletes file from disk
   ↓
7. Server clears logo path from database
   ↓
8. Server logs activity
   ↓
9. Success response returned
   ↓
10. JavaScript shows success toast
    ↓
11. Page reloads after 1.5s
    ↓
12. Logo removed, placeholder shown again
```

---

## 🧪 Testing

### Manual Testing Checklist

- [ ] **Upload Valid Image**:
  - [ ] PNG file uploads successfully
  - [ ] JPG file uploads successfully
  - [ ] GIF file uploads successfully
  - [ ] SVG file uploads successfully
  - [ ] Logo preview shows immediately
  - [ ] Logo persists after page reload

- [ ] **File Validation**:
  - [ ] Files over 5MB rejected with error message
  - [ ] Invalid file types (PDF, TXT, etc.) rejected
  - [ ] Error toast displays for invalid files

- [ ] **Remove Logo**:
  - [ ] Confirmation dialog appears
  - [ ] Clicking Cancel aborts removal
  - [ ] Clicking OK removes logo
  - [ ] Logo file deleted from disk
  - [ ] Database cleared
  - [ ] Placeholder shown after removal

- [ ] **Access Control**:
  - [ ] Dean can upload for assigned department
  - [ ] Dean CANNOT upload for unassigned department
  - [ ] Admin can upload for any department

- [ ] **Activity Logging**:
  - [ ] Upload logged in activity_logs table
  - [ ] Remove logged in activity_logs table
  - [ ] Log includes user ID, department, and action

- [ ] **Responsive Design**:
  - [ ] Upload area clickable on mobile
  - [ ] Preview displays correctly on all screen sizes
  - [ ] Remove button accessible on mobile

### SQL Testing Queries

```sql
-- Check uploaded logo
SELECT id, department_code, department_logo 
FROM departments 
WHERE department_logo IS NOT NULL;

-- Check activity logs
SELECT * FROM activity_logs 
WHERE module = 'department_info' 
AND description LIKE '%Logo%'
ORDER BY timestamp DESC 
LIMIT 10;
```

### File System Verification

```bash
# Check uploaded files
ls -lh app/static/uploads/department_logos/

# Check file permissions
stat app/static/uploads/department_logos/dept_CS_*.png
```

---

## 🐛 Common Issues & Solutions

### Issue 1: "No file uploaded" error

**Cause**: File input not properly configured  
**Solution**: Ensure file input has `type="file"` and form has `enctype="multipart/form-data"`

### Issue 2: File too large error

**Cause**: File exceeds 5MB limit  
**Solution**: User should resize/compress image before upload

### Issue 3: Logo not displaying after upload

**Cause**: Incorrect file path or permissions  
**Solution**: Check file path in database matches actual file location, verify file permissions

### Issue 4: Cannot remove logo

**Cause**: File locked or permission denied  
**Solution**: Check file permissions, ensure no other process has file open

### Issue 5: Old logo not deleted

**Cause**: File path mismatch or file already deleted  
**Solution**: Backend catches exception and continues (non-blocking)

---

## 🚀 Future Enhancements

### Phase 2 Features

1. **Drag & Drop**:
   - Add HTML5 drag-and-drop API
   - Visual feedback when dragging over upload area
   - Multiple file upload support

2. **Image Cropping**:
   - Client-side image cropping tool
   - Enforce aspect ratio (square logos)
   - Real-time preview of cropped image

3. **Compression**:
   - Auto-compress large images
   - Convert to WebP format for better performance
   - Generate multiple sizes (thumbnail, medium, large)

4. **Logo Library**:
   - Predefined logo templates
   - Icon library for quick selection
   - School-wide logo repository

5. **Advanced Features**:
   - Logo version history (track changes)
   - Revert to previous logo
   - Logo approval workflow (submit → review → approve)

---

## 📝 Configuration

### Environment Variables (Optional)

```env
# Maximum file upload size (bytes)
MAX_UPLOAD_SIZE=5242880  # 5MB

# Allowed file extensions
ALLOWED_LOGO_EXTENSIONS=png,jpg,jpeg,gif,svg

# Upload directory (relative to app/static/)
LOGO_UPLOAD_DIR=uploads/department_logos
```

### Flask Config (Optional)

```python
# config/config.py

class Config:
    # File Upload Settings
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max file size
    UPLOAD_FOLDER = 'app/static/uploads/department_logos'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
```

---

## ✅ Deployment Checklist

1. **Create Upload Directory**:
   ```bash
   mkdir -p app/static/uploads/department_logos
   chmod 755 app/static/uploads/department_logos
   ```

2. **Verify Permissions**:
   ```bash
   # Web server user (e.g., www-data, apache, nginx) must have write access
   chown -R www-data:www-data app/static/uploads/
   ```

3. **Update .gitignore**:
   - Ensure uploaded logos are not committed to Git
   - Keep `.gitkeep` file to track directory

4. **Test Upload/Remove**:
   - Upload test logo
   - Verify file created in correct directory
   - Check database updated
   - Remove logo
   - Verify file deleted

5. **Check Activity Logs**:
   ```sql
   SELECT * FROM activity_logs WHERE module = 'department_info' ORDER BY timestamp DESC LIMIT 5;
   ```

---

## 📚 Related Documentation

- [Profile Department Info Management](./PROFILE_DEPARTMENT_INFO_MANAGEMENT.md) - Overall department management feature
- [Profile Department Info UI Guide](./PROFILE_DEPARTMENT_INFO_UI_GUIDE.md) - UI visual guide

---

**End of Document**
