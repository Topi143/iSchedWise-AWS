"""
Section model — represents a student group within a program (e.g., BSCS-1A).

Extracted from the old department.py for cleaner separation of concerns.
"""
from app.extensions import db


class Section(db.Model):
    """Section model for student groups"""

    __tablename__ = 'sections'

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'), nullable=False)
    section_name = db.Column(db.String(100), nullable=False)
    year_level = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, onupdate=db.func.current_timestamp())

    @property
    def full_section_name(self):
        """Returns the full section name format: PROG-YEAR_LEVEL+SECTION_NAME (e.g., BSCS-1A or BSCS/ACT-1A)"""
        if self.program:
            display_code = self.get_display_code_for_year()
            return f"{display_code}-{self.year_level}{self.section_name}"
        return self.section_name

    def get_display_code_for_year(self):
        """
        Get the display code for this section's year level.
        Checks if the program has shared program settings.
        Returns combined code (e.g., 'BSCS/ACT') if shared, otherwise program code.
        """
        if not self.program:
            return ''

        return self.program.get_display_code(self.year_level)

    def __repr__(self):
        return f'<Section {self.full_section_name}>'
