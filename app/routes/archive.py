"""
Archive Routes - Manage archived schedules, curricula, and departments
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models.archive import Archive
from app.models.faculty import FacultySubjectAssignment, Faculty
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
from app.models.settings import AcademicSettings
from app.models.curriculum import Curriculum
from app.models.department import Department
from app.models.building import Building
from app.utils.activity_logger import log_unarchive
from datetime import datetime
from sqlalchemy import or_, and_

archive_bp = Blueprint('archive', __name__, url_prefix='/archive')


@archive_bp.route('/')
@login_required
def index():
    """Display archive page with filters"""
    # Get all unique academic years from archives
    academic_years = db.session.query(Archive.academic_year).distinct().order_by(Archive.academic_year.desc()).all()
    academic_years = [ay[0] for ay in academic_years if ay[0]]
    
    # Get current academic settings
    current_settings = AcademicSettings.query.filter_by(is_active=True).first()
    
    # Get departments for program filter
    user_department_ids = current_user.get_department_ids()
    if user_department_ids is not None:
        # Dean: Only show assigned departments
        departments = Department.query.filter(
            Department.id.in_(user_department_ids),
            Department.is_archived == False
        ).order_by(Department.department_code).all()
    else:
        # Admin: Show all departments
        departments = Department.query.filter_by(is_archived=False).order_by(Department.department_code).all()
    
    # Get filter values from URL (for preserving state)
    selected_academic_year = request.args.get('academic_year', '')
    selected_semester = request.args.get('semester', '')
    selected_exam_period = request.args.get('exam_period', '')
    
    return render_template('archive.html',
                         academic_years=academic_years,
                         current_settings=current_settings,
                         departments=departments,
                         selected_academic_year=selected_academic_year,
                         selected_semester=selected_semester,
                         selected_exam_period=selected_exam_period)


@archive_bp.route('/api/archives')
@login_required
def get_archives():
    """Get archives with filters (API endpoint)"""
    try:
        # Get filter parameters
        academic_year = request.args.get('academic_year', '')
        semester = request.args.get('semester', '')
        exam_period = request.args.get('exam_period', '')
        schedule_type = request.args.get('schedule_type', '')  # 'lecture', 'lab', 'exam'
        section_id = request.args.get('section_id', type=int)
        faculty_id = request.args.get('faculty_id', type=int)
        room_id = request.args.get('room_id', type=int)
        building_id = request.args.get('building_id', type=int)
        department_id = request.args.get('department_id', type=int)
        search = request.args.get('search', '')
        
        # Get user's department access
        user_department_ids = current_user.get_department_ids()
        
        # Build query
        query = Archive.query
        
        # Filter by user's department access (through sections)
        if user_department_ids is not None:
            from app.models.department import Section
            accessible_section_ids = db.session.query(Section.id)\
                .filter(Section.department_id.in_(user_department_ids))\
                .all()
            accessible_section_ids = [sid[0] for sid in accessible_section_ids]
            if accessible_section_ids:
                query = query.filter(Archive.section_id.in_(accessible_section_ids))
        
        # Apply filters
        if academic_year:
            query = query.filter(Archive.academic_year == academic_year)
        
        if semester:
            query = query.filter(Archive.semester == semester)
        
        if exam_period:
            query = query.filter(Archive.exam_period == exam_period)
        
        if schedule_type:
            # Handle multiple schedule types (e.g., 'lecture,lab')
            types = [t.strip() for t in schedule_type.split(',')]
            if len(types) > 1:
                query = query.filter(Archive.schedule_type.in_(types))
            else:
                query = query.filter(Archive.schedule_type == schedule_type)
        
        if section_id:
            query = query.filter(Archive.section_id == section_id)
        
        if faculty_id:
            query = query.filter(Archive.faculty_id == faculty_id)
        
        if room_id:
            query = query.filter(Archive.room_id == room_id)
        
        if building_id:
            # Get all room IDs for this building
            from app.models.building import Room
            room_ids = db.session.query(Room.id).filter_by(building_id=building_id).all()
            room_ids = [rid[0] for rid in room_ids]
            if room_ids:
                query = query.filter(Archive.room_id.in_(room_ids))
        
        if department_id:
            # Get all section IDs for this department
            from app.models.department import Section
            section_ids = db.session.query(Section.id).filter_by(department_id=department_id).all()
            section_ids = [sid[0] for sid in section_ids]
            if section_ids:
                query = query.filter(Archive.section_id.in_(section_ids))
        
        if search:
            search_filter = or_(
                Archive.section_name.ilike(f'%{search}%'),
                Archive.subject_code.ilike(f'%{search}%'),
                Archive.course_description.ilike(f'%{search}%'),
                Archive.faculty_name.ilike(f'%{search}%'),
                Archive.room_number.ilike(f'%{search}%'),
                Archive.building_name.ilike(f'%{search}%'),
                Archive.department_name.ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
        # Order by archived date (most recent first)
        archives = query.order_by(Archive.archived_at.desc()).all()
        
        # Convert to dictionary
        archives_data = [archive.to_dict() for archive in archives]
        
        return jsonify({
            'success': True,
            'archives': archives_data,
            'total': len(archives_data)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching archives: {str(e)}'
        }), 500


@archive_bp.route('/api/archive/schedule/<int:schedule_id>', methods=['POST'])
@login_required
def archive_schedule(schedule_id):
    """Archive a class schedule"""
    try:
        schedule = Schedule.query.get_or_404(schedule_id)
        
        # Get archive reason from request
        data = request.get_json() or {}
        archive_reason = data.get('reason', 'Manual archive')
        
        # Normalize schedule_type: 'laboratory' -> 'lab'
        normalized_type = schedule.schedule_type
        if normalized_type and normalized_type.lower() in ['laboratory', 'lab']:
            normalized_type = 'lab'
        elif normalized_type and normalized_type.lower() == 'lecture':
            normalized_type = 'lecture'
        else:
            normalized_type = 'lecture'  # default
        
        # Create archive record
        archive = Archive(
            section_id=schedule.section_id,
            subject_id=schedule.subject_id,
            faculty_id=schedule.faculty_id,
            room_id=schedule.room_id,
            section_name=schedule.section.full_section_name if schedule.section else None,
            subject_code=schedule.subject.subject_code if schedule.subject else None,
            course_description=schedule.subject.course_description if schedule.subject else None,
            faculty_name=schedule.faculty.full_name if schedule.faculty else None,
            room_number=schedule.room.room_number if schedule.room else None,
            building_name=schedule.room.building.building_name if schedule.room and schedule.room.building else None,
            department_name=schedule.section.department.department_name if schedule.section and schedule.section.department else None,
            day_of_week=schedule.day_of_week,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            semester=schedule.semester,
            academic_year=schedule.academic_year,
            schedule_type=normalized_type,
            original_schedule_id=schedule.id,
            archived_by=current_user.id,
            archive_reason=archive_reason,
            archived_at=datetime.utcnow()
        )
        
        db.session.add(archive)
        
        # Delete the original schedule
        db.session.delete(schedule)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Schedule archived successfully',
            'archive_id': archive.id
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error archiving schedule: {str(e)}'
        }), 500


@archive_bp.route('/api/archive/exam-schedule/<int:exam_schedule_id>', methods=['POST'])
@login_required
def archive_exam_schedule(exam_schedule_id):
    """Archive an exam schedule"""
    try:
        exam_schedule = ExamSchedule.query.get_or_404(exam_schedule_id)
        
        # Get archive reason from request
        data = request.get_json() or {}
        archive_reason = data.get('reason', 'Manual archive')
        
        # Create archive record
        archive = Archive(
            section_id=exam_schedule.section_id,
            subject_id=exam_schedule.subject_id,
            faculty_id=exam_schedule.faculty_id,
            room_id=exam_schedule.room_id,
            section_name=exam_schedule.section.full_section_name if exam_schedule.section else None,
            subject_code=exam_schedule.subject.subject_code if exam_schedule.subject else None,
            course_description=exam_schedule.subject.course_description if exam_schedule.subject else None,
            faculty_name=exam_schedule.faculty.full_name if exam_schedule.faculty else None,
            room_number=exam_schedule.room.room_number if exam_schedule.room else None,
            building_name=exam_schedule.room.building.building_name if exam_schedule.room and exam_schedule.room.building else None,
            department_name=exam_schedule.section.department.department_name if exam_schedule.section and exam_schedule.section.department else None,
            exam_date=exam_schedule.exam_date,
            start_time=exam_schedule.start_time,
            end_time=exam_schedule.end_time,
            semester=exam_schedule.semester,
            academic_year=exam_schedule.academic_year,
            schedule_type='exam',
            exam_period=exam_schedule.exam_period,
            original_schedule_id=exam_schedule.id,
            archived_by=current_user.id,
            archive_reason=archive_reason,
            archived_at=datetime.utcnow()
        )
        
        db.session.add(archive)
        
        # Delete the original exam schedule
        db.session.delete(exam_schedule)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Exam schedule archived successfully',
            'archive_id': archive.id
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error archiving exam schedule: {str(e)}'
        }), 500


@archive_bp.route('/api/archive/bulk', methods=['POST'])
@login_required
def bulk_archive():
    """Bulk archive schedules by academic year and semester"""
    try:
        data = request.get_json()
        academic_year = data.get('academic_year')
        semester = data.get('semester')
        exam_period = data.get('exam_period')
        archive_reason = data.get('reason', 'Bulk archive')
        
        if not academic_year or not semester:
            return jsonify({
                'success': False,
                'message': 'Academic year and semester are required'
            }), 400
        
        archived_count = 0
        
        # Archive class schedules
        schedules = Schedule.query.filter_by(
            academic_year=academic_year,
            semester=semester,
            is_active=True
        ).all()
        
        for schedule in schedules:
            # Normalize schedule_type: 'laboratory' -> 'lab'
            normalized_type = schedule.schedule_type
            if normalized_type and normalized_type.lower() in ['laboratory', 'lab']:
                normalized_type = 'lab'
            elif normalized_type and normalized_type.lower() == 'lecture':
                normalized_type = 'lecture'
            else:
                normalized_type = 'lecture'  # default
            
            archive = Archive(
                section_id=schedule.section_id,
                subject_id=schedule.subject_id,
                faculty_id=schedule.faculty_id,
                room_id=schedule.room_id,
                section_name=schedule.section.full_section_name if schedule.section else None,
                subject_code=schedule.subject.subject_code if schedule.subject else None,
                course_description=schedule.subject.course_description if schedule.subject else None,
                faculty_name=schedule.faculty.full_name if schedule.faculty else None,
                room_number=schedule.room.room_number if schedule.room else None,
                building_name=schedule.room.building.building_name if schedule.room and schedule.room.building else None,
                department_name=schedule.section.department.department_name if schedule.section and schedule.section.department else None,
                day_of_week=schedule.day_of_week,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                semester=schedule.semester,
                academic_year=schedule.academic_year,
                schedule_type=normalized_type,
                original_schedule_id=schedule.id,
                archived_by=current_user.id,
                archive_reason=archive_reason,
                archived_at=datetime.utcnow()
            )
            db.session.add(archive)
            db.session.delete(schedule)
            archived_count += 1
        
        # Archive exam schedules
        exam_query = ExamSchedule.query.filter_by(
            academic_year=academic_year,
            semester=semester,
            is_active=True
        )
        
        if exam_period:
            exam_query = exam_query.filter_by(exam_period=exam_period)
        
        exam_schedules = exam_query.all()
        
        for exam_schedule in exam_schedules:
            archive = Archive(
                section_id=exam_schedule.section_id,
                subject_id=exam_schedule.subject_id,
                faculty_id=exam_schedule.faculty_id,
                room_id=exam_schedule.room_id,
                section_name=exam_schedule.section.full_section_name if exam_schedule.section else None,
                subject_code=exam_schedule.subject.subject_code if exam_schedule.subject else None,
                course_description=exam_schedule.subject.course_description if exam_schedule.subject else None,
                faculty_name=exam_schedule.faculty.full_name if exam_schedule.faculty else None,
                room_number=exam_schedule.room.room_number if exam_schedule.room else None,
                building_name=exam_schedule.room.building.building_name if exam_schedule.room and exam_schedule.room.building else None,
                department_name=exam_schedule.section.department.department_name if exam_schedule.section and exam_schedule.section.department else None,
                exam_date=exam_schedule.exam_date,
                start_time=exam_schedule.start_time,
                end_time=exam_schedule.end_time,
                semester=exam_schedule.semester,
                academic_year=exam_schedule.academic_year,
                schedule_type='exam',
                exam_period=exam_schedule.exam_period,
                original_schedule_id=exam_schedule.id,
                archived_by=current_user.id,
                archive_reason=archive_reason,
                archived_at=datetime.utcnow()
            )
            db.session.add(archive)
            db.session.delete(exam_schedule)
            archived_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully archived {archived_count} schedules',
            'archived_count': archived_count
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error bulk archiving: {str(e)}'
        }), 500


@archive_bp.route('/api/archive/<int:archive_id>', methods=['DELETE'])
@login_required
def delete_archive(archive_id):
    """Permanently delete an archive record"""
    try:
        archive = Archive.query.get_or_404(archive_id)
        
        db.session.delete(archive)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Archive deleted permanently'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting archive: {str(e)}'
        }), 500


@archive_bp.route('/api/archive/stats')
@login_required
def get_archive_stats():
    """Get archive statistics"""
    try:
        # Total archives
        total = Archive.query.count()
        
        # Archives by academic year
        by_year = db.session.query(
            Archive.academic_year,
            db.func.count(Archive.id)
        ).group_by(Archive.academic_year).all()
        
        # Archives by semester
        by_semester = db.session.query(
            Archive.semester,
            db.func.count(Archive.id)
        ).group_by(Archive.semester).all()
        
        # Archives by type
        by_type = db.session.query(
            Archive.schedule_type,
            db.func.count(Archive.id)
        ).group_by(Archive.schedule_type).all()
        
        # Debug: Get raw archive types
        all_archives = Archive.query.all()
        raw_types = [a.schedule_type for a in all_archives]
        
        print(f"DEBUG Archive Stats:")
        print(f"  Total archives: {total}")
        print(f"  Raw schedule types: {raw_types}")
        print(f"  Grouped by_type: {by_type}")
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'by_year': {year: count for year, count in by_year if year},
                'by_semester': {sem: count for sem, count in by_semester if sem},
                'by_type': {type: count for type, count in by_type if type}
            }
        })
    
    except Exception as e:
        print(f"ERROR in get_archive_stats: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching stats: {str(e)}'
        }), 500


@archive_bp.route('/api/faculty-assignments')
@login_required
def get_faculty_assignment_archives():
    """Get archived faculty subject assignments with filters (API endpoint)"""
    try:
        # Get filter parameters
        academic_year = request.args.get('academic_year', '')
        semester = request.args.get('semester', '')
        faculty_id = request.args.get('faculty_id', type=int)
        department = request.args.get('department', '')
        search = request.args.get('search', '')
        
        # Build query against flag-based faculty_subject_assignments
        query = FacultySubjectAssignment.query.filter_by(is_archived=True)
        
        # Apply filters
        if academic_year:
            query = query.filter(FacultySubjectAssignment.academic_year == academic_year)

        if semester:
            query = query.filter(FacultySubjectAssignment.semester == semester)

        if faculty_id:
            query = query.filter(FacultySubjectAssignment.faculty_id == faculty_id)

        # Order by archived date (most recent first)
        assignments = query.order_by(FacultySubjectAssignment.archived_at.desc()).all()
        
        # Convert minimal data to dictionary
        archives_data = []
        for a in assignments:
            archives_data.append({
                'id': a.id,
                'faculty_id': a.faculty_id,
                'subject_id': a.subject_id,
                'faculty_name': a.faculty.full_name if a.faculty else None,
                'subject_code': a.subject.subject_code if a.subject else None,
                'course_description': a.subject.course_description if a.subject else None,
                'academic_year': a.academic_year,
                'semester': a.semester,
                'archive_reason': a.archive_reason,
                'archived_at': a.archived_at.strftime('%Y-%m-%d %H:%M:%S') if a.archived_at else None,
                'archived_by': a.archived_by
            })
        
        return jsonify({
            'success': True,
            'archives': archives_data,
            'total': len(archives_data)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching archived faculty assignments: {str(e)}'
        }), 500


@archive_bp.route('/api/faculty-assignment/<int:archive_id>', methods=['DELETE'])
@login_required
def delete_faculty_assignment_archive(archive_id):
    """Permanently delete an archived faculty assignment record"""
    try:
        assignment = FacultySubjectAssignment.query.get_or_404(archive_id)
        # permanently delete the assignment row
        db.session.delete(assignment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Archived faculty assignment deleted successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting archived faculty assignment: {str(e)}'
        }), 500


@archive_bp.route('/api/faculty-assignment-stats')
@login_required
def get_faculty_assignment_archive_stats():
    """Get faculty assignment archive statistics"""
    try:
        # Total archived assignments
        total = FacultySubjectAssignment.query.filter_by(is_archived=True).count()
        
        # By academic year
        by_year = db.session.query(
            FacultySubjectAssignment.academic_year,
            db.func.count(FacultySubjectAssignment.id)
        ).filter(FacultySubjectAssignment.is_archived==True)\
         .group_by(FacultySubjectAssignment.academic_year)\
         .order_by(FacultySubjectAssignment.academic_year.desc()).all()
        
        # By semester
        by_semester = db.session.query(
            FacultySubjectAssignment.semester,
            db.func.count(FacultySubjectAssignment.id)
        ).filter(FacultySubjectAssignment.is_archived==True)\
         .group_by(FacultySubjectAssignment.semester).all()
        
        # By faculty
        by_faculty = db.session.query(
            FacultySubjectAssignment.faculty_id,
            db.func.count(FacultySubjectAssignment.id)
        ).filter(FacultySubjectAssignment.is_archived==True)\
         .group_by(FacultySubjectAssignment.faculty_id)\
         .order_by(db.func.count(FacultySubjectAssignment.id).desc())\
         .limit(10).all()
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'by_year': {year: count for year, count in by_year if year},
                'by_semester': {sem: count for sem, count in by_semester if sem},
                'top_faculty': [{'id': fac_id, 'count': count} for fac_id, count in by_faculty if fac_id]
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching faculty assignment archive stats: {str(e)}'
        }), 500


@archive_bp.route('/api/curricula')
@login_required
def get_archived_curricula():
    """Get archived curricula with filters (API endpoint)"""
    try:
        # Get filter parameters
        department_id = request.args.get('department_id', type=int)
        search = request.args.get('search', '')
        
        # Get user's department access
        user_department_ids = current_user.get_department_ids()
        
        # Build query for archived curricula
        query = Curriculum.query.filter_by(is_archived=True)
        
        # Filter by user's department access
        if user_department_ids is not None:
            query = query.filter(Curriculum.department_id.in_(user_department_ids))
        
        # Apply department filter
        if department_id:
            query = query.filter_by(department_id=department_id)
        
        # Apply search filter
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                or_(
                    Curriculum.curriculum_code.ilike(search_term),
                    Curriculum.degree_program.ilike(search_term)
                )
            )
        
        # Order by archived date (most recent first)
        curricula = query.order_by(Curriculum.archived_at.desc()).all()
        
        # Convert to dictionary
        curricula_data = [curriculum.to_dict() for curriculum in curricula]
        
        return jsonify({
            'success': True,
            'curricula': curricula_data,
            'total': len(curricula_data)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching archived curricula: {str(e)}'
        }), 500


@archive_bp.route('/api/curriculum/<int:curriculum_id>/unarchive', methods=['POST'])
@login_required
def unarchive_curriculum(curriculum_id):
    """Unarchive a curriculum"""
    try:
        curriculum = Curriculum.query.get_or_404(curriculum_id)
        
        # Log current state for debugging
        print(f"\n=== UNARCHIVE CURRICULUM DEBUG ===")
        print(f"Curriculum ID: {curriculum_id}")
        print(f"Curriculum Code: {curriculum.curriculum_code}")
        print(f"is_archived: {curriculum.is_archived}")
        print(f"is_active: {curriculum.is_active}")
        print(f"archived_by: {curriculum.archived_by}")
        print(f"archived_at: {curriculum.archived_at}")
        print(f"===================================\n")
        
        if not curriculum.is_archived:
            return jsonify({
                'success': False,
                'message': f'Curriculum "{curriculum.curriculum_code}" is not archived (is_archived={curriculum.is_archived}, is_active={curriculum.is_active})'
            }), 400
        
        # Unarchive curriculum using helper method
        curriculum.unarchive()
        
        # Log activity
        log_unarchive('curriculum', curriculum.id, curriculum.curriculum_code)
        
        db.session.commit()
        
        flash(f'Curriculum "{curriculum.curriculum_code}" has been restored successfully', 'success')
        
        return jsonify({
            'success': True,
            'message': f'Curriculum "{curriculum.curriculum_code}" has been restored successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"ERROR in unarchive_curriculum: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error restoring curriculum: {str(e)}'
        }), 500


@archive_bp.route('/api/curriculum-stats')
@login_required
def get_curriculum_archive_stats():
    """Get curriculum archive statistics"""
    try:
        # Get user's department access
        user_department_ids = current_user.get_department_ids()
        
        # Build base query
        query = Curriculum.query.filter_by(is_archived=True)
        
        if user_department_ids is not None:
            query = query.filter(Curriculum.department_id.in_(user_department_ids))
        
        # Total archived curricula
        total = query.count()
        
        # By department
        from app.models.department import Department
        by_department = db.session.query(
            Department.department_name, 
            db.func.count(Curriculum.id)
        ).join(Curriculum).filter(
            Curriculum.is_archived == True
        )
        
        if user_department_ids is not None:
            by_department = by_department.filter(Curriculum.department_id.in_(user_department_ids))
        
        by_department = by_department.group_by(Department.department_name).all()
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'by_department': {dept: count for dept, count in by_department}
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching curriculum archive stats: {str(e)}'
        }), 500


@archive_bp.route('/api/departments')
@login_required
def get_archived_departments():
    """Get archived departments with filters (API endpoint)"""
    try:
        # Get filter parameters
        search = request.args.get('search', '')
        
        # Get user's department access
        user_department_ids = current_user.get_department_ids()
        
        # Build query for archived departments
        query = Department.query.filter_by(is_archived=True)
        
        # Filter by user's department access
        if user_department_ids is not None:
            query = query.filter(Department.id.in_(user_department_ids))
        
        # Apply search filter
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                or_(
                    Department.department_code.ilike(search_term),
                    Department.department_name.ilike(search_term)
                )
            )
        
        # Order by archived date (most recent first)
        departments = query.order_by(Department.archived_at.desc()).all()
        
        # Convert to dictionary
        departments_data = [department.to_dict() for department in departments]
        
        return jsonify({
            'success': True,
            'departments': departments_data,
            'total': len(departments_data)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching archived departments: {str(e)}'
        }), 500


@archive_bp.route('/api/department/<int:department_id>/unarchive', methods=['POST'])
@login_required
def unarchive_department(department_id):
    """Unarchive a department"""
    try:
        department = Department.query.get_or_404(department_id)
        
        # Log current state for debugging
        print(f"\n=== UNARCHIVE DEPARTMENT DEBUG ===")
        print(f"Department ID: {department_id}")
        print(f"Department Code: {department.department_code}")
        print(f"is_archived: {department.is_archived}")
        print(f"is_active: {department.is_active}")
        print(f"archived_by: {department.archived_by}")
        print(f"archived_at: {department.archived_at}")
        print(f"===================================\n")
        
        if not department.is_archived:
            return jsonify({
                'success': False,
                'message': f'Department "{department.department_code}" is not archived (is_archived={department.is_archived}, is_active={department.is_active})'
            }), 400
        
        # Unarchive department using helper method
        department.unarchive()
        
        # Log activity
        log_unarchive('department', department.id, department.department_code)
        
        db.session.commit()
        
        flash(f'Department "{department.department_code}" has been restored successfully', 'success')
        
        return jsonify({
            'success': True,
            'message': f'Department "{department.department_code}" has been restored successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"ERROR in unarchive_department: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error restoring department: {str(e)}'
        }), 500


@archive_bp.route('/api/department-stats')
@login_required
def get_department_archive_stats():
    """Get department archive statistics"""
    try:
        # Get user's department access
        user_department_ids = current_user.get_department_ids()
        
        # Build base query
        query = Department.query.filter_by(is_archived=True)
        
        if user_department_ids is not None:
            query = query.filter(Department.id.in_(user_department_ids))
        
        # Total archived departments
        total = query.count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching department archive stats: {str(e)}'
        }), 500


# ========================================
# FACULTY ARCHIVE ROUTES
# ========================================

@archive_bp.route('/api/faculty')
@login_required
def get_archived_faculty():
    """Get all archived faculty members"""
    try:
        # Get archived faculty (no department filtering - faculty visible to all)
        query = Faculty.query.filter_by(is_archived=True)
        
        faculty_list = query.order_by(Faculty.full_name).all()
        
        return jsonify({
            'success': True,
            'faculty': [f.to_dict() for f in faculty_list]
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching archived faculty: {str(e)}'
        }), 500


@archive_bp.route('/api/faculty/<int:faculty_id>/unarchive', methods=['POST'])
@login_required
def unarchive_faculty(faculty_id):
    """Unarchive a faculty member"""
    try:
        faculty = Faculty.query.get_or_404(faculty_id)
        
        if not faculty.is_archived:
            return jsonify({
                'success': False,
                'message': 'Faculty is not archived'
            }), 400
        
        # Check department access for Deans
        user_department_ids = current_user.get_department_ids()
        if user_department_ids is not None and faculty.department_id not in user_department_ids:
            return jsonify({
                'success': False,
                'message': 'You do not have permission to unarchive this faculty'
            }), 403
        
        faculty_name = faculty.full_name
        
        # Unarchive faculty using helper method
        faculty.unarchive()
        
        # Log activity
        log_unarchive('faculty', faculty.id, faculty_name)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Faculty member {faculty_name} has been restored successfully!'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error unarchiving faculty: {str(e)}'
        }), 500


@archive_bp.route('/api/faculty/<int:faculty_id>', methods=['DELETE'])
@login_required
def delete_archived_faculty(faculty_id):
    """Permanently delete an archived faculty member"""
    try:
        faculty = Faculty.query.get_or_404(faculty_id)
        
        if not faculty.is_archived:
            return jsonify({
                'success': False,
                'message': 'Only archived faculty can be permanently deleted'
            }), 400
        
        # Check department access for Deans
        user_department_ids = current_user.get_department_ids()
        if user_department_ids is not None and faculty.department_id not in user_department_ids:
            return jsonify({
                'success': False,
                'message': 'You do not have permission to delete this faculty'
            }), 403
        
        faculty_name = faculty.full_name
        
        db.session.delete(faculty)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Faculty member {faculty_name} has been permanently deleted!'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting faculty: {str(e)}'
        }), 500


@archive_bp.route('/api/faculty/stats')
@login_required
def get_faculty_archive_stats():
    """Get statistics about archived faculty"""
    try:
        # Get archived faculty (no department filtering - faculty visible to all)
        query = Faculty.query.filter_by(is_archived=True)
        
        # Total archived faculty
        total = query.count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching faculty archive stats: {str(e)}'
        }), 500


# ==================== BUILDING ARCHIVE ENDPOINTS ====================

@archive_bp.route('/api/buildings')
@login_required
def get_archived_buildings():
    """Get all archived buildings (API endpoint)"""
    try:
        # Get search query
        search = request.args.get('search', '').strip()
        
        # Base query for archived buildings
        query = Building.query.filter_by(is_archived=True)
        
        # Apply search filter if provided
        if search:
            query = query.filter(
                or_(
                    Building.building_name.ilike(f'%{search}%'),
                    Building.building_code.ilike(f'%{search}%')
                )
            )
        
        # Order by most recently archived first
        buildings = query.order_by(Building.archived_at.desc()).all()
        
        # Convert to dictionary format
        buildings_data = []
        for building in buildings:
            # Get archived_by user name
            archived_by_name = 'Unknown'
            if building.archived_by:
                from app.models.user import User
                user = User.query.get(building.archived_by)
                if user:
                    archived_by_name = user.full_name
            
            buildings_data.append({
                'id': building.id,
                'building_name': building.building_name,
                'archived_at': building.archived_at.strftime('%Y-%m-%d %H:%M') if building.archived_at else '',
                'archived_by': archived_by_name,
                'archive_reason': building.archive_reason or 'No reason provided'
            })
        
        return jsonify({
            'success': True,
            'buildings': buildings_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching archived buildings: {str(e)}'
        }), 500


@archive_bp.route('/api/buildings/<int:building_id>/unarchive', methods=['POST'])
@login_required
def unarchive_building(building_id):
    """Restore an archived building"""
    try:
        building = Building.query.get_or_404(building_id)
        
        # Check if building is actually archived
        if not building.is_archived:
            return jsonify({
                'success': False,
                'message': 'Building is not archived'
            }), 400
        
        # Unarchive the building
        building.unarchive()
        
        # Log activity
        log_unarchive('building', building.id, building.building_name)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Building "{building.building_name}" restored successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error restoring building: {str(e)}'
        }), 500


@archive_bp.route('/api/buildings/<int:building_id>', methods=['DELETE'])
@login_required
def delete_archived_building(building_id):
    """Permanently delete an archived building"""
    try:
        building = Building.query.get_or_404(building_id)
        
        # Check if building is actually archived
        if not building.is_archived:
            return jsonify({
                'success': False,
                'message': 'Can only permanently delete archived buildings'
            }), 400
        
        building_name = building.building_name
        
        # Delete the building (cascades to rooms)
        db.session.delete(building)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Building "{building_name}" permanently deleted'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting building: {str(e)}'
        }), 500


@archive_bp.route('/api/buildings/stats')
@login_required
def get_building_archive_stats():
    """Get building archive statistics"""
    try:
        # Base query for archived buildings
        query = Building.query.filter_by(is_archived=True)
        
        # Total archived buildings
        total = query.count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching building archive stats: {str(e)}'
        }), 500

