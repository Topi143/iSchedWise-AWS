# Profile Department Information - Visual UI Guide

**Feature**: Department Information Management in Profile Page  
**Date**: 2024-02-10  
**Status**: ✅ Implemented

---

## 📐 UI Layout

### Desktop View (1024px+)

```
┌────────────────────────────────────────────────────────────────────────┐
│                         PROFILE PAGE                                   │
├──────────────────────┬─────────────────────────────────────────────────┤
│                      │                                                 │
│  LEFT COLUMN         │  RIGHT COLUMN                                   │
│  (Profile Overview)  │  (Edit Forms)                                   │
│                      │                                                 │
│  ┌─────────────┐     │  ┌──────────────────────────────────┐          │
│  │ User Avatar │     │  │ Update Profile Information       │          │
│  │             │     │  │  - Full Name                     │          │
│  │   [Photo]   │     │  │  - Username                      │          │
│  │             │     │  │  - Email                         │          │
│  │ John Doe    │     │  │  [Save Changes Button]           │          │
│  │ dean@...    │     │  └──────────────────────────────────┘          │
│  └─────────────┘     │                                                 │
│                      │  ┌──────────────────────────────────┐          │
│  ┌─────────────┐     │  │ Change Password                  │          │
│  │ Role: DEAN  │     │  │  - Current Password              │          │
│  │ Status: ✓   │     │  │  - New Password                  │          │
│  └─────────────┘     │  │  - Confirm Password              │          │
│                      │  │  [Change Password Button]        │          │
│  ┌─────────────┐     │  └──────────────────────────────────┘          │
│  │ Account     │     │                                                 │
│  │ Details     │     │  ┌──────────────────────────────────┐ ← NEW!  │
│  └─────────────┘     │  │ 🏢 Department Information - CS   │          │
│                      │  │                                  │          │
└──────────────────────┤  │ ℹ️ Update official department    │          │
                       │  │    information for reports...    │          │
                       │  │                                  │          │
                       │  │ Full Department Name:            │          │
                       │  │ [Department of Computing Studies]│          │
                       │  │                                  │          │
                       │  │ Department Secretary:            │          │
                       │  │ [Jane Smith                   ]  │          │
                       │  │                                  │          │
                       │  │ Department Logo:                 │          │
                       │  │ ┌─────────────────────┐          │          │
                       │  │ │      [📷 Icon]      │          │          │
                       │  │ │ Logo upload coming  │          │          │
                       │  │ │      soon           │          │          │
                       │  │ └─────────────────────┘          │          │
                       │  │                                  │          │
                       │  │     [Save Department Info] →     │          │
                       │  └──────────────────────────────────┘          │
                       └─────────────────────────────────────────────────┘
```

### Mobile View (320px - 640px)

```
┌────────────────────────┐
│   PROFILE PAGE         │
├────────────────────────┤
│ ┌────────────────────┐ │
│ │   User Avatar      │ │
│ │    [Photo]         │ │
│ │   John Doe         │ │
│ │   dean@...         │ │
│ └────────────────────┘ │
│                        │
│ ┌────────────────────┐ │
│ │ Update Profile     │ │
│ │  Full Name:        │ │
│ │  [Input]           │ │
│ │  Username:         │ │
│ │  [Input]           │ │
│ │  Email:            │ │
│ │  [Input]           │ │
│ │  [Save Button]     │ │
│ └────────────────────┘ │
│                        │
│ ┌────────────────────┐ │
│ │ Change Password    │ │
│ │  Current Password: │ │
│ │  [Input]           │ │
│ │  New Password:     │ │
│ │  [Input]           │ │
│ │  Confirm Password: │ │
│ │  [Input]           │ │
│ │  [Change Button]   │ │
│ └────────────────────┘ │
│                        │
│ ┌────────────────────┐ │ ← NEW SECTION
│ │🏢 Department - CS  │ │
│ │                    │ │
│ │ℹ️ Update info...   │ │
│ │                    │ │
│ │Full Dept Name:     │ │
│ │[Department of      │ │
│ │ Computing Studies] │ │
│ │                    │ │
│ │Secretary:          │ │
│ │[Jane Smith]        │ │
│ │                    │ │
│ │Logo:               │ │
│ │┌──────────────────┐│ │
│ ││   [📷 Icon]      ││ │
│ ││  Coming soon     ││ │
│ │└──────────────────┘│ │
│ │                    │ │
│ │  [Save Button]     │ │
│ └────────────────────┘ │
└────────────────────────┘
```

---

## 🎨 UI Components Breakdown

### 1. Department Information Card

**Component**: Form card with indigo gradient icon

