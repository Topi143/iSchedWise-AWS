# Software Engineering Best Practices Guide

## 🎯 Core Engineering Principles

**This guide contains comprehensive software engineering principles for writing clean, maintainable, and scalable code.**

---

## 1️⃣ DRY - Don't Repeat Yourself

**Every piece of knowledge must have a single, unambiguous, authoritative representation.**

### ✅ DO:
```python
# GOOD - Reusable validation function
def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))

# Use everywhere
if validate_email(user_email):
    process_user(user_email)
```

### ❌ DON'T:
```python
# BAD - Same validation logic duplicated
if re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email1):
    process_user(email1)

# Duplicated again elsewhere
if re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email2):
    process_user(email2)
```

### DRY Implementation Strategies:
| Strategy | Use Case |
|----------|----------|
| **Functions/Methods** | Extract common logic into reusable functions |
| **Base Classes/Mixins** | Share behavior across multiple classes |
| **Utility Modules** | Cross-cutting concerns (logging, validation) |
| **Constants** | Replace magic numbers/strings |
| **Template Inheritance** | Reuse HTML layouts |
| **CSS Utility Classes** | Avoid repeated inline styles |
| **Configuration Files** | Environment-specific values |
| **Decorators** | Reusable function wrappers |

### DRY in Practice:
```python
# BEFORE - Repeated code
class UserController:
    def create_user(self, data):
        if not data.get('email'):
            raise ValueError("Email required")
        if not re.match(r'^[\w.-]+@[\w.-]+\.\w+$', data['email']):
            raise ValueError("Invalid email")
        # ... create user

    def update_user(self, user_id, data):
        if not data.get('email'):
            raise ValueError("Email required")
        if not re.match(r'^[\w.-]+@[\w.-]+\.\w+$', data['email']):
            raise ValueError("Invalid email")
        # ... update user

# AFTER - DRY principle applied
class EmailValidator:
    PATTERN = r'^[\w.-]+@[\w.-]+\.\w+$'
    
    @classmethod
    def validate(cls, email: str) -> None:
        if not email:
            raise ValueError("Email required")
        if not re.match(cls.PATTERN, email):
            raise ValueError("Invalid email")

class UserController:
    def create_user(self, data):
        EmailValidator.validate(data.get('email'))
        # ... create user

    def update_user(self, user_id, data):
        EmailValidator.validate(data.get('email'))
        # ... update user
```

---

## 2️⃣ SOLID Principles

### S - Single Responsibility Principle (SRP)
**A class/function should have only ONE reason to change.**

```python
# ✅ GOOD - Each class has one responsibility
class UserValidator:
    """Validates user data - ONLY validation logic"""
    def validate(self, user_data: dict) -> bool:
        return self._validate_email(user_data) and self._validate_name(user_data)
    
    def _validate_email(self, data): pass
    def _validate_name(self, data): pass

class UserRepository:
    """Handles user persistence - ONLY database operations"""
    def save(self, user): pass
    def find_by_id(self, id): pass
    def delete(self, id): pass

class EmailService:
    """Handles email operations - ONLY email logic"""
    def send_welcome(self, user): pass
    def send_reset_password(self, user): pass

class UserService:
    """Orchestrates user operations"""
    def __init__(self, validator, repository, email_service):
        self.validator = validator
        self.repository = repository
        self.email_service = email_service
    
    def register(self, user_data):
        if not self.validator.validate(user_data):
            raise ValidationError()
        user = self.repository.save(user_data)
        self.email_service.send_welcome(user)
        return user
```

```python
# ❌ BAD - One class doing everything (God Object)
class UserManager:
    def validate(self, data): pass      # Validation
    def save(self, user): pass          # Persistence
    def send_email(self, user): pass    # Email
    def generate_report(self): pass     # Reporting
    def export_to_csv(self): pass       # Export
    def authenticate(self): pass        # Auth
```

### O - Open/Closed Principle (OCP)
**Open for extension, closed for modification.**

```python
# ✅ GOOD - Extend without modifying existing code
from abc import ABC, abstractmethod

class PaymentProcessor(ABC):
    @abstractmethod
    def process(self, amount: float) -> bool:
        pass

class CreditCardProcessor(PaymentProcessor):
    def process(self, amount: float) -> bool:
        # Credit card processing logic
        return True

class PayPalProcessor(PaymentProcessor):
    def process(self, amount: float) -> bool:
        # PayPal processing logic
        return True

# Adding new payment method - NO modification to existing code!
class CryptoProcessor(PaymentProcessor):
    def process(self, amount: float) -> bool:
        # Crypto processing logic
        return True

class PaymentService:
    def __init__(self, processor: PaymentProcessor):
        self.processor = processor
    
    def pay(self, amount: float) -> bool:
        return self.processor.process(amount)
```

