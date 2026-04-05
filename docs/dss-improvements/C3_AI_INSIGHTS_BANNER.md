# C3 — AI Insights Banner (Proactive, Not Hidden)

> **Category:** Part C — Visual Analytics  
> **Priority:** 10  
> **Effort:** Low  
> **DSS Impact:** Medium  
> **Simplicity Impact:** ★★★☆☆ Medium — Key insights visible immediately  

---

## Problem Statement

The AI Analysis feature in Reports Overview is hidden behind a button. Users must:
1. Navigate to Reports → Overview
2. Click "AI Analysis" button
3. Wait for Gemini to generate analysis
4. Read the modal

Most users never discover this feature. The key insights (overloaded faculty, underutilized rooms, scheduling gaps) should be visible **immediately** when the page loads.

---

## Current Implementation

### File: [app/templates/reports/overview.html](../../app/templates/reports/overview.html) (line 49)

```html
<!-- Hidden behind a button -->
<button onclick="openAIModal()" class="bg-gradient-to-r from-blue-600 to-indigo-600 ...">
    <svg><!-- Lightbulb icon --></svg>
    AI Analysis
</button>
```

Clicking opens a modal that calls the backend for Gemini analysis. The modal contains:
- Summary text
- 5 metric widgets
- Insights list (4-5 bullets)
- Recommendations list (4-5 bullets)
- "Regenerate" button

---

## Proposed Solution

### Add a Thin Insight Banner at the Top of Reports Page

On page load, display 1-2 key insights in a **pastel banner** above the stat cards. This uses pre-computed rule-based insights (no Gemini call needed for the banner — keep Gemini for the detailed modal).

**Before:**
```
┌─────────────────────────────────────────────────────────────┐
│ Reports Overview                              [AI Analysis] │
├─────────────────────────────────────────────────────────────┤
│ [Stat Cards: 148 Schedules] [8 Exams] [45 Faculty] [30 S]  │
│ ...                                                         │
```

**After:**
```
┌─────────────────────────────────────────────────────────────┐
│ Reports Overview                              [AI Analysis] │
├─────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────── │ │
│ │ 💡 Faculty workload is 12% higher than last semester.   │ │ ← NEW BANNER
│ │    3 rooms under 20% utilization.  [See full analysis →]│ │
│ └──────────────────────────────────────────────────────── │ │
├─────────────────────────────────────────────────────────────┤
│ [Stat Cards: 148 Schedules] [8 Exams] [45 Faculty] [30 S]  │
│ ...                                                         │
```

---

## Banner Design

### HTML Template

```html
<!-- AI Insight Banner — appears above stat cards -->
{% if ai_insights_banner %}
<div class="mb-3 px-4 py-3 rounded-xl border bg-gradient-to-r from-indigo-50 to-purple-50 
     dark:from-indigo-900/20 dark:to-purple-900/20 border-indigo-100 dark:border-indigo-800">
    <div class="flex items-start gap-3">
        <!-- Icon -->
        <div class="flex-shrink-0 mt-0.5">
            <svg class="w-4 h-4 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
            </svg>
        </div>
        
        <!-- Insights -->
        <div class="flex-1 min-w-0">
            <p class="text-xs text-indigo-900 dark:text-indigo-200 leading-relaxed">
                {{ ai_insights_banner | join(' &nbsp;•&nbsp; ') }}
            </p>
        </div>
        
        <!-- CTA + Dismiss -->
        <div class="flex items-center gap-2 flex-shrink-0">
            <button onclick="openAIModal()" class="text-[10px] text-indigo-600 hover:text-indigo-800 font-medium whitespace-nowrap">
                Full analysis →
            </button>
            <button onclick="this.closest('div.mb-3').remove()" class="text-gray-400 hover:text-gray-600">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
            </button>
        </div>
    </div>
</div>
{% endif %}
```

---

## Insight Generation (Rule-Based, No Gemini)

### Backend: Pre-Computed Insights

