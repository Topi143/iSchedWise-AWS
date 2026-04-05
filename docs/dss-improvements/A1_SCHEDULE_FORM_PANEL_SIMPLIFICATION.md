# A1 — Schedule Form: 3 Panels → 2 Panels + Smart Drawer

> **Category:** Part A — Simplify What Exists  
> **Priority:** 1 (Highest)  
> **Effort:** Medium  
> **DSS Impact:** Low  
> **Simplicity Impact:** ★★★★★ HIGH — Major visual declutter  

---

## Problem Statement

The schedule creation form is the **most complex page in the entire application** — 2,310 lines of HTML across 3 template files plus 1,529 lines of JavaScript for conflict detection alone. The current 3-panel layout (Form | Calendar | AI) creates several usability issues:

1. **On screens below 1280px (xl breakpoint):** The AI panel disappears entirely or awkwardly inlines above the form on mobile, inverting the natural workflow priority
2. **On xl+ screens:** Three columns compete for attention simultaneously — form fields, calendar events, and AI feedback all demand cognitive focus at the same time
3. **Information overload:** Users must mentally juggle filling fields, reading the calendar, and interpreting conflict/recommendation cards in 3 separate visual areas
4. **Wasted space:** The AI panel is often empty (when no conflicts exist) or showing "All clear" — consuming ~280-320px of horizontal space for a success message

---

## Current Architecture

### File Structure
| File | Lines | Purpose |
|------|-------|---------|
| [app/templates/schedule_form.html](../../app/templates/schedule_form.html) | 1,132 | Parent page with header, tab switcher, panel containers |
| [app/templates/schedule/_class_form_content.html](../../app/templates/schedule/_class_form_content.html) | 575 | Class form — 3-column layout defined here |
| [app/templates/schedule/_exam_form_content.html](../../app/templates/schedule/_exam_form_content.html) | 603 | Exam form — 3-column layout defined here |
| [app/static/js/schedule/auto_conflict_check.js](../../app/static/js/schedule/auto_conflict_check.js) | 658 | Class conflict detection & AI panel updates |
| [app/static/js/schedule/exam_ai.js](../../app/static/js/schedule/exam_ai.js) | 871 | Exam conflict detection & AI panel updates |

### Current 3-Panel Layout (Conceptual)

```
┌─────────────────────┬──────────────────────────┬─────────────────────┐
│   FORM PANEL        │   CALENDAR PANEL         │   AI PANEL          │
│   (340-380px)       │   (flex-1)               │   (280-320px)       │
│                     │                          │   (xl+ only)        │
│ ┌─────────────────┐ │ ┌──────────────────────┐ │ ┌─────────────────┐ │
│ │ Section Selector│ │ │  MON TUE WED THU FRI │ │ │ AI Status       │ │
│ │ Progress Bar    │ │ │  ┌───┐               │ │ │ ─────────────── │ │
│ │ ─────────────── │ │ │  │evt│  ┌───┐        │ │ │ Conflicts:      │ │
│ │ 1. Course       │ │ │  └───┘  │evt│        │ │ │  • Section X    │ │
│ │    Curriculum ▼  │ │ │         └───┘        │ │ │  • Room clash   │ │
│ │    Subject ▼     │ │ │      ┌───┐           │ │ │ ─────────────── │ │
│ │    Type ○ ○      │ │ │      │evt│           │ │ │ Recommendations │ │
│ │ 2. Faculty & Day│ │ │      └───┘           │ │ │  ⏰ Alt times   │ │
│ │    Faculty ▼     │ │ │                      │ │ │  📅 Alt days    │ │
│ │    Day ▼         │ │ │                      │ │ │  🏢 Alt rooms   │ │
│ │ 3. Room & Time  │ │ │                      │ │ │  👤 Alt faculty │ │
│ │    Room ▼        │ │ │                      │ │ │ ─────────────── │ │
│ │    Start Time    │ │ │                      │ │ │ AI Explanation  │ │
│ │    End Time      │ │ │                      │ │ │ (Gemini text)   │ │
│ └─────────────────┘ │ └──────────────────────┘ │ └─────────────────┘ │
└─────────────────────┴──────────────────────────┴─────────────────────┘
```

### Breakpoint Behavior (Current)
| Screen Width | Layout |
|-------------|--------|
| < 768px (mobile) | AI panel inlined ABOVE form as a collapsed purple card → form below → calendar hidden or minimal |
| 768px – 1279px (tablet/laptop) | Form + Calendar only (2 columns), AI panel hidden |
| 1280px+ (xl desktop) | Full 3-panel layout |

---

## Proposed Solution

### New Layout: 2 Panels + Floating Badge + Slide-In Drawer