```python
# ❌ BAD - Requires modification for new payment types
class PaymentService:
    def process(self, payment_type: str, amount: float):
        if payment_type == "credit_card":
            # Credit card logic
            pass
        elif payment_type == "paypal":
            # PayPal logic
            pass
        elif payment_type == "crypto":  # Must modify this class!
            # Crypto logic
            pass
```

### L - Liskov Substitution Principle (LSP)
**Subtypes must be substitutable for their base types.**

```python
# ✅ GOOD - Subclass honors base class contract
class Bird:
    def move(self) -> str:
        pass

class Sparrow(Bird):
    def move(self) -> str:
        return "flying"

class Penguin(Bird):
    def move(self) -> str:
        return "swimming"  # Still moves, different implementation

# Both can be used interchangeably
def make_bird_move(bird: Bird):
    print(bird.move())  # Works with any Bird

make_bird_move(Sparrow())  # "flying"
make_bird_move(Penguin())  # "swimming"
```

```python
# ❌ BAD - Violates LSP
class Bird:
    def fly(self):
        pass

class Penguin(Bird):
    def fly(self):
        raise Exception("Penguins can't fly!")  # Breaks substitution!
```

### I - Interface Segregation Principle (ISP)
**Clients shouldn't depend on interfaces they don't use.**

```python
# ✅ GOOD - Small, focused interfaces
class Readable(ABC):
    @abstractmethod
    def read(self) -> str:
        pass

class Writable(ABC):
    @abstractmethod
    def write(self, data: str) -> None:
        pass

class Deletable(ABC):
    @abstractmethod
    def delete(self) -> None:
        pass

# Implement only what you need
class ReadOnlyFile(Readable):
    def read(self) -> str:
        return "file contents"

class FullAccessFile(Readable, Writable, Deletable):
    def read(self) -> str: pass
    def write(self, data: str) -> None: pass
    def delete(self) -> None: pass
```

```python
# ❌ BAD - Fat interface forces unnecessary implementations
class FileOperations(ABC):
    @abstractmethod
    def read(self): pass
    @abstractmethod
    def write(self, data): pass
    @abstractmethod
    def delete(self): pass
    @abstractmethod
    def compress(self): pass
    @abstractmethod
    def encrypt(self): pass

class SimpleTextFile(FileOperations):
    def read(self): pass
    def write(self, data): pass
    def delete(self): pass
    def compress(self): raise NotImplementedError()  # Don't need this!
    def encrypt(self): raise NotImplementedError()   # Don't need this!
```

### D - Dependency Inversion Principle (DIP)
**Depend on abstractions, not concretions.**

```python
# ✅ GOOD - Depend on abstraction
class MessageSender(ABC):
    @abstractmethod
    def send(self, message: str) -> bool:
        pass

class EmailSender(MessageSender):
    def send(self, message: str) -> bool:
        # Send via email
        return True

class SMSSender(MessageSender):
    def send(self, message: str) -> bool:
        # Send via SMS
        return True

class NotificationService:
    def __init__(self, sender: MessageSender):  # Depends on abstraction
        self.sender = sender
    
    def notify(self, message: str) -> bool:
        return self.sender.send(message)

# Can inject any implementation
email_notifier = NotificationService(EmailSender())
sms_notifier = NotificationService(SMSSender())
```

```python
# ❌ BAD - Depends on concrete implementation
class NotificationService:
    def __init__(self):
        self.sender = EmailSender()  # Hardcoded dependency!
    
    def notify(self, message: str):
        self.sender.send(message)
```

---

## 3️⃣ KISS - Keep It Simple, Stupid

**Simplicity is the ultimate sophistication.**

### ✅ DO:
```python
# GOOD - Simple and readable
def get_adult_users(users: List[User]) -> List[User]:
    return [user for user in users if user.age >= 18]

# GOOD - Clear conditionals
def get_discount(user: User) -> float:
    if user.is_premium:
        return 0.20
    if user.is_member:
        return 0.10
    return 0.0
```

### ❌ DON'T:
```python
# BAD - Overly complex
def get_adult_users(users):
    result = []
    for i in range(len(users)):
        if users[i] is not None:
            if hasattr(users[i], 'age'):
                if users[i].age is not None:
                    if int(users[i].age) >= 18:
                        result.append(users[i])
    return result

# BAD - Clever but unreadable
def get_discount(u):
    return (0.2 if u.p else 0.1 if u.m else 0) * (1 if u.a else 0.5)
```

### KISS Guidelines:
| Guideline | Recommendation |
|-----------|----------------|
| Function length | Under 20-30 lines |
| Function parameters | 3-4 maximum |
| Nesting depth | Maximum 3 levels |
| Cyclomatic complexity | Under 10 |
| Class size | Under 200-300 lines |
| Method count per class | Under 10-15 |

---

## 4️⃣ YAGNI - You Aren't Gonna Need It

