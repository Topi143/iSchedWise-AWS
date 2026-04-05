# B3 — Decision Confidence Scores on Recommendations

> **Category:** Part B — Add DSS Power Behind Simple Surfaces  
> **Priority:** 5  
> **Effort:** Low  
> **DSS Impact:** ★★★★★ HIGH — Recommendations become quantified, ranked decisions  
> **Simplicity Impact:** ★★★☆☆ Medium — Same cards, just annotated  

---

## Problem Statement

The recommendation engine currently suggests alternative time slots, days, rooms, and faculty — but all suggestions appear without any indication of *how good* each option is. Users see a flat list of alternatives and must judge quality themselves. 

**Example (current):**
```
⏰ Best Times
  [Apply] Tuesday 8:00 AM - 9:30 AM
  [Apply] Thursday 10:00 AM - 11:30 AM
  [Apply] Wednesday 1:00 PM - 2:30 PM
```

There's no indication that the Tuesday 8AM slot is significantly better than the Wednesday 1PM slot. The user has to guess.

---

## Current Scoring (Internal)

### File: [app/services/recommendation_engine.py](../../app/services/recommendation_engine.py)

The recommendation engine already computes internal scores. They're just never exposed to the user.

**Time slot scoring** (lines 1042-1058):
```python
def _calculate_time_slot_score(self, start: time) -> int:
    if 8 <= hour < 10:   return 100  # Prime morning
    elif hour < 8:        return 85   # Early morning  
    elif 10 <= hour < 12: return 90   # Late morning
    elif 13 <= hour < 15: return 80   # Early afternoon
    elif 15 <= hour < 17: return 70   # Late afternoon
    elif 17 <= hour < 19: return 60   # Evening
    else:                 return 50   # Late evening
```

**Workload penalties** (lines 330-337):
```python
base_score = self._calculate_time_slot_score(slot_start)
if faculty_id and (faculty_daily_hours + duration_hours) > self.PREFERRED_DAILY_HOURS:
    base_score -= 20
if faculty_id and (faculty_daily_hours + duration_hours) > self.MAX_FACULTY_DAILY_HOURS:
    base_score -= 40
```

**Room scoring** (lines 506-512):
```python
score = 100
if current_room_type and room.room_type == current_room_type:
    score += 20  # Same room type bonus
if current_building_id and room.building_id == current_building_id:
    score += 10  # Same building bonus
```

**Faculty scoring** (lines 586-593):
```python
score = 100
if weekly_hours >= self.MAX_FACULTY_WEEKLY_UNITS:
    score -= 50
elif weekly_hours > self.MAX_FACULTY_WEEKLY_UNITS * 0.8:
    score -= 20
else:
    score += int((self.MAX_FACULTY_WEEKLY_UNITS - weekly_hours) / 2)
```

**Current score ranges:** The raw scores range roughly from -10 to 130 across different recommendation types. They're used internally for sorting but never shown to the user.

---

## Proposed Solution

### Normalize Scores to 0-100% and Display as Confidence Badges

**After (proposed):**
```
⏰ Best Times
  [95%] [Apply] Tuesday 8:00 AM - 9:30 AM
         "No conflicts • Faculty prefers mornings • Balanced daily load"
  [78%] [Apply] Thursday 10:00 AM - 11:30 AM
         "No conflicts • 4 classes already on Thursday"  
  [52%] [Apply] Wednesday 1:00 PM - 2:30 PM
         "No conflicts • Afternoon slot • Near daily limit"
```

### Badge Visualization

| Score Range | Color | Badge Style |
|-------------|-------|-------------|
| 80-100% | `bg-emerald-100 text-emerald-700` | Green — Excellent match |
| 60-79% | `bg-blue-100 text-blue-700` | Blue — Good match |
| 40-59% | `bg-amber-100 text-amber-700` | Amber — Acceptable |
| 0-39% | `bg-red-100 text-red-700` | Red — Poor match |

---

## Backend Changes

### Score Normalization Function

Add to `app/services/recommendation_engine.py`:

