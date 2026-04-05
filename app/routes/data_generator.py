"""
Data Seed routes - Hidden page for generating realistic sample data
Accessible only by manually navigating to /dataseed (no sidebar link)
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.decorators import super_admin_required
from app.extensions import db

data_generator_bp = Blueprint('data_generator', __name__)


@data_generator_bp.route('/dataseed')
@login_required
@super_admin_required
def data_generator():
    """Data seed page — generate realistic sample data for testing"""
    return render_template('dataseed.html')


@data_generator_bp.route('/api/dataseed/status')
@login_required
@super_admin_required
def api_data_generator_status():
    """Get current entity counts for safety checks"""
    try:
        from app.services.data_generator import DataGenerator
        counts = DataGenerator.get_entity_counts()

        # Get active academic settings for display
        from app.models.settings import AcademicSettings
        settings = AcademicSettings.query.filter_by(is_active=True).first()
        academic_info = None
        if settings:
            academic_info = {
                'academic_year': settings.academic_year,
                'semester': settings.semester,
                'exam_period': settings.exam_period,
            }

        return jsonify({
            'success': True,
            'counts': counts,
            'academic_settings': academic_info,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@data_generator_bp.route('/api/dataseed/generate', methods=['POST'])
@login_required
@super_admin_required
def api_data_generator_generate():
    """Generate sample data based on provided configuration"""
    try:
        data = request.get_json() or {}
        config = data.get('config', {})

        if not config:
            return jsonify({'success': False, 'error': 'No generation config provided'}), 400

        from app.services.data_generator import DataGenerator
        generator = DataGenerator()
        result = generator.generate_all(config)

        if result['success']:
            from app.utils.activity_logger import log_activity
            summary_parts = []
            for k, v in result['results'].items():
                if v > 0:
                    summary_parts.append(f"{v} {k}")
            summary = ', '.join(summary_parts) if summary_parts else 'No data generated'
            log_activity('generate_sample_data', 'system',
                        details=f'Generated sample data: {summary}')

        return jsonify(result)
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@data_generator_bp.route('/api/dataseed/clear', methods=['POST'])
@login_required
@super_admin_required
def api_data_generator_clear():
    """Clear data for a specific entity type"""
    try:
        data = request.get_json() or {}
        entity_type = data.get('entity_type')

        if not entity_type:
            return jsonify({'success': False, 'error': 'No entity_type provided'}), 400

        # Get academic settings for scoped cleanup
        from app.models.settings import AcademicSettings
        settings = AcademicSettings.query.filter_by(is_active=True).first()
        academic_year = settings.academic_year if settings else None
        semester = settings.semester if settings else None

        # Scoped types use academic settings filter
        scoped_types = {'schedules', 'exam_schedules', 'faculty_assignments'}
        ay = academic_year if entity_type in scoped_types else None
        sem = semester if entity_type in scoped_types else None

        from app.services.data_generator import DataGenerator
        result = DataGenerator.clear_entity(entity_type, ay, sem)

        if result.get('success'):
            from app.utils.activity_logger import log_activity
            scope = f" ({academic_year} {semester})" if ay else ""
            log_activity('clear_generated_data', 'system',
                        details=f'Cleared {result["deleted"]} {entity_type}{scope}')

        return jsonify(result)
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@data_generator_bp.route('/api/dataseed/clear-all', methods=['POST'])
@login_required
@super_admin_required
def api_data_generator_clear_all():
    """Clear ALL generated data in FK-safe reverse-dependency order"""
    try:
        from app.models.settings import AcademicSettings
        settings = AcademicSettings.query.filter_by(is_active=True).first()
        academic_year = settings.academic_year if settings else None
        semester = settings.semester if settings else None

        from app.services.data_generator import DataGenerator

        results = {}
        clear_order = [
            ('exam_schedules', academic_year, semester),
            ('schedules', academic_year, semester),
            ('faculty_assignments', academic_year, semester),
            ('sections', None, None),
            ('faculty', None, None),
            ('buildings', None, None),
            ('programs', None, None),
        ]

        for entity_type, ay, sem in clear_order:
            result = DataGenerator.clear_entity(entity_type, ay, sem)
            if not result.get('success'):
                # Stop on first failure, report what was done so far
                from app.utils.activity_logger import log_activity
                summary_parts = [f"{v} {k}" for k, v in results.items() if v > 0]
                if summary_parts:
                    log_activity('clear_all_data', 'system',
                                details=f'Partial clear-all: {", ".join(summary_parts)} (failed on {entity_type}: {result.get("error", "Unknown")})')
                return jsonify({
                    'success': False,
                    'error': f'Failed clearing {entity_type}: {result.get("error", "Unknown error")}',
                    'results': results,
                }), 500
            results[entity_type] = result.get('deleted', 0)

        from app.utils.activity_logger import log_activity
        summary_parts = [f"{v} {k}" for k, v in results.items() if v > 0]
        summary = ', '.join(summary_parts) if summary_parts else 'No data to clear'
        log_activity('clear_all_data', 'system', details=f'Cleared all data: {summary}')

        return jsonify({'success': True, 'results': results})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