**Don't implement something until you actually need it.**

### ✅ DO:
```python
# GOOD - Only what's needed now
class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

class UserService:
    def create_user(self, name: str, email: str) -> User:
        return User(name, email)
```

### ❌ DON'T:
```python
# BAD - Features "we might need someday"
class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email
        self.phone = None           # Might need later
        self.fax = None             # Who uses fax?
        self.pager = None           # Just in case
        self.social_security = None # Future feature
        self.blood_type = None      # You never know
        self.favorite_color = None  # For personalization?
        self.shoe_size = None       # ????

class UserService:
    def create_user(self, name, email): pass
    def import_from_csv(self): pass      # Never asked for
    def export_to_xml(self): pass        # No requirement
    def sync_with_ldap(self): pass       # Might need someday
    def generate_avatar(self): pass      # Cool but unnecessary
```

### YAGNI Exceptions:
When it IS appropriate to plan ahead:
- Security features (authentication, authorization)
- Logging and monitoring
- Database indexes for known query patterns
- API versioning strategy
- Internationalization hooks (if global market is certain)

---

## 5️⃣ Clean Code Principles

### Meaningful Names
```python
# ✅ GOOD - Self-documenting code
def calculate_monthly_salary(employee: Employee, hours_worked: int) -> Decimal:
    hourly_rate = employee.hourly_rate
    overtime_hours = max(0, hours_worked - STANDARD_HOURS)
    overtime_pay = overtime_hours * hourly_rate * OVERTIME_MULTIPLIER
    regular_pay = min(hours_worked, STANDARD_HOURS) * hourly_rate
    return regular_pay + overtime_pay

# ❌ BAD - Cryptic names
def calc(e, h):
    r = e.r
    oh = max(0, h - 160)
    op = oh * r * 1.5
    rp = min(h, 160) * r
    return rp + op
```

### Naming Conventions:
| Element | Convention | Example |
|---------|------------|---------|
| Variables | snake_case, descriptive | `user_count`, `is_active` |
| Functions | snake_case, verb phrase | `calculate_total()`, `get_user()` |
| Classes | PascalCase, noun | `UserService`, `OrderRepository` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| Private | Leading underscore | `_internal_method()`, `_cache` |
| Boolean | is_, has_, can_ prefix | `is_valid`, `has_permission` |

### Functions Should Do One Thing
```python
# ✅ GOOD - Each function has one job
def validate_user(user: User) -> bool:
    """Validate user data."""
    return _validate_email(user.email) and _validate_name(user.name)

def save_user(user: User) -> User:
    """Persist user to database."""
    return user_repository.save(user)

def send_welcome_email(user: User) -> None:
    """Send welcome email to new user."""
    email_service.send_template("welcome", user.email)

def register_user(user_data: dict) -> User:
    """Orchestrate user registration."""
    user = User(**user_data)
    
    if not validate_user(user):
        raise ValidationError("Invalid user data")
    
    saved_user = save_user(user)
    send_welcome_email(saved_user)
    
    return saved_user
```

### Comments: Why, Not What
```python
# ✅ GOOD - Explains WHY
# Using binary search because dataset exceeds 1M records
# and linear search caused 30s+ response times
result = binary_search(sorted_data, target)

# Retry with exponential backoff to handle transient network failures
# per AWS best practices for DynamoDB
for attempt in range(MAX_RETRIES):
    try:
        return dynamodb.get_item(key)
    except TransientError:
        time.sleep(2 ** attempt)

# ❌ BAD - States the obvious
# Increment counter by 1
counter += 1

# Loop through users
for user in users:
    pass

# Check if user is none
if user is None:
    pass
```

### Error Handling
```python
# ✅ GOOD - Specific, informative errors
class UserNotFoundError(Exception):
    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"User with ID {user_id} not found")

class InvalidEmailError(Exception):
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Invalid email format: {email}")

def get_user(user_id: int) -> User:
    user = db.query(User).get(user_id)
    if not user:
        raise UserNotFoundError(user_id)
    return user

def update_email(user_id: int, email: str) -> User:
    if not is_valid_email(email):
        raise InvalidEmailError(email)
    user = get_user(user_id)
    user.email = email
    return user
```

```python
# ❌ BAD - Generic, unhelpful errors
def get_user(user_id):
    try:
        return db.query(User).get(user_id)
    except:
        return None  # Swallows all errors silently

def update_email(user_id, email):
    try:
        user = get_user(user_id)
        user.email = email
    except Exception as e:
        print("Error")  # Useless error handling
```

---

## 6️⃣ Design Patterns