```python
def _normalize_score(self, raw_score, min_possible=-50, max_possible=130):
    """Normalize raw score to 0-100 percentage.
    
    Args:
        raw_score: The raw internal score
        min_possible: Minimum possible score (worst case = 0%)
        max_possible: Maximum possible score (best case = 100%)
    
    Returns:
        int: Normalized score 0-100
    """
    if max_possible == min_possible:
        return 50
    normalized = ((raw_score - min_possible) / (max_possible - min_possible)) * 100
    return max(0, min(100, round(normalized)))
```

### Add Confidence Score to Each Recommendation

Modify the methods that build recommendation dicts to include a `confidence` field:

```python
# In _find_alternative_times():
recommendations.append({
    'type': 'time_slot',
    'day': day,
    'start_time': slot_start.strftime('%H:%M'),
    'end_time': slot_end.strftime('%H:%M'),
    'score': raw_score,                                    # Already exists
    'confidence': self._normalize_score(raw_score, 0, 120), # NEW
    'reason': self._generate_reason(raw_score, factors)     # NEW
})
```

### Reason Generation

```python
def _generate_reason(self, factors):
    """Generate a human-readable reason string from scoring factors.
    
    Args:
        factors: dict of factor_name → score_contribution
        
    Returns:
        str: "No conflicts • Faculty prefers mornings • Balanced daily load"
    """
    reasons = []
    
    if factors.get('conflict_free', True):
        reasons.append('No conflicts')
    else:
        reasons.append('Has conflicts')
    
    if factors.get('time_preference', 0) >= 90:
        reasons.append('Preferred time slot')
    elif factors.get('time_preference', 0) >= 70:
        reasons.append('Good time slot')
    elif factors.get('time_preference', 0) < 50:
        reasons.append('Less preferred time')
    
    if factors.get('workload_penalty', 0) < -30:
        reasons.append('Near daily limit')
    elif factors.get('workload_penalty', 0) == 0:
        reasons.append('Balanced workload')
    
    if factors.get('faculty_available', False):
        reasons.append('Faculty available')
    
    if factors.get('room_type_match', False):
        reasons.append('Room type matches')
    
    if factors.get('same_building', False):
        reasons.append('Same building')
    
    return ' • '.join(reasons[:3])  # Max 3 reasons
```

### Track Scoring Factors

Modify scoring methods to return factors alongside the score:

```python
def _score_time_slot(self, slot_start, faculty_id, day, ...):
    """Score a time slot and return factors breakdown."""
    factors = {}
    
    base = self._calculate_time_slot_score(slot_start)
    factors['time_preference'] = base
    
    workload_penalty = 0
    if faculty_id and daily_hours > self.PREFERRED_DAILY_HOURS:
        workload_penalty -= 20
    if faculty_id and daily_hours > self.MAX_FACULTY_DAILY_HOURS:
        workload_penalty -= 40
    factors['workload_penalty'] = workload_penalty
    
    factors['conflict_free'] = not has_conflicts
    factors['faculty_available'] = is_available
    
    total = base + workload_penalty
    return total, factors
```

---

## Frontend Changes

### Rendering Confidence Badges

In [app/static/js/schedule/schedule_full.js](../../app/static/js/schedule/schedule_full.js) — modify `displayAIRecommendations()`:

```javascript
function renderRecommendationOption(option) {
    const confidence = option.confidence || 0;
    
    // Color based on confidence
    let badgeClass, badgeRing;
    if (confidence >= 80) {
        badgeClass = 'bg-emerald-100 text-emerald-700 ring-emerald-300';
        badgeRing = 'ring-1';
    } else if (confidence >= 60) {
        badgeClass = 'bg-blue-100 text-blue-700 ring-blue-300';
        badgeRing = 'ring-1';
    } else if (confidence >= 40) {
        badgeClass = 'bg-amber-100 text-amber-700 ring-amber-300';
        badgeRing = 'ring-1';
    } else {
        badgeClass = 'bg-red-100 text-red-700 ring-red-300';
        badgeRing = 'ring-1';
    }
    
    return `
        <div class="flex items-start gap-2 p-2 rounded-lg hover:bg-gray-50 transition-colors">
            <!-- Confidence Badge -->
            <span class="flex-shrink-0 px-1.5 py-0.5 text-[10px] font-bold rounded-md ${badgeClass} ${badgeRing}">
                ${confidence}%
            </span>
            
            <!-- Option Content -->
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                    <span class="text-xs font-medium text-gray-900">${option.label}</span>
                    <button onclick="applyRecommendation('${option.type}', ${JSON.stringify(option)})" 
                            class="ml-auto text-[10px] px-2 py-0.5 bg-blue-50 text-blue-600 rounded hover:bg-blue-100">
                        Apply
                    </button>
                </div>
                ${option.reason ? `<p class="text-[10px] text-gray-500 mt-0.5">${option.reason}</p>` : ''}
            </div>
        </div>
    `;
}
```