```
┌─────────────────────┬─────────────────────────────────────────────┐
│   FORM PANEL        │   CALENDAR PANEL (full width)               │
│   (340-380px)       │   (flex-1, more space than before)          │
│                     │                                             │
│ ┌─────────────────┐ │ ┌─────────────────────────────────────────┐ │
│ │ Section Selector│ │ │  MON  TUE  WED  THU  FRI  SAT          │ │
│ │ Progress Bar    │ │ │  ┌───┐                                  │ │
│ │ ─────────────── │ │ │  │evt│  ┌───┐                           │ │
│ │ 1. Course       │ │ │  └───┘  │evt│         ┌───┐             │ │
│ │    Curriculum ▼  │ │ │         └───┘         │evt│             │ │
│ │    Subject ▼     │ │ │      ┌───┐            └───┘             │ │
│ │    Type ○ ○      │ │ │      │evt│                              │ │
│ │ 2. Faculty & Day│ │ │      └───┘                              │ │
│ │    Faculty ▼     │ │ │                                         │ │
│ │    Day ▼         │ │ │                                         │ │
│ │ 3. Room & Time  │ │ │                      ┌─────────────────┐│ │
│ │    Room ▼        │ │ │                      │  ✓ All Clear    ││ │
│ │    Start Time    │ │ │                      │  or             ││ │
│ │    End Time      │ │ │                      │  ⚠ 2 Conflicts  ││ │
│ └─────────────────┘ │ │                      └─────────────────┘│ │
└─────────────────────┴─┴─────────────────────────────────────────┴─┘
                                                   ↑ Floating pill badge
```

### When Badge is Clicked → Drawer Slides In

```
┌─────────────────────┬──────────────────────┬─────────────────────┐
│   FORM PANEL        │   CALENDAR (shrinks) │   AI DRAWER         │
│   (340-380px)       │   (flex-1)           │   (320px overlay)   │
│                     │                      │   slide-in-right    │
│                     │                      │ ┌─────────────────┐ │
│                     │                      │ │ ✕ Close         │ │
│                     │                      │ │ ─────────────── │ │
│                     │                      │ │ Status: ⚠ 2     │ │
│                     │                      │ │ ─────────────── │ │
│                     │                      │ │ Conflicts       │ │
│                     │                      │ │  • Section X    │ │
│                     │                      │ │  • Room clash   │ │
│                     │                      │ │ ─────────────── │ │
│                     │                      │ │ Recommendations │ │
│                     │                      │ │  ⏰ Alt times   │ │
│                     │                      │ │  📅 Alt days    │ │
│                     │                      │ │  🏢 Alt rooms   │ │
│                     │                      │ │ ─────────────── │ │
│                     │                      │ │ AI Explanation  │ │
│                     │                      │ └─────────────────┘ │
└─────────────────────┴──────────────────────┴─────────────────────┘
```

### Responsive Behavior (Proposed)
| Screen Width | Layout |
|-------------|--------|
| < 768px (mobile) | Form only (stacked), floating badge at bottom-right, drawer slides up as bottom sheet |
| 768px – 1279px (tablet/laptop) | Form + Calendar (2 columns), floating badge, drawer overlays on right |
| 1280px+ (xl desktop) | Form + Full Calendar (2 columns), floating badge, drawer overlays on right |

---

## Floating Pill Badge Specification

### Visual States
| State | Color | Icon | Text | Condition |
|-------|-------|------|------|-----------|
| Idle | Gray 200 | — | Hidden | No fields filled yet |
| Checking | Blue 500 pulse | ⟳ spinning | "Checking..." | API call in progress |
| All Clear | Emerald 500 | ✓ | "All Clear" | 0 conflicts detected |
| Warnings | Amber 500 | ⚠ | "2 Warnings" | Only medium/low conflicts |
| Conflicts | Red 500 | ✕ | "3 Conflicts" | Has critical/high conflicts |
| Error | Gray 400 | ! | "Check Failed" | API error or offline |

### Position & Sizing
```css
.ai-floating-badge {
    position: fixed;
    bottom: 1.5rem;               /* 24px from bottom */
    right: 1.5rem;                /* 24px from right */
    z-index: 40;                  /* Below modals (50) but above content */
    padding: 0.5rem 1rem;
    border-radius: 9999px;        /* Full pill shape */
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    transition: all 0.3s ease;
}

/* Pulse animation for checking state */
.ai-floating-badge.checking {
    animation: pulse 1.5s ease-in-out infinite;
}
```

### Interaction
- **Click** → Toggles the AI drawer open/closed
- **Keyboard** → `Escape` closes the drawer
- **Auto-open** → Drawer auto-opens when conflicts are first detected (user can close)
- **Auto-close** → Drawer auto-closes when all conflicts are resolved

---

## AI Drawer Specification

