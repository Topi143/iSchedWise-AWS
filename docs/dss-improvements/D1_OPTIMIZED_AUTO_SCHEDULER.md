# D1 — Optimized Auto-Scheduler (Quick vs Smart Mode)

> **Category:** Part D — Advanced (Stretch Goals)  
> **Priority:** 12  
> **Effort:** High  
> **DSS Impact:** ★★★★★ Very High  
> **Simplicity Impact:** ★★★★☆ High — Same button, better results  

---

## Problem Statement

The current `AutoScheduler` uses a **greedy heuristic**: it sorts subjects by total units (heaviest first) and places each one into the first acceptable slot. This is fast but often produces suboptimal schedules:

- A subject placed early may "steal" the best slot from a later subject that needs it more
- No backtracking — once placed, a subject is never reconsidered
- Faculty workload distribution is scored but not globally optimized
- Day-balancing uses a local penalty (excess × 50) rather than a global objective

The result: many "unplaceable" subjects when the timetable gets tight, and uneven distributions.

---

## Current Implementation

### File: [app/services/auto_scheduler.py](../../app/services/auto_scheduler.py) (~2249 lines)

**Key method — `generate_batch_preview()` (line 105):**
```python
def generate_batch_preview(self, section_id, curriculum_id=None,
                            preferred_building_id=None):
    # ...
    # 4. Sort by total units descending (heaviest subjects first)
    unscheduled.sort(key=lambda s: float(s.total_units or 0), reverse=True)
    
    # 5. Load all existing schedules for conflict checking
    existing_schedules = Schedule.query.filter_by(...)
    
    # 6. Run greedy placement WITHOUT faculty
    proposed, unplaceable = self._greedy_place_batch(
        section, unscheduled, existing_schedules, settings,
        preferred_building_id=preferred_building_id
    )
```

**Key method — `_score_candidate()` (line 1302):**
```python
def _score_candidate(self, day, start, faculty, room,
                      subject, schedule_type, all_schedules, settings, section=None):
    score = 0
    score += self.TIME_PREFERENCE.get(start.hour, 50)     # 40-100
    score += self.DAY_PREFERENCE.get(day, 60)              # 60-90
    score -= day_excess * 50                                # Day-balancing penalty
    score -= 100  # Faculty overload penalty
    score -= 200  # Back-to-back penalty (no break)
    score += 80   # Ideal gap bonus (30-60 min)
    score += 30   # Room type match bonus
    return score
```

**Limitations:**
1. **Greedy, no backtracking** — first-fit placement, never reconsiders
2. **No faculty auto-assignment** — `faculty_id=null` in preview; user must pick
3. **Sequential placement** — subject order matters, no global view
4. **No constraint propagation** — doesn't detect dead-ends early

---

## Proposed Solution

### Two Modes: "Quick" (Current) and "Smart" (New)

Add a **mode toggle** to the batch scheduler UI. Both modes use the same button and produce the same output format — the difference is the algorithm behind the scenes.

| Feature | Quick Mode (Current) | Smart Mode (New) |
|---------|---------------------|-----------------|
| Algorithm | Greedy heuristic | Backtracking + constraint propagation |
| Speed | <5 seconds | 10-30 seconds |
| Quality | Good (70-85% SQI) | Excellent (85-98% SQI) |
| Unplaceable | May have some | Fewer (explores alternatives) |
| Faculty auto-assign | No | Optional |
| Library | None | Native Python (no external deps) |

**UI:**
```
┌──────────────────────────────────────────────────────────────────┐
│ Auto-Generate Schedule                                           │
│                                                                  │
│ Section: [BSIT 1-A  ▾]   Building: [GV Hall  ▾]                │
│                                                                  │
│ Mode:  ⚡ Quick  |  🧠 Smart                                    │
│        ~3 sec       ~15 sec                                      │
│        First-fit    Best-fit                                      │
│                                                                  │
│                                [Generate Preview]                │
└──────────────────────────────────────────────────────────────────┘
```

After generation, show SQI comparison:
```
┌ Schedule Quality ──────────────────────────────────────┐
│  SQI: 92/100  ⬆️ +14 vs Quick mode                    │
│  ✓ 12/12 subjects placed  •  0 conflicts              │
│  Faculty spread: 4.2 ± 0.3 hrs/day (balanced)         │
└────────────────────────────────────────────────────────┘
```

---

## Smart Mode Algorithm: Backtracking with Constraint Propagation

### Why Not OR-Tools?

While OR-Tools CP-SAT is the gold standard, it adds a ~15MB dependency and complex setup. For a thesis project, a well-implemented **backtracking search with forward-checking** is sufficient and has zero dependencies.

### Algorithm Overview