### Factory Pattern
```python
class ScheduleFactory:
    """Creates schedule objects based on type."""
    
    _creators = {}
    
    @classmethod
    def register(cls, schedule_type: str, creator):
        cls._creators[schedule_type] = creator
    
    @classmethod
    def create(cls, schedule_type: str, **kwargs):
        creator = cls._creators.get(schedule_type)
        if not creator:
            raise ValueError(f"Unknown schedule type: {schedule_type}")
        return creator(**kwargs)

# Register creators
ScheduleFactory.register("class", ClassSchedule)
ScheduleFactory.register("exam", ExamSchedule)
ScheduleFactory.register("meeting", MeetingSchedule)

# Usage
class_schedule = ScheduleFactory.create("class", subject="Math", time="9:00")
```

### Strategy Pattern
```python
class ConflictChecker(ABC):
    """Abstract strategy for conflict detection."""
    
    @abstractmethod
    def check(self, schedule: Schedule) -> Optional[Conflict]:
        pass

class RoomConflictChecker(ConflictChecker):
    def check(self, schedule: Schedule) -> Optional[Conflict]:
        existing = Schedule.query.filter_by(
            room_id=schedule.room_id,
            day=schedule.day
        ).all()
        for s in existing:
            if self._times_overlap(schedule, s):
                return Conflict("Room already booked", s)
        return None

class FacultyConflictChecker(ConflictChecker):
    def check(self, schedule: Schedule) -> Optional[Conflict]:
        # Faculty conflict logic
        pass

class ConflictDetector:
    """Detects schedule conflicts using multiple strategies."""
    
    def __init__(self, strategies: List[ConflictChecker] = None):
        self.strategies = strategies or [
            RoomConflictChecker(),
            FacultyConflictChecker(),
            SectionConflictChecker()
        ]
    
    def detect_all(self, schedule: Schedule) -> List[Conflict]:
        conflicts = []
        for strategy in self.strategies:
            conflict = strategy.check(schedule)
            if conflict:
                conflicts.append(conflict)
        return conflicts
```

### Repository Pattern
```python
class UserRepository(ABC):
    """Abstract repository for user persistence."""
    
    @abstractmethod
    def find_by_id(self, id: int) -> Optional[User]: pass
    
    @abstractmethod
    def find_by_email(self, email: str) -> Optional[User]: pass
    
    @abstractmethod
    def find_all(self, filters: dict = None) -> List[User]: pass
    
    @abstractmethod
    def save(self, user: User) -> User: pass
    
    @abstractmethod
    def delete(self, id: int) -> bool: pass

class SQLAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of user repository."""
    
    def __init__(self, session):
        self.session = session
    
    def find_by_id(self, id: int) -> Optional[User]:
        return self.session.query(User).get(id)
    
    def find_by_email(self, email: str) -> Optional[User]:
        return self.session.query(User).filter_by(email=email).first()
    
    def save(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        return user
```

### Service Layer Pattern
```python
class ScheduleService:
    """Orchestrates schedule-related business logic."""
    
    def __init__(
        self,
        repository: ScheduleRepository,
        validator: ScheduleValidator,
        conflict_detector: ConflictDetector,
        notifier: NotificationService
    ):
        self.repository = repository
        self.validator = validator
        self.conflict_detector = conflict_detector
        self.notifier = notifier
    
    def create_schedule(self, data: dict, user: User) -> Result:
        # Validate
        validation_result = self.validator.validate(data)
        if not validation_result.is_valid:
            return Result.failure(validation_result.errors)
        
        # Check conflicts
        schedule = Schedule(**data)
        conflicts = self.conflict_detector.detect_all(schedule)
        if conflicts:
            return Result.failure(conflicts)
        
        # Save
        saved = self.repository.save(schedule)
        
        # Notify
        self.notifier.notify_schedule_created(saved, user)
        
        return Result.success(saved)
```

### Decorator Pattern
```python
def log_execution(func):
    """Decorator to log function execution."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Executing {func.__name__}")
        start = time.time()
        try:
            result = func(*args, **kwargs)
            logger.info(f"Completed {func.__name__} in {time.time() - start:.2f}s")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise
    return wrapper

def require_permission(permission: str):
    """Decorator to check user permission."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.has_permission(permission):
                raise PermissionDenied(permission)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@log_execution
@require_permission("schedule.create")
def create_schedule(data: dict) -> Schedule:
    pass
```

---

## 7️⃣ Code Organization

### Project Structure
```
project/
├── app/
│   ├── __init__.py          # App factory
│   ├── models/              # Data models (one per file)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── schedule.py
│   ├── routes/              # HTTP handlers (thin controllers)
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── schedule.py
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   └── schedule_service.py
│   ├── repositories/        # Data access layer
│   │   ├── __init__.py
│   │   └── user_repository.py
│   ├── validators/          # Input validation
│   │   ├── __init__.py
│   │   └── schedule_validator.py
│   ├── utils/               # Helpers and utilities
│   │   ├── __init__.py
│   │   └── date_utils.py
│   └── templates/           # View templates
│       └── base.html
├── config/                  # Configuration
│   ├── __init__.py
│   └── config.py
├── tests/                   # All tests
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── requirements.txt
└── README.md
```