### Structure
```html
<!-- AI Analysis Drawer -->
<div id="aiDrawer" class="fixed top-0 right-0 h-full w-80 xl:w-96 bg-white dark:bg-gray-800 
     shadow-2xl z-45 transform translate-x-full transition-transform duration-300 ease-in-out
     border-l border-gray-200 dark:border-gray-700 overflow-y-auto custom-scrollbar">
    
    <!-- Drawer Header (sticky) -->
    <div class="sticky top-0 bg-white dark:bg-gray-800 border-b p-3 flex items-center justify-between">
        <h3 class="text-sm font-semibold">AI Schedule Assistant</h3>
        <button onclick="toggleAIDrawer()" class="text-gray-400 hover:text-gray-600">✕</button>
    </div>

    <!-- Content: Same as current AI panel, just in drawer form -->
    <div id="aiDrawerContent" class="p-3">
        <!-- Status indicator -->
        <!-- Conflicts list -->
        <!-- Recommendations list -->
        <!-- AI explanation -->
    </div>
</div>
```

### Animation
```css
/* Closed (default) */
#aiDrawer {
    transform: translateX(100%);
}

/* Open */
#aiDrawer.open {
    transform: translateX(0);
}

/* Optional: dim overlay behind drawer on mobile */
@media (max-width: 768px) {
    #aiDrawerOverlay {
        position: fixed;
        inset: 0;
        background: rgba(0,0,0,0.3);
        z-index: 44;
    }
}
```

---

## Implementation Steps

### Step 1: Modify `_class_form_content.html`
1. Remove the third column (AI panel) from the grid layout
2. Change the grid from 3-column to 2-column
3. Add the floating pill badge HTML at the end (outside the grid)
4. Add the drawer HTML as a sibling to the grid (positioned fixed, outside flow)

### Step 2: Modify `_exam_form_content.html`
1. Same changes as class form content
2. Ensure drawer uses exam-specific element IDs

### Step 3: Modify `auto_conflict_check.js`
1. Update DOM references from inline AI panel to drawer elements
2. Add `toggleAIDrawer()` function
3. Add floating badge state management (`updateBadge(state, count)`)
4. Add auto-open logic when conflicts detected for the first time
5. Keep the same API call flow — only the rendering target changes

### Step 4: Modify `exam_ai.js`
1. Same rendering target changes as auto_conflict_check.js
2. Ensure badge + drawer work for exam form independently

### Step 5: Modify `schedule_form.html`
1. Remove any xl-only conditionals that showed/hid the AI panel
2. Ensure the floating badge and drawer are loaded for both form tabs (class + exam)

### Step 6: Update Mobile Layout
1. On mobile (< 768px): floating badge appears at bottom-right
2. Drawer slides up as a bottom sheet (75% viewport height) instead of from the right
3. Add swipe-down-to-close gesture (optional)

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `app/templates/schedule/_class_form_content.html` | **Major edit** | Remove 3rd column, add badge + drawer HTML |
| `app/templates/schedule/_exam_form_content.html` | **Major edit** | Same as class form |
| `app/templates/schedule_form.html` | **Minor edit** | Remove xl-only AI panel conditionals |
| `app/static/js/schedule/auto_conflict_check.js` | **Medium edit** | Render to drawer instead of inline panel, add badge logic |
| `app/static/js/schedule/exam_ai.js` | **Medium edit** | Same as auto_conflict_check.js |
| `app/static/js/schedule/schedule_full.js` | **Medium edit** | Update `displayAIConflicts()` and `displayAIRecommendations()` to target drawer |

---

## User Experience Comparison

| Aspect | Before (3 Panels) | After (2 Panels + Drawer) |
|--------|-------------------|--------------------------|
| Initial visual elements | 3 panels visible | 2 panels + 1 small badge |
| Cognitive load | High (3 areas to focus) | Low (form + calendar only) |
| AI panel on <1280px | Hidden or awkward inline | Always accessible via badge |
| Calendar space | Compressed (flex-1 between 2 fixed panels) | Full remaining width |
| Conflict awareness | Must read AI panel | Instant via color-coded badge |
| Recommendation access | Always visible (even when empty) | On-demand via badge click |
| Mobile experience | AI panel above form (inverted priority) | Badge + bottom sheet |

---

## Testing Checklist

- [ ] Badge appears after first field is filled
- [ ] Badge shows "Checking..." with pulse during API call
- [ ] Badge shows "All Clear" in green when no conflicts
- [ ] Badge shows "N Conflicts" in red when conflicts detected
- [ ] Clicking badge opens drawer with smooth animation
- [ ] Clicking badge again closes drawer
- [ ] Pressing Escape closes drawer
- [ ] Drawer auto-opens on first conflict detection
- [ ] Recommendations "Apply" buttons still work from drawer
- [ ] Calendar has more horizontal space than before
- [ ] Mobile: badge at bottom-right, drawer as bottom sheet
- [ ] Tablet: badge at bottom-right, drawer slides from right
- [ ] Desktop: badge at bottom-right, drawer slides from right
- [ ] Dark mode: badge and drawer adapt correctly
- [ ] Both class and exam forms work independently
- [ ] Batch schedule builder unaffected