### Sorting by Confidence (Already Done by Score)

The recommendations already come sorted by score from the backend. Since confidence is derived from score, the order is preserved. The badge just makes the ranking visible.

---

## API Response Change

### Current Response Shape
```json
{
    "recommendations": [
        {
            "type": "time_slot",
            "day": "Tuesday",
            "start_time": "08:00",
            "end_time": "09:30",
            "score": 100
        }
    ]
}
```

### New Response Shape (Backward Compatible)
```json
{
    "recommendations": [
        {
            "type": "time_slot",
            "day": "Tuesday",
            "start_time": "08:00",
            "end_time": "09:30",
            "score": 100,
            "confidence": 95,
            "reason": "No conflicts • Preferred time slot • Balanced workload"
        }
    ]
}
```

New fields `confidence` and `reason` are additive — old clients ignore them.

---

## Implementation Steps

### Step 1: Add Normalization & Reason Functions
1. Add `_normalize_score()` to `recommendation_engine.py`
2. Add `_generate_reason()` to `recommendation_engine.py`

### Step 2: Modify Recommendation Builders
1. In `_find_alternative_times()`: track factors, compute confidence, generate reason
2. In `_find_alternative_days()`: same
3. In `_find_alternative_rooms()`: same  
4. In `_find_alternative_faculty()`: same
5. In exam equivalents: same

### Step 3: Update Frontend Rendering
1. Modify recommendation option rendering in `schedule_full.js`
2. Add confidence badge element
3. Add reason text element
4. Apply to both class and exam recommendation cards

### Step 4: Sort by Confidence
1. Ensure recommendations are sorted by confidence descending
2. Mark the top option visually ("Best Match" label)

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `app/services/recommendation_engine.py` | **Medium edit** | Add normalize, reason functions; modify all 8 recommendation builders |
| `app/static/js/schedule/schedule_full.js` | **Small edit** | Add confidence badge + reason text to recommendation cards |
| `app/static/js/schedule/exam_ai.js` | **Small edit** | Same for exam recommendation cards |

---

## Visual Example

### Before (Current)

```
┌─────────────────────────────────────────┐
│ ⏰ Best Times                           │
│                                         │
│  [Apply] Tuesday 8:00 AM - 9:30 AM     │
│  [Apply] Thursday 10:00 AM - 11:30 AM  │
│  [Apply] Wednesday 1:00 PM - 2:30 PM   │
└─────────────────────────────────────────┘
```

### After (Proposed)

```
┌─────────────────────────────────────────┐
│ ⏰ Best Times                           │
│                                         │
│  [95%] Tuesday 8:00 AM - 9:30 AM [Apply]│
│   No conflicts • Preferred time • Balanced│
│                                         │
│  [78%] Thursday 10:00 AM - 11:30 AM [Ap]│
│   No conflicts • 4 classes on Thursday   │
│                                         │
│  [52%] Wednesday 1:00 PM - 2:30 PM [Ap] │
│   No conflicts • Afternoon • Near limit  │
└─────────────────────────────────────────┘
```

---

## Testing Checklist

- [ ] Confidence scores appear on all recommendation types (time, day, room, faculty)
- [ ] Scores are in 0-100 range (no negative, no >100)
- [ ] Badge color matches score: green ≥80, blue ≥60, amber ≥40, red <40
- [ ] Reason text shows max 3 bullet points
- [ ] Recommendations sorted by confidence (highest first)
- [ ] "Apply" button still works correctly with confidence data
- [ ] Exam recommendations also show confidence scores
- [ ] No visual clutter — badges are compact (10px text, rounded)
- [ ] Dark mode: badge colors adapt
- [ ] When all options are similar quality, scores cluster together (not misleadingly spread)
- [ ] Edge case: only 1 recommendation still shows confidence
- [ ] Backward compatible: old API consumers still work