### Import Organization
```python
# Standard library imports
import os
import sys
from datetime import datetime
from typing import List, Optional

# Third-party imports
from flask import Flask, request, jsonify
from sqlalchemy import Column, Integer, String

# Local application imports
from app.models import User, Schedule
from app.services import UserService
from app.utils import format_date
```

---

## 8️⃣ Database Best Practices

### Query Optimization
```python
# ✅ GOOD - Eager loading prevents N+1
schedules = (
    Schedule.query
    .options(
        db.joinedload(Schedule.faculty),
        db.joinedload(Schedule.room),
        db.joinedload(Schedule.section)
    )
    .filter_by(is_active=True)
    .all()
)

# Now these don't trigger additional queries
for s in schedules:
    print(f"{s.faculty.name} in {s.room.name}")
```

```python
# ❌ BAD - N+1 query problem
schedules = Schedule.query.filter_by(is_active=True).all()

for s in schedules:
    # Each of these triggers a new query!
    print(f"{s.faculty.name} in {s.room.name}")
```

### Transaction Management
```python
# ✅ GOOD - Atomic transaction with proper error handling
def transfer_funds(from_account_id: int, to_account_id: int, amount: Decimal) -> bool:
    try:
        from_account = Account.query.get(from_account_id)
        to_account = Account.query.get(to_account_id)
        
        if from_account.balance < amount:
            raise InsufficientFundsError()
        
        from_account.balance -= amount
        to_account.balance += amount
        
        db.session.commit()
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Transfer failed: {e}")
        raise
```

### Index Strategy
```sql
-- Index foreign keys (always!)
CREATE INDEX idx_schedule_faculty_id ON schedules(faculty_id);
CREATE INDEX idx_schedule_room_id ON schedules(room_id);
CREATE INDEX idx_schedule_section_id ON schedules(section_id);

-- Index frequently queried columns
CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_schedule_is_active ON schedules(is_active);

-- Composite index for common query patterns
CREATE INDEX idx_schedule_day_time ON schedules(day_of_week, start_time);
CREATE INDEX idx_schedule_semester ON schedules(academic_year, semester);

-- Partial index for filtered queries
CREATE INDEX idx_active_schedules ON schedules(faculty_id) WHERE is_active = 1;
```

### Batch Operations
```python
# ✅ GOOD - Batch insert
def bulk_create_users(user_data_list: List[dict]) -> List[User]:
    users = [User(**data) for data in user_data_list]
    db.session.bulk_save_objects(users)
    db.session.commit()
    return users

# ✅ GOOD - Batch update
def deactivate_old_schedules(cutoff_date: date) -> int:
    result = (
        Schedule.query
        .filter(Schedule.end_date < cutoff_date)
        .update({Schedule.is_active: False})
    )
    db.session.commit()
    return result

# ❌ BAD - Individual operations in loop
def bulk_create_users_slow(user_data_list):
    for data in user_data_list:
        user = User(**data)
        db.session.add(user)
        db.session.commit()  # Commit per item is slow!
```

---

## 9️⃣ Security Best Practices

### Input Validation
```python
# ✅ ALWAYS validate and sanitize input
from wtforms import Form, StringField, PasswordField
from wtforms.validators import DataRequired, Email, Length, Regexp

class RegistrationForm(Form):
    email = StringField('Email', validators=[
        DataRequired(message="Email is required"),
        Email(message="Invalid email format"),
        Length(max=255)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required"),
        Length(min=8, message="Password must be at least 8 characters"),
        Regexp(
            r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)',
            message="Password must contain uppercase, lowercase, and number"
        )
    ])
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=50),
        Regexp(r'^[\w]+$', message="Username can only contain letters, numbers, and underscores")
    ])
```

### Authentication & Authorization
```python
# ✅ ALWAYS protect routes
from flask_login import login_required, current_user
from functools import wraps

def role_required(*roles):
    """Decorator to require specific roles."""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/admin/users')
@role_required('Admin')
def admin_users():
    return render_template('admin/users.html')

@app.route('/schedule/create', methods=['POST'])
@login_required
@role_required('Admin', 'Dean')
def create_schedule():
    pass
```

### SQL Injection Prevention
```python
# ✅ GOOD - Parameterized queries (ORM)
user = User.query.filter_by(email=user_email).first()

# ✅ GOOD - Parameterized raw query
result = db.session.execute(
    text("SELECT * FROM users WHERE email = :email"),
    {"email": user_email}
)

# ❌ NEVER - String concatenation
db.session.execute(f"SELECT * FROM users WHERE email = '{user_email}'")
```