```
1. Sort subjects by "most constrained first" (MCV heuristic)
   - Fewest available time slots → schedule first
   - This is the key insight: constrained subjects get first pick

2. For each subject, try all candidate (day, time, room) combos:
   a. Score each candidate using existing _score_candidate()
   b. Sort candidates by score (best first)
   c. Forward-check: does placing here make ANY remaining subject impossible?
      - If yes, skip this candidate (pruning)
   d. Place subject and recurse to next

3. If no valid placement exists, BACKTRACK:
   - Undo last placement
   - Try next-best candidate for previous subject
   - Depth limit: max 3 backtracks per subject

4. Return best solution found
```

### Python Implementation

```python
class SmartScheduler:
    """Backtracking scheduler with constraint propagation.
    
    Extends AutoScheduler's scoring but uses backtracking search
    instead of greedy placement to find globally better solutions.
    """
    
    MAX_BACKTRACKS_PER_SUBJECT = 3
    MAX_TOTAL_BACKTRACKS = 50     # Safety limit
    TIMEOUT_SECONDS = 30          # Hard time limit
    
    def __init__(self, auto_scheduler: 'AutoScheduler'):
        self.auto = auto_scheduler
        self.conflict_detector = auto_scheduler.conflict_detector
    
    def generate_smart_preview(self, section_id, curriculum_id=None,
                                preferred_building_id=None):
        """
        Generate an optimized batch schedule using backtracking search.
        
        Returns same format as AutoScheduler.generate_batch_preview()
        so the UI doesn't need changes.
        """
        import time as time_module
        
        # Reuse AutoScheduler's data loading
        section, settings, unscheduled, existing = self._load_data(
            section_id, curriculum_id
        )
        if not unscheduled:
            return self.auto.generate_batch_preview(section_id, curriculum_id,
                                                      preferred_building_id)
        
        rooms = self._load_rooms(settings, preferred_building_id)
        
        # Build candidate slots for each subject
        subjects_with_slots = self._build_candidates(
            section, unscheduled, existing, rooms, settings
        )
        
        # Sort by Most Constrained Variable (MCV) heuristic
        # Subject with fewest candidates goes first
        subjects_with_slots.sort(key=lambda x: len(x['candidates']))
        
        # Run backtracking search
        start_time = time_module.time()
        best_solution = []
        self._total_backtracks = 0
        
        solution = self._backtrack(
            subjects_with_slots, 0, [], existing[:],
            section, settings, start_time
        )
        
        if solution is None:
            # Fallback to greedy if backtracking times out
            return self.auto.generate_batch_preview(
                section_id, curriculum_id, preferred_building_id
            )
        
        # Convert solution to same format as greedy output
        return self._format_result(solution, section, settings, unscheduled)
    
    def _build_candidates(self, section, subjects, existing, rooms, settings):
        """For each subject, enumerate all valid (day, time, room) candidates."""
        result = []
        days = self.auto._get_allowed_days(settings)
        
        for subj in subjects:
            slots = self.auto._determine_slots_needed(subj)
            for slot in slots:
                duration = slot['duration']
                candidates = []
                
                for day in days:
                    for start in self._time_slots(settings):
                        end = self._add_minutes(start, duration)
                        if end is None:
                            continue
                        
                        for room in rooms:
                            # Hard constraint: no conflict
                            if self.auto._has_section_conflict(
                                section.id, day, start, end, existing
                            ):
                                continue
                            if self.auto._has_entity_conflict(
                                room.id, 'room_id', day, start, end, existing
                            ):
                                continue
                            
                            # Soft constraint: score
                            # (faculty=None placeholder for now)
                            score = self._score_placement(
                                day, start, room, subj, slot['type'],
                                existing, settings, section
                            )
                            
                            candidates.append({
                                'day': day,
                                'start': start,
                                'end': end,
                                'room': room,
                                'score': score,
                                'subject': subj,
                                'schedule_type': slot['type'],
                                'duration': duration
                            })
                
                # Sort best-first
                candidates.sort(key=lambda c: c['score'], reverse=True)
                
                result.append({
                    'subject': subj,
                    'slot': slot,
                    'candidates': candidates
                })
        
        return result
    
    def _backtrack(self, subjects_with_slots, idx, current_solution,
                    current_schedules, section, settings, start_time):
        """Recursive backtracking search with forward checking."""
        import time as time_module
        
        # Timeout check
        if time_module.time() - start_time > self.TIMEOUT_SECONDS:
            return current_solution if current_solution else None
        
        # Base case: all subjects placed
        if idx >= len(subjects_with_slots):
            return current_solution[:]
        
        subject_info = subjects_with_slots[idx]
        backtracks_here = 0
        
        for candidate in subject_info['candidates']:
            # Check conflicts against current state
            if self._conflicts_with_current(candidate, current_schedules, section):
                continue
            
            # Forward check: would this make any future subject impossible?
            if self._forward_check_fails(
                candidate, subjects_with_slots, idx + 1,
                current_schedules, section
            ):
                backtracks_here += 1
                self._total_backtracks += 1
                if (backtracks_here >= self.MAX_BACKTRACKS_PER_SUBJECT or
                    self._total_backtracks >= self.MAX_TOTAL_BACKTRACKS):
                    break
                continue
            
            # Place this candidate
            mock = self._to_mock_schedule(candidate, section)
            current_schedules.append(mock)
            current_solution.append(candidate)
            
            # Recurse
            result = self._backtrack(
                subjects_with_slots, idx + 1, current_solution,
                current_schedules, section, settings, start_time
            )
            
            if result is not None:
                return result
            
            # Backtrack: undo placement
            current_schedules.pop()
            current_solution.pop()
            backtracks_here += 1
            self._total_backtracks += 1
            
            if (backtracks_here >= self.MAX_BACKTRACKS_PER_SUBJECT or
                self._total_backtracks >= self.MAX_TOTAL_BACKTRACKS):
                break
        
        # Could not place this subject — return partial solution
        # (still continue with remaining subjects)
        return self._backtrack(
            subjects_with_slots, idx + 1, current_solution,
            current_schedules, section, settings, start_time
        )
    
    def _forward_check_fails(self, candidate, all_subjects, next_idx,
                              current_schedules, section):
        """Check if placing candidate makes any future subject impossible.
        
        This is the key optimization: if placing Subject A at 8AM Monday
        leaves Subject B with ZERO valid options, skip this placement early.
        """
        mock = self._to_mock_schedule(candidate, section)
        test_schedules = current_schedules + [mock]
        
        for i in range(next_idx, len(all_subjects)):
            future = all_subjects[i]
            has_valid = False
            for fc in future['candidates']:
                if not self._conflicts_with_current(fc, test_schedules, section):
                    has_valid = True
                    break
            if not has_valid:
                return True  # Dead end detected!
        
        return False
    
    def _conflicts_with_current(self, candidate, schedules, section):
        """Check if candidate conflicts with any already-placed schedule."""
        day = candidate['day']
        start = candidate['start']
        end = candidate['end']
        room = candidate['room']
        
        if self.auto._has_section_conflict(
            section.id, day, start, end, schedules
        ):
            return True
        if self.auto._has_entity_conflict(
            room.id, 'room_id', day, start, end, schedules
        ):
            return True
        return False
```