```python
def generate_report_insights_banner(stats):
    """Generate 2-3 key insights for the reports page banner.
    
    Uses rule-based logic (no AI API call needed).
    These are pre-computed from calculate_statistics() data.
    
    Args:
        stats: dict from calculate_statistics()
    
    Returns:
        list[str]: 2-3 short insight strings
    """
    insights = []
    
    # --- Faculty workload insights ---
    overloaded = stats.get('overloaded_faculty_count', 0)
    warning = stats.get('warning_faculty_count', 0)
    if overloaded > 0:
        insights.append(
            f"⚠️ {overloaded} faculty member{'s' if overloaded > 1 else ''} "
            f"exceeded maximum workload"
        )
    elif warning > 0:
        insights.append(
            f"{warning} faculty member{'s' if warning > 1 else ''} "
            f"approaching workload limit (>75%)"
        )
    else:
        avg_util = stats.get('avg_faculty_utilization', 0)
        if avg_util > 0:
            insights.append(f"Faculty workloads are balanced (avg {avg_util:.0f}% utilization)")
    
    # --- Room utilization insights ---
    total_rooms = stats.get('total_rooms', 0)
    rooms_in_use = stats.get('rooms_in_use', 0)
    unused_rooms = total_rooms - rooms_in_use
    if unused_rooms > 0 and total_rooms > 0:
        pct = round((unused_rooms / total_rooms) * 100)
        insights.append(f"{unused_rooms} room{'s' if unused_rooms > 1 else ''} ({pct}%) have no schedules assigned")
    
    # --- Schedule completion ---
    total_schedules = stats.get('total_schedules', 0)
    total_sections = stats.get('total_sections', 0)
    if total_sections > 0:
        sections_with = stats.get('sections_with_schedules', total_sections)
        if sections_with < total_sections:
            remaining = total_sections - sections_with
            insights.append(f"{remaining} section{'s' if remaining > 1 else ''} still need scheduling")
    
    # --- Unassigned faculty ---
    unassigned = stats.get('unassigned_faculty_count', 0)
    if unassigned > 0:
        insights.append(f"{unassigned} faculty have no schedule assignments this semester")
    
    # --- Weekly distribution imbalance ---
    by_day = stats.get('schedule_by_day', {})
    if by_day:
        max_day = max(by_day, key=by_day.get) if by_day else None
        min_day = min((d for d in by_day if by_day[d] > 0), key=by_day.get, default=None)
        if max_day and min_day and by_day.get(max_day, 0) > by_day.get(min_day, 0) * 2:
            insights.append(
                f"Schedule imbalance: {max_day} has {by_day[max_day]} classes vs "
                f"{min_day}'s {by_day[min_day]}"
            )
    
    return insights[:3]  # Max 3 insights
```

---

## Integration with Reports Route

### In `app/routes/reports.py`:

```python
@reports_bp.route('/')
@login_required
def index():
    # ... existing code to calculate stats ...
    
    stats = calculate_statistics(
        academic_year=academic_year,
        semester=semester,
        user_department_ids=user_department_ids,
        include={'counts', 'faculty', 'rooms', 'weekly'}
    )
    
    # NEW: Generate banner insights
    ai_insights_banner = generate_report_insights_banner(stats)
    
    return render_template('reports/overview.html',
        stats=stats,
        ai_insights_banner=ai_insights_banner,  # NEW
        # ... existing variables ...
    )
```

---

## Implementation Steps

### Step 1: Add `generate_report_insights_banner()` to Reports Route
1. Add function to `app/routes/reports.py`
2. Call from the `index()` route
3. Pass `ai_insights_banner` to template

### Step 2: Add Banner HTML
1. Insert banner template above stat cards in `reports/overview.html`
2. Add dismiss (X) button
3. Add "Full analysis →" link to existing AI modal

### Step 3: Edge Cases
1. If no insights generated → don't show banner
2. Banner is dismissible (X button removes from DOM)
3. Dark mode styling

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `app/routes/reports.py` | **Small addition** | Add `generate_report_insights_banner()` function |
| `app/templates/reports/overview.html` | **Small edit** | Add insight banner HTML above stat cards |

---

## Key Distinction: Banner vs. AI Modal

| Feature | Banner (NEW) | AI Modal (Existing) |
|---------|-------------|-------------------|
| Trigger | Auto-show on page load | Manual button click |
| Data source | Rule-based (Python) | Gemini AI |
| Latency | Instant (pre-computed) | 2-5 seconds (API call) |
| Content depth | 2-3 short sentences | Full summary + metrics + insights + recommendations |
| API cost | $0 (no API call) | Gemini free tier |
| Dismissible | Yes (X button) | Yes (close modal) |

The banner **complements** the AI modal — it doesn't replace it. The banner gives instant awareness; the modal gives deep analysis.

---

## Testing Checklist

- [ ] Banner appears on reports page load with relevant insights
- [ ] Banner shows max 3 insights separated by bullet dots
- [ ] Dismiss (X) button removes banner from DOM
- [ ] "Full analysis →" opens the existing AI modal
- [ ] Banner does NOT appear when there are no noteworthy insights
- [ ] Banner correctly identifies: overloaded faculty, unused rooms, incomplete scheduling
- [ ] Dark mode: banner gradient and text colors adapt
- [ ] Dean role: insights reflect department-filtered data
- [ ] Performance: banner generation adds <50ms to page load
- [ ] Mobile: banner wraps text properly, dismiss button accessible
