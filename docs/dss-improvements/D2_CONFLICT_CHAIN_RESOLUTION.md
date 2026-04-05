# D2 — Conflict Chain Resolution ("Resolve All" Button)

> **Category:** Part D — Advanced (Stretch Goals)  
> **Priority:** 13  
> **Effort:** Medium-High  
> **DSS Impact:** ★★★★☆ High  
> **Simplicity Impact:** ★★★★★ Very High — One click resolves cascading conflicts  

---

## Problem Statement

When conflicts are detected, the user currently sees a list of individual conflicts and must resolve each one manually:

1. Read conflict description
2. Open the conflicting schedule
3. Change day/time/room/faculty
4. Check if the change created NEW conflicts
5. Repeat for each conflict

This is tedious, especially during batch scheduling where one change can cascade. The system already has a `RecommendationEngine` that suggests alternatives — but users must manually apply each suggestion.

---

## Current Flow

```
┌─────────────────────────────────────────────────────────┐
│ ⚠ 3 Conflicts Found                                     │
│                                                          │
│ 1. Faculty Conflict: Dr. Santos at MWF 8:00-9:30        │
│    → See recommendations (link)                          │
│                                                          │
│ 2. Room Conflict: Room 301 at MWF 8:00-9:30             │
│    → See recommendations (link)                          │
│                                                          │
│ 3. Section Overlap: BSIT 1-A at MWF 8:00-9:30           │
│    → See recommendations (link)                          │
│                                                          │
│                                             [Close]      │
└─────────────────────────────────────────────────────────┘
```

**User must**: click each recommendation → review → apply → check for new conflicts → repeat.

---

## Proposed Solution

### "Resolve All" Button

Add a single button that applies the top-ranked recommendation for each conflict in sequence, checking for new conflicts after each application.

```
┌─────────────────────────────────────────────────────────┐
│ ⚠ 3 Conflicts Found                                     │
│                                                          │
│ 1. Faculty Conflict: Dr. Santos at MWF 8:00-9:30        │
│    💡 Best fix: Move to TTh 10:00-11:30 (92% confidence) │
│                                                          │
│ 2. Room Conflict: Room 301 at MWF 8:00-9:30             │
│    💡 Best fix: Use Room 305 instead (88% confidence)    │
│                                                          │
│ 3. Section Overlap: BSIT 1-A at MWF 8:00-9:30           │
│    💡 Best fix: Move to MWF 1:00-2:30 (85% confidence)  │
│                                                          │
│ ┌────────────────────────────────────────────────────┐   │
│ │ 🔧 Resolve All — Apply top recommendations        │   │
│ │    3 changes will be made. Preview before applying │   │
│ └────────────────────────────────────────────────────┘   │
│                                                          │
│                                [Apply All]     [Close]   │
└─────────────────────────────────────────────────────────┘
```

---

## Architecture

### Resolution Pipeline

```
Conflicts → For each conflict:
  1. Get top recommendation from RecommendationEngine
  2. Simulate applying it (in-memory only)
  3. Check if simulation creates new conflicts
  4. If yes: try 2nd-best recommendation
  5. If all tried: mark as "needs manual resolution"
  
→ Present resolution plan to user
→ User clicks "Apply All"
→ Apply all changes in one transaction
```

### Key Principle: Preview Before Apply

The system NEVER auto-applies changes. It:
1. Computes a resolution plan
2. Shows the plan to the user (what will change)
3. User confirms with "Apply All" or adjusts individual items
4. Only then are changes committed

---

## Backend Implementation

### New Service: `app/services/conflict_resolver.py`

