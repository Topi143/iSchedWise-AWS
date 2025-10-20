# Database Change Workflow - Quick Reference

## 🎯 The Golden Rule

**ALWAYS update `database.sql` first, then `sample_data.sql`, then Python models!**

---

## 📋 Step-by-Step Workflow

### 1️⃣ Update `database.sql`

```sql
-- Add this in the appropriate section of database.sql
-- Use IF NOT EXISTS to avoid errors on re-import

-- Example: Adding a new table
CREATE TABLE IF NOT EXISTS `new_feature` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(100) NOT NULL,
  `description` TEXT,
  `department_id` INT(11) NULL,
  `is_active` TINYINT(1) DEFAULT 1,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `department_id` (`department_id`),
  CONSTRAINT `new_feature_ibfk_1` FOREIGN KEY (`department_id`) 
    REFERENCES `departments` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Example: Adding a column
ALTER TABLE `existing_table` 
ADD COLUMN `new_column` VARCHAR(50) NULL AFTER `id`;

-- Example: Adding an index
ALTER TABLE `existing_table` 
ADD KEY `idx_new_column` (`new_column`);

-- Example: Adding a foreign key
ALTER TABLE `existing_table`
ADD CONSTRAINT `fk_related_table`
FOREIGN KEY (`related_id`) REFERENCES `related_table` (`id`)
ON DELETE CASCADE;
```

### 2️⃣ Update `sample_data.sql`

```sql
-- Add sample data for new tables/columns
-- Always check foreign key references are valid

-- Delete old data if structure changed
DELETE FROM `new_feature`;
ALTER TABLE `new_feature` AUTO_INCREMENT = 1;

-- Insert new sample data
INSERT INTO `new_feature` (`name`, `description`, `department_id`, `is_active`) VALUES
('Sample Item 1', 'Description for item 1', 1, 1),
('Sample Item 2', 'Description for item 2', 1, 1),
('Sample Item 3', 'Description for item 3', 2, 1);

-- Update existing data if needed
UPDATE `existing_table` SET `new_column` = 'default_value' WHERE `id` = 1;
```

### 3️⃣ Update Python Models

```python
# In app/models/new_feature.py (create new file if needed)
from app.extensions import db

class NewFeature(db.Model):
    """Description of what this model represents"""
    
    __tablename__ = 'new_feature'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='SET NULL'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    
    # Relationships
    department = db.relationship('Department', backref='new_features')
    
    def __repr__(self):
        return f'<NewFeature {self.name}>'
```

```python
# Update app/models/__init__.py
from app.models.new_feature import NewFeature

__all__ = [
    # ... existing models
    'NewFeature',  # Add this
]
```

### 4️⃣ Test the Changes

```bash
# In phpMyAdmin:
# 1. Drop database: ischedwise_db
# 2. Create database: ischedwise_db
# 3. Import: database.sql
# 4. Import: sample_data.sql

# Run the application
python run.py

# Test:
# - Navigate to affected pages
# - Create/edit/delete records
# - Check for errors in console
```

---

## 🔧 Common Operations

### Adding a New Table

```sql
-- 1. In database.sql
CREATE TABLE IF NOT EXISTS `table_name` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `field_name` VARCHAR(100) NOT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. In sample_data.sql
INSERT INTO `table_name` (`field_name`) VALUES
('Sample 1'),
('Sample 2');

-- 3. In Python (app/models/table_name.py)
class TableName(db.Model):
    __tablename__ = 'table_name'
    id = db.Column(db.Integer, primary_key=True)
    field_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
```

### Adding a Column to Existing Table

```sql
-- 1. In database.sql (modify CREATE TABLE statement)
CREATE TABLE IF NOT EXISTS `existing_table` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `existing_field` VARCHAR(100) NOT NULL,
  `new_field` VARCHAR(50) NULL,  -- Add this line
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. In sample_data.sql (update INSERT statements)
INSERT INTO `existing_table` (`existing_field`, `new_field`) VALUES
('Value 1', 'New Value 1'),
('Value 2', 'New Value 2');

-- 3. In Python (update model)
class ExistingTable(db.Model):
    __tablename__ = 'existing_table'
    id = db.Column(db.Integer, primary_key=True)
    existing_field = db.Column(db.String(100), nullable=False)
    new_field = db.Column(db.String(50))  # Add this
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
```