**Visual Elements**:
```
┌─────────────────────────────────────────┐
│ [🏢] Department Information - CS        │  ← Header with icon
├─────────────────────────────────────────┤
│ ℹ️ Update official department          │  ← Info banner (blue)
│    information for reports and docs     │
├─────────────────────────────────────────┤
│ Full Department Name                    │  ← Label
│ [                                    ]  │  ← Input field
│ Official full name for CS               │  ← Help text
│                                         │
│ Department Secretary                    │  ← Label
│ [                                    ]  │  ← Input field
│ Secretary name for CS                   │  ← Help text
│                                         │
│ Department Logo                         │  ← Label
│ ┌─────────────────────────────────────┐ │
│ │         [📷 Large Icon]             │ │  ← Logo placeholder
│ │      Logo upload coming soon        │ │
│ └─────────────────────────────────────┘ │
│                                         │
│                    [Save Department Info]│ ← Action button
└─────────────────────────────────────────┘
```

### 2. Color Scheme

**Header Icon**: 
- Background: Indigo gradient (from-indigo-600 to-indigo-800)
- Icon: White building icon

**Info Banner**:
- Background: Blue-50
- Border: Blue-200
- Text: Blue-800
- Icon: Info circle (blue)

**Input Fields**:
- Border: Gray-300
- Focus: Blue-500 with shadow
- Placeholder: Gray-400

**Save Button**:
- Background: Blue gradient (from-blue-600 to-blue-800)
- Text: White
- Icon: Checkmark
- Hover: Elevated shadow, slight upward translation

### 3. Icons Used

**Header Icon** (Building):
```
<svg viewBox="0 0 24 24">
  <path d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
</svg>
```

**Info Banner Icon** (Info Circle):
```
<svg viewBox="0 0 24 24">
  <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
</svg>
```

**Logo Placeholder Icon** (Image):
```
<svg viewBox="0 0 24 24">
  <path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
</svg>
```

**Save Button Icon** (Checkmark):
```
<svg viewBox="0 0 24 24">
  <path d="M5 13l4 4L19 7"/>
</svg>
```

---

## 🎬 User Interaction Flow

### Scenario: Dean Updates Department Name

```
Step 1: User navigates to Profile page
┌────────────────────────┐
│ Profile Page Loads     │
│ ✓ User info displayed  │
│ ✓ Forms rendered       │
│ ✓ Dept section shows   │  ← Shows if user.departments exists
└────────────────────────┘
           ↓

Step 2: User types in Full Department Name field
┌────────────────────────┐
│ Input field focused    │
│ Border: Blue           │  ← Focus state
│ Typing: "Department of │
│         Computing..."  │
└────────────────────────┘
           ↓

Step 3: User clicks "Save Department Info" button
┌────────────────────────┐
│ Button state changes:  │
│ - Disabled            │
│ - Shows spinner       │
│ - Text: "Saving..."   │  ← Loading state
└────────────────────────┘
           ↓

Step 4: AJAX request sent to /account/update-department
┌────────────────────────┐
│ POST /account/update-  │
│ department             │
│ {                      │
│   department_id: 1,    │
│   full_department_name:│
│   "Department of       │
│    Computing Studies", │
│   secretary_name: ""   │
│ }                      │
└────────────────────────┘
           ↓

Step 5: Server validates and saves
┌────────────────────────┐
│ ✓ User has access     │
│ ✓ Department exists   │
│ ✓ Data saved to DB    │
│ ✓ Activity logged     │
└────────────────────────┘
           ↓

Step 6: Success response received
┌────────────────────────┐
│ {                      │
│   success: true,       │
│   message: "Department │
│   information updated  │
│   successfully"        │
│ }                      │
└────────────────────────┘
           ↓

Step 7: Toast notification shows
┌────────────────────────┐
│ ╔════════════════════╗ │
│ ║ ✓ Department info  ║ │  ← Green success toast
│ ║   updated success  ║ │     (top-right corner)
│ ║   fully            ║ │
│ ╚════════════════════╝ │
└────────────────────────┘
           ↓

Step 8: Button returns to normal state
┌────────────────────────┐
│ Button state:          │
│ - Enabled             │
│ - Shows checkmark     │
│ - Text: "Save Dept    │
│         Info"         │  ← Ready for next save
└────────────────────────┘
```

---

## 🎯 Visual States

### 1. Empty State (No Data)
```
Full Department Name
[                                        ]  ← Placeholder shown
Official full name for CS

Department Secretary
[                                        ]  ← Placeholder shown
Secretary name for CS
```

### 2. Filled State (Has Data)
```
Full Department Name
[Department of Computing Studies         ]  ← Value displayed
Official full name for CS

Department Secretary
[Jane Smith                              ]  ← Value displayed
Secretary name for CS
```

### 3. Loading State (Saving)
```
                    [⟳ Saving...]
                    ^^^^^^^^^^^^
                    Button disabled
                    Shows spinner
```

### 4. Success State (Toast)
```
                                    ┌────────────────┐
                                    │ ✓ Department   │ ← Slides in
                                    │   info updated │   from right
                                    │   successfully │
                                    └────────────────┘
                                         (Auto-dismiss
                                          after 5s)
```