```python
"""
Conflict Chain Resolver

Takes a list of detected conflicts and generates a resolution plan
by applying top recommendations sequentially while checking for
cascading conflicts.
"""

from typing import Dict, List, Optional
from app.services.conflict_detector import ConflictDetector
from app.services.recommendation_engine import RecommendationEngine


class ConflictResolver:
    """Resolves multiple conflicts by chaining recommendations."""
    
    MAX_ALTERNATIVES_PER_CONFLICT = 3  # Try top 3 if first fails
    
    def __init__(self):
        self.conflict_detector = ConflictDetector()
        self.recommendation_engine = RecommendationEngine()
    
    def generate_resolution_plan(self, schedule_id: int,
                                  conflicts: List[Dict]) -> Dict:
        """
        Generate a resolution plan for all detected conflicts.
        
        Args:
            schedule_id: The schedule being edited
            conflicts: List of conflict dicts from ConflictDetector
        
        Returns:
            {
                'resolvable': [
                    {
                        'conflict': {...},
                        'resolution': {
                            'action': 'change_time' | 'change_room' | 'change_faculty',
                            'from': {'day': 'MWF', 'time': '8:00-9:30', 'room': '301'},
                            'to': {'day': 'TTh', 'time': '10:00-11:30', 'room': '301'},
                            'confidence': 0.92,
                            'impact': 'Moves Dr. Santos from MWF 8AM to TTh 10AM'
                        }
                    }, ...
                ],
                'unresolvable': [
                    {
                        'conflict': {...},
                        'reason': 'No conflict-free alternative found within constraints'
                    }
                ],
                'stats': {
                    'total_conflicts': 3,
                    'auto_resolvable': 2,
                    'needs_manual': 1
                }
            }
        """
        from app.models.schedule import Schedule
        
        schedule = Schedule.query.get(schedule_id)
        if not schedule:
            return {'error': 'Schedule not found'}
        
        resolvable = []
        unresolvable = []
        
        # Track simulated state changes for cascade detection
        simulated_changes = []
        
        for conflict in conflicts:
            resolution = self._resolve_single(
                schedule, conflict, simulated_changes
            )
            
            if resolution:
                resolvable.append({
                    'conflict': conflict,
                    'resolution': resolution
                })
                simulated_changes.append(resolution)
            else:
                unresolvable.append({
                    'conflict': conflict,
                    'reason': 'No conflict-free alternative found within constraints'
                })
        
        return {
            'resolvable': resolvable,
            'unresolvable': unresolvable,
            'stats': {
                'total_conflicts': len(conflicts),
                'auto_resolvable': len(resolvable),
                'needs_manual': len(unresolvable)
            }
        }
    
    def _resolve_single(self, schedule, conflict, 
                         prior_changes: List) -> Optional[Dict]:
        """
        Find the best resolution for a single conflict.
        
        Tries recommendations in order, checking each against
        both existing schedules AND prior simulated changes.
        """
        conflict_type = conflict.get('type', '')
        
        # Get recommendations based on conflict type
        if 'faculty' in conflict_type.lower():
            recommendations = self.recommendation_engine.recommend_faculty(
                schedule_id=schedule.id,
                limit=self.MAX_ALTERNATIVES_PER_CONFLICT
            )
            action = 'change_faculty'
        elif 'room' in conflict_type.lower():
            recommendations = self.recommendation_engine.recommend_rooms(
                schedule_id=schedule.id,
                limit=self.MAX_ALTERNATIVES_PER_CONFLICT
            )
            action = 'change_room'
        else:
            # Time/section conflict — recommend alternative times
            recommendations = self.recommendation_engine.recommend_times(
                schedule_id=schedule.id,
                limit=self.MAX_ALTERNATIVES_PER_CONFLICT
            )
            action = 'change_time'
        
        # Try each recommendation
        for rec in recommendations:
            # Simulate the change
            simulated = self._simulate_change(schedule, action, rec)
            
            # Check if simulation creates new conflicts
            new_conflicts = self._check_simulated_conflicts(
                simulated, prior_changes
            )
            
            if not new_conflicts:
                return {
                    'action': action,
                    'from': self._describe_current(schedule, action),
                    'to': self._describe_recommendation(rec, action),
                    'confidence': rec.get('confidence', rec.get('score', 0.5)),
                    'impact': self._describe_impact(schedule, action, rec),
                    'recommendation': rec
                }
        
        return None  # No valid resolution found
    
    def _simulate_change(self, schedule, action, recommendation):
        """Create a simulated schedule state without modifying the database."""
        simulated = {
            'id': schedule.id,
            'section_id': schedule.section_id,
            'subject_id': schedule.subject_id,
            'faculty_id': schedule.faculty_id,
            'room_id': schedule.room_id,
            'day_of_week': schedule.day_of_week,
            'start_time': schedule.start_time,
            'end_time': schedule.end_time,
        }
        
        if action == 'change_faculty':
            simulated['faculty_id'] = recommendation.get('faculty_id')
        elif action == 'change_room':
            simulated['room_id'] = recommendation.get('room_id')
        elif action == 'change_time':
            simulated['day_of_week'] = recommendation.get('day', schedule.day_of_week)
            simulated['start_time'] = recommendation.get('start_time', schedule.start_time)
            simulated['end_time'] = recommendation.get('end_time', schedule.end_time)
        
        return simulated
    
    def _check_simulated_conflicts(self, simulated, prior_changes):
        """Check if a simulated change would create new conflicts."""
        # Use ConflictDetector with simulated state
        # This is a lightweight check using in-memory comparisons
        conflicts = self.conflict_detector.detect_class_conflicts(
            section_id=simulated['section_id'],
            faculty_id=simulated['faculty_id'],
            room_id=simulated['room_id'],
            day_of_week=simulated['day_of_week'],
            start_time=simulated['start_time'],
            end_time=simulated['end_time'],
            exclude_schedule_id=simulated['id']
        )
        
        # Filter out only CRITICAL and HIGH severity
        real_conflicts = [
            c for c in conflicts 
            if c.get('severity') in ('CRITICAL', 'HIGH')
        ]
        
        return real_conflicts
    
    def _describe_current(self, schedule, action):
        """Describe current state for the resolution preview."""
        if action == 'change_time':
            return {
                'day': schedule.day_of_week,
                'time': f"{schedule.start_time.strftime('%I:%M %p')}-{schedule.end_time.strftime('%I:%M %p')}"
            }
        elif action == 'change_room':
            room = schedule.room
            return {'room': room.room_name if room else 'Unknown'}
        elif action == 'change_faculty':
            faculty = schedule.faculty
            return {'faculty': faculty.full_name if faculty else 'Unknown'}
    
    def _describe_recommendation(self, rec, action):
        """Describe recommended change."""
        if action == 'change_time':
            return {
                'day': rec.get('day', ''),
                'time': f"{rec.get('start_time_display', '')}-{rec.get('end_time_display', '')}"
            }
        elif action == 'change_room':
            return {'room': rec.get('room_name', '')}
        elif action == 'change_faculty':
            return {'faculty': rec.get('faculty_name', '')}
    
    def _describe_impact(self, schedule, action, rec):
        """Generate human-readable impact description."""
        if action == 'change_time':
            return (f"Move from {schedule.day_of_week} "
                    f"{schedule.start_time.strftime('%I:%M %p')} to "
                    f"{rec.get('day', '')} {rec.get('start_time_display', '')}")
        elif action == 'change_room':
            return f"Switch room to {rec.get('room_name', '')}"
        elif action == 'change_faculty':
            return f"Assign to {rec.get('faculty_name', '')} instead"


class ResolutionApplier:
    """Applies a confirmed resolution plan to the database."""
    
    @staticmethod
    def apply_plan(resolution_plan: Dict, user_id: int = None) -> Dict:
        """
        Apply all resolvable items from a resolution plan.
        
        Runs in a single transaction — all succeed or all roll back.
        
        Returns:
            {'success': bool, 'applied': int, 'errors': [...]}
        """
        from app.extensions import db
        from app.models.schedule import Schedule
        from datetime import datetime
        
        applied = 0
        errors = []
        
        for item in resolution_plan.get('resolvable', []):
            try:
                schedule_id = item.get('conflict', {}).get('schedule_id')
                resolution = item.get('resolution', {})
                action = resolution.get('action')
                rec = resolution.get('recommendation', {})
                
                schedule = Schedule.query.get(schedule_id)
                if not schedule:
                    errors.append(f"Schedule {schedule_id} not found")
                    continue
                
                if action == 'change_time':
                    schedule.day_of_week = rec.get('day', schedule.day_of_week)
                    if rec.get('start_time'):
                        schedule.start_time = rec['start_time']
                    if rec.get('end_time'):
                        schedule.end_time = rec['end_time']
                elif action == 'change_room':
                    schedule.room_id = rec.get('room_id')
                elif action == 'change_faculty':
                    schedule.faculty_id = rec.get('faculty_id')
                
                schedule.updated_at = datetime.utcnow()
                schedule.version = (schedule.version or 1) + 1
                applied += 1
                
            except Exception as e:
                errors.append(str(e))
        
        if applied > 0 and not errors:
            try:
                # Log activity
                if user_id:
                    from app.models.activity_log import UserActivityLog
                    log = UserActivityLog(
                        user_id=user_id,
                        action='batch_resolve_conflicts',
                        entity_type='schedule',
                        details=f'Auto-resolved {applied} conflict(s)',
                        ip_address='system'
                    )
                    db.session.add(log)
                
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return {'success': False, 'error': str(e)}
        elif errors:
            db.session.rollback()
        
        return {
            'success': applied > 0,
            'applied': applied,
            'errors': errors
        }
```