### XSS Prevention
```html
<!-- ✅ GOOD - Auto-escaped in Jinja2 -->
<p>Welcome, {{ user.name }}</p>
<input value="{{ form.email.data }}">

<!-- ❌ DANGEROUS - Unescaped (only use when you KNOW it's safe) -->
<div>{{ trusted_html | safe }}</div>
```

### CSRF Protection
```python
# ✅ Enable CSRF protection
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)

# In templates, always include CSRF token
```
```html
<form method="POST">
    {{ form.hidden_tag() }}
    <!-- or -->
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
</form>
```

### Password Handling
```python
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    password_hash = db.Column(db.String(256))
    
    def set_password(self, password: str) -> None:
        """Hash and store password. NEVER store plain text!"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)
```

---

## 🔟 Testing Principles

### Test Structure (AAA Pattern)
```python
def test_user_registration_success():
    # Arrange - Set up test data and conditions
    user_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "password": "SecurePass123"
    }
    service = UserService(mock_repository, mock_email_service)
    
    # Act - Execute the code under test
    result = service.register(user_data)
    
    # Assert - Verify the expected outcome
    assert result.success is True
    assert result.user.name == "John Doe"
    assert result.user.email == "john@example.com"
    mock_email_service.send_welcome.assert_called_once()
```

### Test Categories
```python
# Unit Tests - Test individual functions/methods in isolation
class TestEmailValidator:
    def test_valid_email(self):
        assert EmailValidator.validate("test@example.com") is True
    
    def test_invalid_email_no_at(self):
        assert EmailValidator.validate("testexample.com") is False
    
    def test_empty_email(self):
        with pytest.raises(ValueError):
            EmailValidator.validate("")

# Integration Tests - Test component interactions
class TestUserAPI:
    def test_create_user_endpoint(self, client, db):
        response = client.post('/api/users', json={
            "name": "Test User",
            "email": "test@example.com"
        })
        assert response.status_code == 201
        assert User.query.filter_by(email="test@example.com").first() is not None

# Edge Case Tests
class TestScheduleConflict:
    def test_overlapping_times(self): pass
    def test_adjacent_times_no_conflict(self): pass
    def test_same_start_time(self): pass
    def test_null_end_time(self): pass
```

### Test Coverage Guidelines
| Area | Coverage Target |
|------|-----------------|
| Business logic | 90%+ |
| API endpoints | 80%+ |
| Utility functions | 90%+ |
| Error handling | 80%+ |
| Edge cases | Cover all known |

### What to Test Checklist
- [ ] Happy path (normal expected usage)
- [ ] Edge cases (boundary values, empty inputs)
- [ ] Error scenarios (invalid input, missing data)
- [ ] Authorization (access control)
- [ ] Concurrency (if applicable)
- [ ] Performance (for critical paths)

---

## 1️⃣1️⃣ Performance Guidelines

### Avoid Common Pitfalls
```python
# ✅ GOOD - Generator for large datasets (memory efficient)
def process_large_file(filename: str):
    with open(filename) as f:
        for line in f:
            yield process_line(line)

# Use generator
for processed in process_large_file("huge.csv"):
    save(processed)

# ❌ BAD - Loading everything into memory
def process_large_file_bad(filename: str):
    with open(filename) as f:
        lines = f.readlines()  # Loads entire file!
    return [process_line(line) for line in lines]
```

### Caching
```python
from functools import lru_cache
from flask_caching import Cache

# Function-level caching
@lru_cache(maxsize=128)
def get_expensive_computation(key: str) -> dict:
    """Cache expensive computations."""
    return expensive_database_query(key)

# Application-level caching
cache = Cache(app, config={'CACHE_TYPE': 'redis'})

@cache.memoize(timeout=300)
def get_user_stats(user_id: int) -> dict:
    """Cache for 5 minutes."""
    return calculate_stats(user_id)

# Invalidate cache when data changes
def update_user(user_id: int, data: dict):
    user = save_user(user_id, data)
    cache.delete_memoized(get_user_stats, user_id)
    return user
```

### Pagination
```python
# ✅ GOOD - Paginated results
def get_users(page: int = 1, per_page: int = 20) -> Pagination:
    return User.query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

# Route
@app.route('/users')
def list_users():
    page = request.args.get('page', 1, type=int)
    pagination = get_users(page)
    return render_template('users.html', 
                          users=pagination.items,
                          pagination=pagination)
```

### Async Operations
```python
# For long-running tasks, use background processing
from celery import Celery

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])

@celery.task
def send_bulk_emails(user_ids: List[int], template: str):
    """Process emails in background."""
    for user_id in user_ids:
        user = User.query.get(user_id)
        send_email(user.email, template)

# Trigger async task
@app.route('/send-newsletter', methods=['POST'])
def send_newsletter():
    user_ids = get_subscriber_ids()
    send_bulk_emails.delay(user_ids, 'newsletter')  # .delay() makes it async
    return jsonify({"status": "queued"})
```

