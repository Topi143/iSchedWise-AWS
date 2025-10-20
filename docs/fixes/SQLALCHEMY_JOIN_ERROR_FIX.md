# SQLAlchemy Join Error Fix

## Error
```
sqlalchemy.exc.ArgumentError: Join target, typically a FROM expression, or ORM relationship attribute expected, got 'year_level'.
```

## Cause
The error occurred when using string-based joins in SQLAlchemy queries:

```python
# INCORRECT - String joins don't work properly
Subject.query.join(Subject.semester)\
    .join('year_level')\  # ❌ String reference fails
    .join('curriculum')\
    .filter(...)
```

SQLAlchemy couldn't resolve the string `'year_level'` to the proper ORM relationship.

## Solution
Import the actual model classes and use explicit joins:

```python
# CORRECT - Use actual model classes
from app.models.curriculum import Semester, YearLevel

db.session.query(Subject)\
    .join(Semester)\        # ✅ Direct model reference
    .join(YearLevel)\       # ✅ Direct model reference  
    .join(Curriculum)\
    .filter(...)
```

## Files Fixed

### 1. `app/routes/main.py`

**Before:**
```python
subject_count = Subject.query.join(Subject.semester)\
    .join('year_level')\
    .join('curriculum')\
    .filter(Curriculum.department_id.in_(user_department_ids) if user_department_ids else True)\
    .count()
```

**After:**
```python
# Subject count - handle filtering differently
if user_department_ids is None:
    subject_count = Subject.query.count()
else:
    from app.models.curriculum import Semester, YearLevel
    subject_count = db.session.query(Subject).join(Semester).join(YearLevel).join(Curriculum)\
        .filter(Curriculum.department_id.in_(user_department_ids))\
        .count()
```

### 2. `app/routes/reports.py`

**Before:**
```python
stats['total_subjects'] = Subject.query.join(Subject.semester)\
    .join('year_level')\
    .join('curriculum')\
    .filter(Curriculum.department_id.in_(user_department_ids))\
    .count()
```

**After:**
```python
# Import required models for proper joins
from app.models.curriculum import Semester, YearLevel
stats['total_subjects'] = db.session.query(Subject).join(Semester).join(YearLevel).join(Curriculum)\
    .filter(Curriculum.department_id.in_(user_department_ids))\
    .count()
```

## Key Takeaways

1. **Avoid String-Based Joins**: Always import and use actual model classes
2. **Explicit is Better**: Direct model references are clearer and less error-prone
3. **Use db.session.query()**: When doing complex joins, use the session query API
4. **Import at Function Level**: Import models within functions when needed to avoid circular imports

## Testing
✅ Application now starts without errors
✅ Dashboard loads successfully
✅ Subject counts work correctly for both admin and dean users

## Related
- Part of department-based access control implementation
- Fixes subject counting when filtering by department access