---

## Integration with Existing Code

### Route Changes: `app/routes/schedule.py`

```python
@schedule_bp.route('/auto-generate-preview', methods=['POST'])
@login_required
def auto_generate_preview():
    data = request.get_json()
    section_id = data.get('section_id')
    curriculum_id = data.get('curriculum_id')
    building_id = data.get('preferred_building_id')
    mode = data.get('mode', 'quick')  # NEW: 'quick' or 'smart'
    
    scheduler = AutoScheduler()
    
    if mode == 'smart':
        smart = SmartScheduler(scheduler)
        result = smart.generate_smart_preview(
            section_id, curriculum_id, building_id
        )
    else:
        result = scheduler.generate_batch_preview(
            section_id, curriculum_id, building_id
        )
    
    # Compute SQI for the result (from B1)
    if result.get('success') and result.get('proposed'):
        from app.services.schedule_quality import compute_sqi
        result['sqi'] = compute_sqi(result['proposed'], section_id)
    
    return jsonify(result)
```

### UI: Mode Toggle

```html
<!-- In auto-generate modal -->
<div class="flex items-center gap-2 mb-4">
    <span class="text-xs text-gray-500">Mode:</span>
    <div class="inline-flex rounded-lg border border-gray-200 p-0.5">
        <button id="mode-quick" onclick="setScheduleMode('quick')" 
                class="px-3 py-1 text-xs rounded-md bg-blue-100 text-blue-700 font-medium">
            ⚡ Quick (~3s)
        </button>
        <button id="mode-smart" onclick="setScheduleMode('smart')"
                class="px-3 py-1 text-xs rounded-md text-gray-500 hover:bg-gray-50">
            🧠 Smart (~15s)
        </button>
    </div>
</div>
```

```javascript
let scheduleMode = 'quick';

function setScheduleMode(mode) {
    scheduleMode = mode;
    document.getElementById('mode-quick').className = mode === 'quick' 
        ? 'px-3 py-1 text-xs rounded-md bg-blue-100 text-blue-700 font-medium'
        : 'px-3 py-1 text-xs rounded-md text-gray-500 hover:bg-gray-50';
    document.getElementById('mode-smart').className = mode === 'smart'
        ? 'px-3 py-1 text-xs rounded-md bg-purple-100 text-purple-700 font-medium'
        : 'px-3 py-1 text-xs rounded-md text-gray-500 hover:bg-gray-50';
}

async function generatePreview() {
    const payload = {
        section_id: selectedSection,
        curriculum_id: selectedCurriculum,
        preferred_building_id: selectedBuilding,
        mode: scheduleMode   // NEW
    };
    
    // Show appropriate loading message
    showLoading(scheduleMode === 'smart' 
        ? 'Optimizing schedule (this may take up to 30 seconds)...'
        : 'Generating schedule...'
    );
    
    const response = await fetch('/schedule/auto-generate-preview', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    });
    // ... handle response (unchanged)
}
```