---

## 1️⃣2️⃣ Documentation Standards

### Docstrings (Google Style)
```python
def calculate_grade(scores: List[float], weights: List[float]) -> float:
    """Calculate weighted average grade.
    
    Computes the weighted average of scores using provided weights.
    Useful for calculating final grades from multiple assessments.
    
    Args:
        scores: List of individual scores (0-100 scale).
        weights: Corresponding weights for each score. Must sum to 1.0.
    
    Returns:
        Weighted average as a float between 0 and 100.
    
    Raises:
        ValueError: If scores and weights have different lengths.
        ValueError: If weights don't sum to approximately 1.0.
    
    Example:
        >>> calculate_grade([85, 90, 78], [0.3, 0.4, 0.3])
        84.9
        
        >>> calculate_grade([100, 80], [0.5, 0.5])
        90.0
    """
    if len(scores) != len(weights):
        raise ValueError("Scores and weights must have same length")
    
    if not (0.99 <= sum(weights) <= 1.01):
        raise ValueError("Weights must sum to 1.0")
    
    return sum(s * w for s, w in zip(scores, weights))
```

### Class Documentation
```python
class ScheduleService:
    """Service for managing schedule operations.
    
    This service orchestrates all schedule-related business logic,
    including creation, validation, conflict detection, and notifications.
    
    Attributes:
        repository: Repository for schedule persistence.
        validator: Validator for schedule data.
        conflict_detector: Detector for schedule conflicts.
    
    Example:
        >>> service = ScheduleService(repo, validator, detector)
        >>> result = service.create_schedule(data, user)
        >>> if result.success:
        ...     print(f"Created: {result.schedule.id}")
    """
    
    def __init__(self, repository, validator, conflict_detector):
        """Initialize ScheduleService with dependencies.
        
        Args:
            repository: ScheduleRepository instance for data access.
            validator: ScheduleValidator for input validation.
            conflict_detector: ConflictDetector for checking conflicts.
        """
        self.repository = repository
        self.validator = validator
        self.conflict_detector = conflict_detector
```

### API Documentation
```python
@app.route('/api/schedules', methods=['POST'])
def create_schedule():
    """Create a new schedule.
    
    Creates a new schedule entry with conflict validation.
    
    Request Body:
        {
            "subject_id": int,      # Required. ID of the subject.
            "faculty_id": int,      # Required. ID of the faculty.
            "room_id": int,         # Required. ID of the room.
            "day_of_week": str,     # Required. "Monday"-"Saturday".
            "start_time": str,      # Required. Format: "HH:MM".
            "end_time": str,        # Required. Format: "HH:MM".
            "section_id": int       # Required. ID of the section.
        }
    
    Returns:
        201: Schedule created successfully.
            {
                "success": true,
                "schedule_id": int,
                "message": "Schedule created"
            }
        
        400: Validation error or conflict detected.
            {
                "success": false,
                "errors": ["Error message"]
            }
        
        401: Unauthorized.
        403: Forbidden (insufficient permissions).
    """
    pass
```

---

## 1️⃣3️⃣ Git Best Practices

### Commit Message Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types:
| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code change, no new feature or fix |
| `perf` | Performance improvement |
| `test` | Adding tests |
| `chore` | Maintenance tasks |

### Examples:
```bash
# ✅ GOOD - Clear and descriptive
feat(auth): add email verification for registration

Implement email verification flow:
- Send verification email on registration
- Add verification endpoint
- Block login until verified

Closes #123

fix(schedule): resolve race condition in booking

Use database-level locking to prevent double booking
when concurrent requests try to book the same slot.

refactor(user): extract validation to separate service

Move validation logic from UserController to UserValidator
for better separation of concerns and testability.

# ❌ BAD - Vague and unhelpful
fix bug
update code
changes
WIP
asdfasdf
```

### Branch Naming
```bash
feature/user-authentication
feature/schedule-export-pdf
bugfix/schedule-conflict-detection
bugfix/login-redirect-loop
hotfix/security-vulnerability
hotfix/production-crash
refactor/database-queries
refactor/service-layer
docs/api-documentation
test/schedule-service
```

---

## 1️⃣4️⃣ Code Review Checklist

### Before Submitting PR:
- [ ] Code compiles/runs without errors
- [ ] All tests pass
- [ ] New code has tests
- [ ] Documentation updated
- [ ] No debug code left behind
- [ ] Followed coding standards

### Functionality
- [ ] Code works as intended
- [ ] Edge cases handled
- [ ] Error handling implemented
- [ ] No breaking changes (or documented)
- [ ] Backward compatible

### Code Quality
- [ ] DRY principle followed
- [ ] SOLID principles applied
- [ ] Functions are small and focused
- [ ] Names are meaningful
- [ ] No code smells
- [ ] No TODO/FIXME without ticket reference