### Adding a Foreign Key Relationship

```sql
-- 1. In database.sql (modify CREATE TABLE)
CREATE TABLE IF NOT EXISTS `child_table` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `parent_id` INT(11) NOT NULL,  -- Add foreign key field
  `name` VARCHAR(100) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `parent_id` (`parent_id`),  -- Add index
  CONSTRAINT `child_table_ibfk_1` FOREIGN KEY (`parent_id`) 
    REFERENCES `parent_table` (`id`) ON DELETE CASCADE  -- Add constraint
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. In sample_data.sql (ensure valid parent_id references)
INSERT INTO `child_table` (`parent_id`, `name`) VALUES
(1, 'Child 1'),  -- parent_id 1 must exist in parent_table
(1, 'Child 2'),
(2, 'Child 3');

-- 3. In Python (add relationship)
class ChildTable(db.Model):
    __tablename__ = 'child_table'
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('parent_table.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    
    # Add relationship
    parent = db.relationship('ParentTable', backref='children')
```

### Modifying Column Type/Constraints

```sql
-- 1. In database.sql (modify the CREATE TABLE definition)
CREATE TABLE IF NOT EXISTS `table_name` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `field_name` TEXT NOT NULL,  -- Changed from VARCHAR(100) to TEXT
  `status` VARCHAR(20) DEFAULT 'active',  -- Changed default value
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. In sample_data.sql (update data if needed)
INSERT INTO `table_name` (`field_name`, `status`) VALUES
('Longer text that requires TEXT field', 'active'),
('Another long description', 'inactive');

-- 3. In Python (update model)
class TableName(db.Model):
    __tablename__ = 'table_name'
    id = db.Column(db.Integer, primary_key=True)
    field_name = db.Column(db.Text, nullable=False)  # Changed from String
    status = db.Column(db.String(20), default='active')  # Changed default
```

---

## ⚠️ Important Notes

### DO:
- ✅ Always backup database before making changes
- ✅ Use `IF NOT EXISTS` when creating tables
- ✅ Match Python model field names to database column names
- ✅ Test by re-importing database.sql after changes
- ✅ Keep sample_data.sql synchronized with schema
- ✅ Document changes with SQL comments
- ✅ Use proper foreign key constraints with ON DELETE behavior

### DON'T:
- ❌ Don't use `flask db migrate` or Alembic
- ❌ Don't modify database through ORM/migrations folder
- ❌ Don't forget to update sample_data.sql
- ❌ Don't leave orphaned foreign key references
- ❌ Don't change schema without updating Python models
- ❌ Don't test without re-importing SQL files

---

## 🎯 Quick Checklist

Before committing database changes:

- [ ] Updated CREATE TABLE in `database.sql`
- [ ] Updated INSERT statements in `sample_data.sql`
- [ ] Created/updated Python model in `app/models/`
- [ ] Added model to `app/models/__init__.py` exports
- [ ] Dropped and recreated database
- [ ] Imported `database.sql` successfully
- [ ] Imported `sample_data.sql` successfully
- [ ] Application starts without errors
- [ ] Can view/create/edit/delete records
- [ ] Foreign key relationships work correctly
- [ ] No console errors

---

## 📚 Reference: Common Data Types

### MySQL → SQLAlchemy Mapping

| MySQL Type | SQLAlchemy Type | Example |
|------------|----------------|---------|
| `INT(11)` | `db.Integer` | `id = db.Column(db.Integer)` |
| `VARCHAR(100)` | `db.String(100)` | `name = db.Column(db.String(100))` |
| `TEXT` | `db.Text` | `description = db.Column(db.Text)` |
| `DECIMAL(10,2)` | `db.Numeric(10,2)` | `price = db.Column(db.Numeric(10,2))` |
| `DATETIME` | `db.DateTime` | `created_at = db.Column(db.DateTime)` |
| `TINYINT(1)` | `db.Boolean` | `is_active = db.Column(db.Boolean)` |
| `DATE` | `db.Date` | `birth_date = db.Column(db.Date)` |
| `TIME` | `db.Time` | `start_time = db.Column(db.Time)` |

---

## 🔗 Related Documentation

- Main instructions: `.github/copilot-instructions.md`
- Migration guide: `MIGRATION_GUIDE.md`
- Database schema: `database.sql`
- Sample data: `sample_data.sql`