---

## SQI Comparison (Integration with B1)

After both Quick and Smart modes have been tried, show a comparison:

```javascript
// After receiving smart mode result
if (quickResult && smartResult) {
    showSqiComparison(quickResult.sqi, smartResult.sqi);
}

function showSqiComparison(quickSqi, smartSqi) {
    const diff = smartSqi.overall - quickSqi.overall;
    const el = document.getElementById('sqi-comparison');
    el.innerHTML = `
        <div class="flex items-center gap-4 text-xs">
            <span class="text-gray-500">SQI:</span>
            <span class="font-mono">${quickSqi.overall}/100 (Quick)</span>
            <span class="text-green-600 font-semibold">→ ${smartSqi.overall}/100 (Smart)</span>
            <span class="text-green-700 bg-green-50 px-1.5 py-0.5 rounded">+${diff}</span>
        </div>
    `;
}
```

---

## Implementation Steps

### Step 1: Create `SmartScheduler` Class
1. Create `app/services/smart_scheduler.py` with the `SmartScheduler` class
2. Reuse `AutoScheduler`'s data loading, scoring, and conflict checking methods
3. Implement `_build_candidates()`, `_backtrack()`, `_forward_check_fails()`
4. Add timeout safety (30 seconds max)

### Step 2: Add Mode Toggle to Route
1. Accept `mode` parameter in `/auto-generate-preview`
2. Route to `SmartScheduler` when `mode='smart'`
3. Fallback to greedy if backtracking times out or fails

### Step 3: Add Mode Toggle to UI
1. Add Quick/Smart toggle buttons in auto-generate modal
2. Update loading message for Smart mode
3. Show SQI comparison when both results available

### Step 4: Testing
1. Test with small sections (5 subjects) — should find optimal
2. Test with large sections (15+ subjects) — verify timeout works
3. Test with tight rooms (few rooms, many sections) — verify backtracking helps
4. Compare SQI: Smart should be ≥ Quick in all cases

---

## Performance Considerations

| Scenario | Quick Mode | Smart Mode |
|----------|-----------|------------|
| 5 subjects, 10 rooms | <1s | 1-3s |
| 10 subjects, 10 rooms | 1-2s | 5-10s |
| 15 subjects, 5 rooms | 2-3s | 10-20s |
| 20 subjects, 3 rooms | 3-5s | 20-30s (may timeout) |

**Safety mechanisms:**
- Hard timeout: 30 seconds → return best partial solution
- Max backtracks: 50 → stop and return current state
- Per-subject backtrack limit: 3 → move on to next subject
- Graceful fallback: if Smart fails, auto-fallback to Quick

---

## Future Enhancement: OR-Tools CP-SAT

If performance needs to scale beyond backtracking (e.g., scheduling entire department at once), OR-Tools can be introduced as an optional dependency:

```python
# Only imported if available
try:
    from ortools.sat.python import cp_model
    HAS_ORTOOLS = True
except ImportError:
    HAS_ORTOOLS = False
```

This would be a drop-in replacement for the `SmartScheduler._backtrack()` method, using CP-SAT's constraint solver for guaranteed optimal solutions. But for a thesis project with section-level scheduling, the backtracking approach is sufficient.

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `app/services/smart_scheduler.py` | **New file** | SmartScheduler class with backtracking |
| `app/routes/schedule.py` | **Small edit** | Add `mode` parameter to auto-generate route |
| Auto-generate modal template | **Small edit** | Add Quick/Smart toggle buttons |
| Auto-generate JS | **Small edit** | Send `mode` in request, show SQI comparison |

---

## Testing Checklist

- [ ] Quick mode still works exactly as before (no regression)
- [ ] Smart mode produces valid, conflict-free schedules
- [ ] Smart mode SQI ≥ Quick mode SQI for same input
- [ ] Smart mode respects 30-second timeout
- [ ] Smart mode falls back to Quick on timeout/failure
- [ ] Loading indicator shows appropriate message per mode
- [ ] Mode toggle UI works (visual state update)
- [ ] SQI comparison displays when both modes have been tried
- [ ] All "unplaceable" subjects from Quick mode are attempted in Smart mode
- [ ] No faculty/room/section conflicts in Smart mode output
- [ ] Works for sections with 1 subject (trivial case)
- [ ] Works for sections with 15+ subjects (stress test)
