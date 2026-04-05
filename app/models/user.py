"""
User model for authentication
"""
import hashlib
import secrets
import re
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer as Serializer
from datetime import datetime, timedelta, timezone
from app.extensions import db


_USERNAME_FORMAT_RE = re.compile(r'^[A-Za-z0-9._-]{3,30}$')
_NAME_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9' -]{0,49}$")
_MIDDLE_INITIAL_RE = re.compile(r'^[A-Za-z]{1,5}$')


# Junction table for many-to-many relationship between users and programs
user_programs = db.Table('user_programs',
    db.Column('id', db.Integer, primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    db.Column('program_id', db.Integer, db.ForeignKey('programs.id', ondelete='CASCADE'), nullable=False),
    db.Column('created_at', db.DateTime, default=db.func.current_timestamp()),
    db.UniqueConstraint('user_id', 'program_id', name='user_program_unique')
)


class User(UserMixin, db.Model):
    """User model for admin and dean roles"""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'super_admin', 'admin', or 'dean'
    full_name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Archive pattern columns
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    archived_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    archived_at = db.Column(db.DateTime, nullable=True)
    archive_reason = db.Column(db.String(255), nullable=True)
    
    # Email verification / First-login setup
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    email_verified_at = db.Column(db.DateTime, nullable=True)
    needs_password_change = db.Column(db.Boolean, nullable=False, default=False)
    two_factor_enabled = db.Column(db.Boolean, nullable=False, default=False)
    two_factor_secret = db.Column(db.String(64), nullable=True)
    two_factor_enabled_at = db.Column(db.DateTime, nullable=True)
    
    # Display preferences
    text_size = db.Column(db.Integer, nullable=False, default=100)
    dark_mode = db.Column(db.Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())
    last_login = db.Column(db.DateTime)
    force_logout_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships - many-to-many with programs
    programs = db.relationship('Program', secondary=user_programs, backref='users', lazy='subquery')
    
    # Self-referential relationship for archived_by
    archiver = db.relationship('User', remote_side=[id], foreign_keys=[archived_by], backref='archived_users')
    
    @property
    def is_super_admin(self):
        """Check if user is a super admin"""
        return self.role == 'super_admin'
    
    @property
    def is_admin(self):
        """Check if user is an admin (includes super_admin)"""
        return self.role in ('admin', 'super_admin')
    
    @property
    def is_dean(self):
        """Check if user is a dean"""
        return self.role == 'dean'
    
    def get_program_ids(self):
        """Get list of program IDs assigned to this user"""
        if self.is_admin:
            # Admins have access to all programs
            return None
        return [prog.id for prog in self.programs]
    
    def get_department_ids(self):
        """Get list of department IDs derived from user's assigned programs.
        Used for department-level access control on faculty."""
        if self.is_admin:
            return None  # Admin = access all
        return list({prog.department_id for prog in self.programs if prog.department_id})
    
    def has_program_access(self, program_id):
        """Check if user has access to a specific program"""
        if self.is_admin:
            return True
        if not program_id:
            return True  # Allow access to records without program
        return program_id in self.get_program_ids()
    
    def set_password(self, password):
        """Hash and set the user's password"""
        if len(password) < 8 or len(password) > 30:
            raise ValueError('Password must be between 8 and 30 characters')
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the hash"""
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def normalize_username(username):
        """Normalize username input before validation or persistence."""
        if username is None:
            return ''
        return str(username).strip()

    @staticmethod
    def validate_username_format(username):
        """Validate username format and return (is_valid, message, normalized_username)."""
        normalized = User.normalize_username(username)

        if not normalized:
            return False, 'Username is required', normalized

        if not _USERNAME_FORMAT_RE.fullmatch(normalized):
            return (
                False,
                'Username must be 3-30 characters and can only contain letters, numbers, dots, underscores, and hyphens',
                normalized,
            )

        return True, None, normalized

    @staticmethod
    def normalize_name_component(value):
        """Normalize first/last name input by trimming and collapsing internal spaces."""
        if value is None:
            return ''
        return ' '.join(str(value).strip().split())

    @staticmethod
    def split_full_name(full_name):
        """Split a legacy full_name string into first/middle-initial/last parts."""
        normalized_full_name = User.normalize_name_component(full_name)
        if not normalized_full_name:
            return {
                'first_name': '',
                'middle_initial': '',
                'last_name': '',
                'full_name': '',
            }

        tokens = normalized_full_name.split(' ')
        first_name = tokens[0]
        middle_initial = ''
        last_name = ''

        if len(tokens) >= 3:
            middle_token = tokens[1].rstrip('.')
            is_single_letter_middle = len(middle_token) == 1 and middle_token.isalpha()
            # Multi-letter middle initials are stored uppercased to avoid parsing
            # regular last-name particles (e.g., "Dela") as middle initials.
            is_multi_letter_middle = bool(
                _MIDDLE_INITIAL_RE.fullmatch(middle_token) and middle_token == middle_token.upper()
            )
            if is_single_letter_middle or is_multi_letter_middle:
                middle_initial = middle_token.upper()
                last_name = ' '.join(tokens[2:])
            else:
                last_name = ' '.join(tokens[1:])
        elif len(tokens) == 2:
            last_name = tokens[1]

        return {
            'first_name': first_name,
            'middle_initial': middle_initial,
            'last_name': last_name,
            'full_name': normalized_full_name,
        }

    @staticmethod
    def validate_name_parts(first_name, last_name, middle_initial=None):
        """Validate split-name parts and return (is_valid, message, normalized_payload)."""
        normalized_first_name = User.normalize_name_component(first_name)
        normalized_last_name = User.normalize_name_component(last_name)
        normalized_middle_initial = User.normalize_name_component(middle_initial).replace('.', '')

        if not normalized_first_name:
            return False, 'First name is required', None

        if not normalized_last_name:
            return False, 'Last name is required', None

        if not _NAME_COMPONENT_RE.fullmatch(normalized_first_name):
            return False, 'First name contains invalid characters', None

        if not _NAME_COMPONENT_RE.fullmatch(normalized_last_name):
            return False, 'Last name contains invalid characters', None

        if normalized_middle_initial:
            if not _MIDDLE_INITIAL_RE.fullmatch(normalized_middle_initial):
                return False, 'Middle initial must be 1 to 5 letters', None
            normalized_middle_initial = normalized_middle_initial.upper()

        full_name_tokens = [normalized_first_name]
        if normalized_middle_initial:
            full_name_tokens.append(normalized_middle_initial)
        full_name_tokens.append(normalized_last_name)
        normalized_full_name = ' '.join(full_name_tokens)

        if len(normalized_full_name) > 100:
            return False, 'Full name must be 100 characters or fewer', None

        return True, None, {
            'first_name': normalized_first_name,
            'middle_initial': normalized_middle_initial,
            'last_name': normalized_last_name,
            'full_name': normalized_full_name,
        }

    @staticmethod
    def resolve_full_name_input(full_name=None, first_name=None, middle_initial=None, last_name=None):
        """Resolve either split-name parts or legacy full_name into a validated payload."""
        has_split_fields = any(value is not None for value in (first_name, middle_initial, last_name))
        if has_split_fields:
            return User.validate_name_parts(first_name, last_name, middle_initial)

        normalized_full_name = User.normalize_name_component(full_name)
        if not normalized_full_name:
            return False, 'First name and last name are required', None

        parsed_parts = User.split_full_name(normalized_full_name)
        if parsed_parts['first_name'] and parsed_parts['last_name']:
            is_valid, message, normalized_parts = User.validate_name_parts(
                parsed_parts['first_name'],
                parsed_parts['last_name'],
                parsed_parts['middle_initial'],
            )
            if is_valid:
                return True, None, normalized_parts

        if len(normalized_full_name) > 100:
            return False, 'Full name must be 100 characters or fewer', None

        return True, None, parsed_parts

    @staticmethod
    def _resolve_otp_length(length=6):
        """Clamp requested OTP length into a safe numeric range."""
        try:
            parsed = int(length)
        except Exception:
            parsed = 6
        return min(max(parsed, 4), 8)

    @staticmethod
    def _utcnow_naive():
        """Return UTC now as naive datetime for legacy DATETIME columns."""
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def generate_email_otp(length=6):
        """Generate a numeric one-time code for email verification."""
        otp_length = User._resolve_otp_length(length)
        digits = '0123456789'
        return ''.join(secrets.choice(digits) for _ in range(otp_length))

    @staticmethod
    def hash_email_otp(code, salt):
        """Hash OTP code with a per-challenge salt before session storage."""
        normalized_code = User._normalize_two_factor_code(code)
        if not normalized_code or not salt:
            return None
        return hashlib.sha256(f'{salt}:{normalized_code}'.encode('utf-8')).hexdigest()

    @staticmethod
    def verify_email_otp_hash(code, expected_hash, salt, length=6):
        """Validate a submitted email OTP code against a stored hash."""
        normalized_code = User._normalize_two_factor_code(code)
        otp_length = User._resolve_otp_length(length)

        if len(normalized_code) != otp_length or not expected_hash or not salt:
            return False

        calculated_hash = User.hash_email_otp(normalized_code, salt)
        if not calculated_hash:
            return False

        return secrets.compare_digest(calculated_hash, expected_hash)

    @staticmethod
    def generate_two_factor_secret():
        """Generate a new base32 secret for TOTP."""
        import pyotp
        return pyotp.random_base32()

    @staticmethod
    def _normalize_two_factor_code(code):
        """Return only digits from a user-submitted TOTP code."""
        return ''.join(ch for ch in str(code or '') if ch.isdigit())

    @staticmethod
    def verify_two_factor_code_with_secret(secret, code, valid_window=1):
        """Verify a TOTP code using the provided shared secret."""
        normalized_code = User._normalize_two_factor_code(code)
        if not secret or len(normalized_code) != 6:
            return False

        import pyotp
        totp = pyotp.TOTP(secret)
        return bool(totp.verify(normalized_code, valid_window=valid_window))

    def verify_two_factor_code(self, code, valid_window=1):
        """Verify a TOTP code using the user's configured secret."""
        return User.verify_two_factor_code_with_secret(
            self.two_factor_secret,
            code,
            valid_window=valid_window
        )

    def get_two_factor_uri(self, secret=None, issuer='iSchedWise'):
        """Build the otpauth provisioning URI for authenticator apps."""
        resolved_secret = secret or self.two_factor_secret
        if not resolved_secret:
            return None

        import pyotp
        identifier = self.email or self.username
        totp = pyotp.TOTP(resolved_secret)
        return totp.provisioning_uri(name=identifier, issuer_name=issuer)

    def enable_two_factor(self, secret=None):
        """Enable 2FA and optionally persist a legacy shared secret."""
        self.two_factor_secret = secret
        self.two_factor_enabled = True
        self.two_factor_enabled_at = User._utcnow_naive()

    def disable_two_factor(self):
        """Disable TOTP 2FA and clear persisted secret data."""
        self.two_factor_enabled = False
        self.two_factor_secret = None
        self.two_factor_enabled_at = None
    
    def is_temporary_user(self):
        """
        Check if this is a temporary auto-generated user account.
        Temporary users have usernames like user001, user002, etc.
        and STILL have the default password 'ischedwise'
        """
        # Check if username matches the pattern user###
        if self.username.startswith('user') and len(self.username) == 7:
            try:
                # Check if the last 3 characters are digits
                int(self.username[4:])
                # Also check if they still have the default password
                if self.check_password('ischedwise'):
                    return True
            except ValueError:
                pass
        return False
    
    def is_expired_temporary_account(self):
        """
        Check if this temporary account has expired (24 hours without configuration).
        Returns True if:
        - Account is a temporary user (user### with default password)
        - Account was created more than 24 hours ago
        """
        if not self.is_temporary_user():
            return False
        
        # Check if account is older than 24 hours
        if self.created_at:
            expiry_time = self.created_at + timedelta(hours=24)
            if User._utcnow_naive() > expiry_time:
                return True
        
        return False
    
    def check_and_disable_if_expired(self):
        """
        Check if temporary account has expired and disable it if needed.
        Returns True if account was disabled, False otherwise.
        """
        if self.is_expired_temporary_account() and self.is_active:
            self.is_active = False
            return True
        return False
    
    def needs_first_login_setup(self):
        """
        Check if this user needs to complete first-login setup.
        Returns True if:
        - Account is a quick-generated temporary user (user### pattern)
        - AND still has the default password
        - AND has not completed email verification/setup
        """
        return self.is_temporary_user() and not self.email_verified
    
    def complete_first_login_setup(self, new_email, new_password, new_username=None, new_full_name=None):
        """
        Complete the first-login setup process for quick-generated accounts.
        Updates email, password, and optionally username and full_name.
        Marks email as verified.
        
        Args:
            new_email: New email address (required)
            new_password: New password (required)
            new_username: New username (optional)
            new_full_name: New full name (optional)
        """
        self.email = new_email
        self.set_password(new_password)
        self.email_verified = True
        self.email_verified_at = datetime.utcnow()
        self.needs_password_change = False
        
        if new_username:
            self.username = new_username
        if new_full_name:
            self.full_name = new_full_name
    
    def archive(self, user_id=None, reason=None):
        """
        Archive this user account (soft delete).
        
        Args:
            user_id: ID of the user performing the archive
            reason: Reason for archiving the account
        """
        self.is_archived = True
        self.is_active = False
        self.archived_by = user_id
        self.archive_reason = reason
        self.archived_at = datetime.utcnow()
    
    def unarchive(self):
        """
        Restore this user account from archive.
        Sets is_active to True and clears archive fields.
        """
        self.is_archived = False
        self.is_active = True
        self.archived_by = None
        self.archive_reason = None
        self.archived_at = None
    
    def generate_reset_token(self):
        """Generate a password reset token"""
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})
    
    @staticmethod
    def verify_reset_token(token, expiration=3600):
        """
        Verify a password reset token
        
        Args:
            token: The reset token to verify
            expiration: Token expiration time in seconds (default 1 hour)
            
        Returns:
            User object if token is valid, None otherwise
        """
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expiration)
            user_id = data.get('user_id')
            if user_id:
                return User.query.get(user_id)
        except:
            return None
        return None
    
    def __repr__(self):
        return f'<User {self.username}>'