### 5. Error State (Toast)
```
                                    ┌────────────────┐
                                    │ ⚠ Error: You   │ ← Red border
                                    │   do not have  │   Red icon
                                    │   access...    │
                                    └────────────────┘
```

---

## 📱 Responsive Breakpoints

### Mobile (320px - 640px)
- **Layout**: Single column, stacked sections
- **Input Width**: 100% (full width)
- **Font Sizes**: 0.75rem - 0.875rem
- **Padding**: 0.75rem (12px)
- **Button Height**: 42px (touch-friendly)
- **Icon Size**: 0.875rem - 1rem

### Tablet (768px - 1024px)
- **Layout**: Transitioning to two-column
- **Input Width**: 100% in forms
- **Font Sizes**: 0.875rem - 1rem
- **Padding**: 1rem (16px)
- **Button Height**: 40px
- **Icon Size**: 1rem - 1.25rem

### Desktop (1024px+)
- **Layout**: Full two-column (left: overview, right: forms)
- **Input Width**: 100% in form grid
- **Font Sizes**: 0.875rem - 1rem
- **Padding**: 1rem - 1.5rem (16px - 24px)
- **Button Height**: 40px
- **Icon Size**: 1rem - 1.25rem

---

## 🧩 Component Hierarchy

```
ProfilePage
│
├── LeftColumn (Profile Overview)
│   ├── UserAvatarCard
│   ├── RoleInfoCard
│   └── AccountDetailsCard
│
└── RightColumn (Edit Forms)
    ├── UpdateProfileForm
    ├── ChangePasswordForm
    └── DepartmentInfoForm (NEW!)  ← Multiple forms if user has multiple departments
        ├── InfoBanner
        ├── FullDepartmentNameInput
        ├── SecretaryNameInput
        ├── LogoPlaceholder
        └── SaveButton
```

---

## 🎨 Tailwind CSS Classes Reference

### Form Card
```css
.profile-card {
  @apply bg-white border border-gray-200 rounded-xl shadow-sm;
}

.form-section {
  @apply p-3 sm:p-4;
}
```

### Section Header
```css
.section-header {
  @apply text-xs sm:text-sm font-bold text-gray-800 mb-3 sm:mb-4 flex items-center;
}

.section-icon {
  @apply w-6 h-6 sm:w-7 sm:h-7 bg-gradient-to-br from-indigo-600 to-indigo-800 rounded-lg flex items-center justify-center mr-2;
}
```

### Form Inputs
```css
.form-input {
  @apply w-full px-3 py-2 border border-gray-300 rounded-lg text-sm;
  @apply focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500;
}

.form-label {
  @apply block text-xs font-semibold text-gray-700 mb-1 sm:mb-1.5;
}
```

### Buttons
```css
.btn-primary {
  @apply bg-gradient-to-br from-blue-600 to-blue-800 text-white;
  @apply px-3 sm:px-4 py-1.5 sm:py-2 rounded-lg font-semibold text-xs sm:text-sm;
  @apply transition-all duration-200 shadow-md hover:shadow-lg;
  @apply flex items-center;
}
```

---

## 🔍 Accessibility Features

1. **Semantic HTML**:
   - `<form>` element with proper submit handling
   - `<label>` elements with `for` attributes
   - `<button type="submit">` for form submission

2. **Keyboard Navigation**:
   - Tab through form fields
   - Enter to submit form
   - ESC to close toast notifications

3. **Screen Reader Support**:
   - Label text describes input purpose
   - Helper text provides context
   - Button text describes action
   - Toast messages are announced

4. **Visual Indicators**:
   - Focus states on inputs (blue border + shadow)
   - Loading states (spinner icon)
   - Success/error feedback (colored toasts)
   - Disabled states (grayed out button)

5. **Touch Targets**:
   - Buttons: Minimum 42px height on mobile
   - Input fields: Minimum 42px height
   - Adequate spacing between interactive elements

---

## 📊 User Scenarios

### Scenario 1: First-Time Setup
**User**: Dean John Doe (CS department)
**Goal**: Add official department name

```
1. Login → Navigate to Profile
2. See "Department Information - CS" section (empty)
3. Enter "Department of Computing Studies"
4. Click "Save Department Info"
5. See success toast
6. Reload page → Name is saved
```

### Scenario 2: Update Secretary
**User**: Dean Maria Garcia (IT department)
**Goal**: Add secretary name

```
1. Login → Navigate to Profile
2. See "Department Information - IT" section
3. Enter "Jane Smith" in Secretary field
4. Click "Save Department Info"
5. See success toast
6. Activity log records change
```

### Scenario 3: Admin Access Control
**User**: Admin (no departments assigned)
**Goal**: Should not see department form

```
1. Login as Admin → Navigate to Profile
2. ✓ Profile form shows
3. ✓ Password form shows
4. ✗ Department form does NOT show (user.departments is empty)
5. Admin uses Programs page for department management
```

---

**End of Visual UI Guide**
