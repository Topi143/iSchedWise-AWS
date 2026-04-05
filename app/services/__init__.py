"""
Services package - Business logic and utilities
"""
from app.services.conflict_detector import ConflictDetector, Conflict, ConflictType, ConflictSeverity
from app.services.export_service import (
    generate_class_schedule_excel,
    generate_faculty_schedule_excel,
    generate_room_schedule_excel,
    generate_class_schedule_pdf,
    generate_faculty_schedule_pdf,
    generate_room_schedule_pdf
)
from app.services.recommendation_engine import RecommendationEngine

__all__ = [
    # Conflict Detection
    'ConflictDetector',
    'Conflict',
    'ConflictType',
    'ConflictSeverity',
    # Export Services
    'generate_class_schedule_excel',
    'generate_faculty_schedule_excel',
    'generate_room_schedule_excel',
    'generate_class_schedule_pdf',
    'generate_faculty_schedule_pdf',
    'generate_room_schedule_pdf',
    # Recommendation
    'RecommendationEngine',
]
