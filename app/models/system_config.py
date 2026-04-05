"""
SystemConfig model - key-value system configuration store
"""
from datetime import datetime
from app.extensions import db


class SystemConfig(db.Model):
    """Key-value store for system-wide configuration settings"""
    __tablename__ = 'system_config'

    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(100), unique=True, nullable=False)
    config_value = db.Column(db.Text, nullable=True)
    config_type = db.Column(db.Enum('string', 'integer', 'boolean', 'json'), nullable=False, default='string')
    category = db.Column(db.String(50), nullable=False, default='general')
    description = db.Column(db.String(255), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)

    # Relationships
    updater = db.relationship('User', foreign_keys=[updated_by])

    @classmethod
    def get(cls, key, default=None):
        """Get a config value by key, with type conversion"""
        config = cls.query.filter_by(config_key=key).first()
        if not config or config.config_value is None:
            return default

        # Type conversion
        if config.config_type == 'integer':
            try:
                return int(config.config_value)
            except (ValueError, TypeError):
                return default
        elif config.config_type == 'boolean':
            return config.config_value.lower() in ('true', '1', 'yes')
        elif config.config_type == 'json':
            import json
            try:
                return json.loads(config.config_value)
            except (ValueError, TypeError):
                return default
        else:
            return config.config_value

    @classmethod
    def set(cls, key, value, user_id=None):
        """Set a config value by key"""
        config = cls.query.filter_by(config_key=key).first()
        if config:
            # Convert value to string for storage
            if isinstance(value, bool):
                config.config_value = 'true' if value else 'false'
            elif isinstance(value, dict) or isinstance(value, list):
                import json
                config.config_value = json.dumps(value)
            else:
                config.config_value = str(value)
            config.updated_by = user_id
            config.updated_at = datetime.utcnow()
        else:
            # Auto-detect type
            if isinstance(value, bool):
                config_type = 'boolean'
                str_value = 'true' if value else 'false'
            elif isinstance(value, int):
                config_type = 'integer'
                str_value = str(value)
            elif isinstance(value, (dict, list)):
                import json
                config_type = 'json'
                str_value = json.dumps(value)
            else:
                config_type = 'string'
                str_value = str(value)

            config = cls(
                config_key=key,
                config_value=str_value,
                config_type=config_type,
                updated_by=user_id
            )
            db.session.add(config)
        return config

    @classmethod
    def get_by_category(cls, category):
        """Get all configs in a category as a dict"""
        configs = cls.query.filter_by(category=category).order_by(cls.config_key).all()
        return {c.config_key: c for c in configs}

    @classmethod
    def get_all_grouped(cls):
        """Get all configs grouped by category"""
        configs = cls.query.order_by(cls.category, cls.config_key).all()
        grouped = {}
        for config in configs:
            if config.category not in grouped:
                grouped[config.category] = []
            grouped[config.category].append(config)
        return grouped

    @property
    def typed_value(self):
        """Get the value with proper type conversion"""
        return SystemConfig.get(self.config_key)

    def to_dict(self):
        """Serialize config to dictionary"""
        return {
            'id': self.id,
            'key': self.config_key,
            'value': self.config_value,
            'type': self.config_type,
            'category': self.category,
            'description': self.description,
            'typed_value': self.typed_value,
            'updated_by': self.updated_by,
            'updater_name': self.updater.full_name if self.updater else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<SystemConfig {self.config_key}={self.config_value}>'