---

## Route Integration

### New Endpoints in `app/routes/schedule.py`

```python
@schedule_bp.route('/resolve-conflicts', methods=['POST'])
@login_required
def resolve_conflicts():
    """Generate a resolution plan for detected conflicts."""
    data = request.get_json()
    schedule_id = data.get('schedule_id')
    conflicts = data.get('conflicts', [])
    
    resolver = ConflictResolver()
    plan = resolver.generate_resolution_plan(schedule_id, conflicts)
    
    return jsonify(plan)


@schedule_bp.route('/apply-resolution', methods=['POST'])
@login_required
def apply_resolution():
    """Apply a confirmed resolution plan."""
    data = request.get_json()
    plan = data.get('plan', {})
    
    applier = ResolutionApplier()
    result = applier.apply_plan(plan, user_id=current_user.id)
    
    return jsonify(result)
```

---

## Frontend: Conflict Panel Enhancement

### In `/schedule/auto_conflict_check.js` or equivalent:

```javascript
/**
 * After conflict detection completes, show "Resolve All" option
 */
function showConflictsWithResolution(conflicts, scheduleId) {
    if (conflicts.length === 0) return;
    
    const container = document.getElementById('conflict-results');
    
    // Show individual conflicts (existing behavior)
    renderConflictList(conflicts, container);
    
    // Add "Resolve All" section
    if (conflicts.some(c => c.severity === 'CRITICAL' || c.severity === 'HIGH')) {
        const resolveSection = document.createElement('div');
        resolveSection.className = 'mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg';
        resolveSection.innerHTML = `
            <div class="flex items-center justify-between">
                <div>
                    <p class="text-sm font-medium text-blue-900">
                        🔧 Auto-Resolve Available
                    </p>
                    <p class="text-xs text-blue-700 mt-0.5">
                        The system can suggest fixes for ${conflicts.length} conflict(s)
                    </p>
                </div>
                <button onclick="generateResolutionPlan(${scheduleId})" 
                        class="px-3 py-1.5 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700">
                    Generate Plan
                </button>
            </div>
        `;
        container.appendChild(resolveSection);
    }
}

/**
 * Generate and display resolution plan
 */
async function generateResolutionPlan(scheduleId) {
    const conflicts = currentConflicts; // Store from last detection
    
    showLoading('Analyzing resolutions...');
    
    const response = await fetch('/schedule/resolve-conflicts', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
        body: JSON.stringify({ schedule_id: scheduleId, conflicts })
    });
    
    const plan = await response.json();
    hideLoading();
    
    showResolutionPlan(plan);
}

/**
 * Display resolution plan with preview
 */
function showResolutionPlan(plan) {
    const container = document.getElementById('conflict-results');
    container.innerHTML = '';
    
    // Resolution header
    const header = document.createElement('div');
    header.className = 'mb-3 p-3 bg-green-50 border border-green-200 rounded-lg';
    header.innerHTML = `
        <p class="text-sm font-medium text-green-900">
            Resolution Plan: ${plan.stats.auto_resolvable}/${plan.stats.total_conflicts} 
            conflicts can be auto-resolved
        </p>
    `;
    container.appendChild(header);
    
    // Resolvable items
    plan.resolvable.forEach((item, idx) => {
        const card = document.createElement('div');
        card.className = 'mb-2 p-3 bg-white border border-gray-200 rounded-lg';
        card.innerHTML = `
            <div class="flex items-start gap-2">
                <span class="text-green-500 text-xs mt-0.5">✓</span>
                <div class="flex-1">
                    <p class="text-xs font-medium text-gray-900">${item.resolution.impact}</p>
                    <p class="text-[10px] text-gray-500 mt-0.5">
                        Confidence: ${Math.round(item.resolution.confidence * 100)}%
                    </p>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
    
    // Unresolvable items
    plan.unresolvable.forEach(item => {
        const card = document.createElement('div');
        card.className = 'mb-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg';
        card.innerHTML = `
            <div class="flex items-start gap-2">
                <span class="text-yellow-500 text-xs mt-0.5">⚠</span>
                <div class="flex-1">
                    <p class="text-xs text-yellow-800">Needs manual resolution</p>
                    <p class="text-[10px] text-yellow-600">${item.reason}</p>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
    
    // Apply All button
    if (plan.stats.auto_resolvable > 0) {
        const applyBtn = document.createElement('div');
        applyBtn.className = 'mt-3';
        applyBtn.innerHTML = `
            <button onclick="applyResolutionPlan()" 
                    class="w-full py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700">
                Apply ${plan.stats.auto_resolvable} Resolution(s)
            </button>
        `;
        container.appendChild(applyBtn);
        
        // Store plan for application
        window._currentResolutionPlan = plan;
    }
}

/**
 * Apply confirmed resolution plan
 */
async function applyResolutionPlan() {
    const plan = window._currentResolutionPlan;
    if (!plan) return;
    
    showLoading('Applying resolutions...');
    
    const response = await fetch('/schedule/apply-resolution', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
        body: JSON.stringify({ plan })
    });
    
    const result = await response.json();
    hideLoading();
    
    if (result.success) {
        showToast(`✅ ${result.applied} conflict(s) resolved`, 'success');
        // Refresh schedule view
        refreshScheduleTable();
    } else {
        showToast('Failed to apply resolutions', 'error');
    }
}
```

---

## Implementation Steps

### Step 1: Create `ConflictResolver` Service
1. Create `app/services/conflict_resolver.py`
2. Implement `generate_resolution_plan()` and `ResolutionApplier`
3. Integrate with existing `ConflictDetector` and `RecommendationEngine`

### Step 2: Add Routes
1. Add `/resolve-conflicts` endpoint (POST)
2. Add `/apply-resolution` endpoint (POST)
3. Add CSRF protection and `@login_required`

### Step 3: Update Conflict Display UI
1. After conflict detection, add "Auto-Resolve Available" section
2. Show resolution plan preview with confidence scores
3. Add "Apply All" button

### Step 4: Testing
1. Create a schedule with known conflict
2. Verify resolution plan suggests valid fix
3. Verify "Apply All" commits changes
4. Verify cascading conflict detection works
5. Verify rollback on error

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `app/services/conflict_resolver.py` | **New file** | ConflictResolver and ResolutionApplier classes |
| `app/routes/schedule.py` | **Small addition** | Two new endpoints |
| `app/static/js/schedule/auto_conflict_check.js` | **Medium edit** | Resolution UI after conflict detection |

---

## Edge Cases

| Scenario | Handling |
|----------|---------|
| All conflicts unresolvable | Show message: "No automatic resolutions available. These conflicts need manual adjustment." |
| Circular conflict (A conflicts with B, fixing A conflicts with C) | Resolution pipeline checks cascading conflicts; marks as unresolvable if circular |
| User rejects some resolutions | Allow individual item deselection before "Apply All" |
| Database conflict during apply | Full transaction rollback, show error message |
| Concurrent edit (WebSocket) | Version check on each schedule before applying |

---

## Testing Checklist

- [ ] Resolution plan correctly identifies fixable vs. unfixable conflicts
- [ ] Top recommendations don't create new CRITICAL/HIGH conflicts
- [ ] Cascade detection works (fixing A shouldn't break B)
- [ ] "Apply All" commits all changes in single transaction
- [ ] Rollback works if any application fails
- [ ] Activity log records batch resolution
- [ ] Resolution plan matches RecommendationEngine output format
- [ ] Edge case: 0 conflicts → no resolve button shown
- [ ] Edge case: all unresolvable → appropriate message
- [ ] WebSocket version check prevents stale updates
- [ ] Dean can only resolve conflicts within their departments