### Security
- [ ] Input validation present
- [ ] Authentication checked where needed
- [ ] Authorization verified
- [ ] No sensitive data in logs
- [ ] No hardcoded secrets
- [ ] SQL injection prevented
- [ ] XSS prevented

### Performance
- [ ] No N+1 queries
- [ ] Appropriate indexes
- [ ] Large datasets paginated
- [ ] No memory leaks
- [ ] Efficient algorithms

---

## 1️⃣5️⃣ Anti-Patterns to Avoid

### God Object
```python
# ❌ BAD - One class does everything
class ApplicationManager:
    def authenticate_user(self): pass
    def create_schedule(self): pass
    def send_email(self): pass
    def generate_pdf(self): pass
    def process_payment(self): pass
    def manage_inventory(self): pass
    def handle_notifications(self): pass
    # ... 50 more methods
```

### Spaghetti Code
```python
# ❌ BAD - Tangled, deeply nested, hard to follow
def process(data):
    if data:
        if data.get('type'):
            if data['type'] == 'A':
                for item in data.get('items', []):
                    if item:
                        if item.get('status'):
                            if item['status'] == 'active':
                                for sub in item.get('subs', []):
                                    if sub:
                                        # ... 10 more levels deep
```

### Magic Numbers/Strings
```python
# ❌ BAD - What do these mean?
if status == 3:
    discount = price * 0.15
    if days > 30:
        fee = amount * 0.025

# ✅ GOOD - Self-documenting
STATUS_PREMIUM = 3
PREMIUM_DISCOUNT_RATE = 0.15
LATE_PAYMENT_THRESHOLD_DAYS = 30
LATE_FEE_RATE = 0.025

if status == STATUS_PREMIUM:
    discount = price * PREMIUM_DISCOUNT_RATE
    if days > LATE_PAYMENT_THRESHOLD_DAYS:
        fee = amount * LATE_FEE_RATE
```

### Copy-Paste Programming
```python
# ❌ BAD - Same logic repeated
def validate_user_email(email):
    if not email:
        return False
    if '@' not in email:
        return False
    if '.' not in email.split('@')[1]:
        return False
    return True

def validate_contact_email(email):
    if not email:
        return False
    if '@' not in email:
        return False
    if '.' not in email.split('@')[1]:
        return False
    return True

# ✅ GOOD - Reusable function
def validate_email(email: str) -> bool:
    if not email or '@' not in email:
        return False
    domain = email.split('@')[1]
    return '.' in domain
```

### Premature Optimization
```python
# ❌ BAD - Optimizing before measuring
def get_user(user_id):
    # "Optimized" with complex caching before proving it's needed
    cache_key = f"user:{user_id}:v{VERSION}:shard{user_id % 10}"
    user = redis.get(cache_key)
    if not user:
        user = memcached.get(cache_key)
        if not user:
            user = db.query(User).get(user_id)
            memcached.set(cache_key, user, 300)
        redis.set(cache_key, user, 60)
    return pickle.loads(zlib.decompress(user))

# ✅ GOOD - Simple first, optimize when needed
def get_user(user_id):
    return User.query.get(user_id)
```

---

## 📋 Quick Reference Checklist

### Before Writing Code
- [ ] Understand requirements completely
- [ ] Check for existing similar code (DRY)
- [ ] Plan the solution architecture
- [ ] Consider edge cases upfront

### While Writing Code
- [ ] Apply DRY - extract duplicates
- [ ] Apply SOLID principles
- [ ] Keep it simple (KISS)
- [ ] Only build what's needed (YAGNI)
- [ ] Use meaningful names
- [ ] Handle errors gracefully
- [ ] Add comments for "why", not "what"

### After Writing Code
- [ ] Review for code smells
- [ ] Add/update tests
- [ ] Update documentation
- [ ] Verify no breaking changes
- [ ] Check security implications
- [ ] Run linting/formatting
- [ ] Self-review the diff

---

## 🎯 Summary

### The 5 Core Principles

| Principle | Meaning | Action |
|-----------|---------|--------|
| **DRY** | Don't Repeat Yourself | Extract and reuse code |
| **SOLID** | 5 OOP design principles | Design flexible, maintainable classes |
| **KISS** | Keep It Simple | Choose simplicity over cleverness |
| **YAGNI** | You Aren't Gonna Need It | Build only what's required now |
| **Clean Code** | Readable, maintainable code | Names, functions, comments |

### Key Takeaways

1. **Write code for humans first**, computers second
2. **Optimize for readability** and maintainability
3. **Test everything** you build
4. **Document the "why"**, not the "what"
5. **Security is not optional**
6. **Performance matters**, but don't optimize prematurely
7. **Keep learning** and improving

---

*Follow these principles consistently for maintainable, scalable, and robust software.* 🚀
