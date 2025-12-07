"""
Building and Room management routes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Building, Room
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
from app.utils.activity_logger import log_create, log_edit, log_delete, log_archive, log_unarchive

building_bp = Blueprint('building', __name__, url_prefix='/buildings')


@building_bp.route('/')
@login_required
def index():
    """Buildings management page"""
    # Get selected building ID from query parameter
    selected_building_id = request.args.get('building_id', type=int)
    
    # Filter out archived buildings
    buildings = Building.query.filter_by(is_archived=False).order_by(Building.building_name).all()
    
    # If a building is selected, find it
    selected_building = None
    if selected_building_id and buildings:
        selected_building = Building.query.get(selected_building_id)
    
    return render_template('building.html', 
                         user=current_user, 
                         buildings=buildings,
                         selected_building=selected_building)


@building_bp.route('/add', methods=['POST'])
@login_required
def add():
    """Add a new building"""
    try:
        building_name = request.form.get('building_name', '').strip()
        
        # Validation
        if not building_name:
            flash('Please enter a building name.', 'error')
            return redirect(url_for('building.index'))
        
        # Check for duplicate building name
        if Building.query.filter_by(building_name=building_name).first():
            flash(f'Building "{building_name}" already exists.', 'error')
            return redirect(url_for('building.index'))
        
        # Create new building
        new_building = Building(
            building_name=building_name,
            is_active=True
        )
        
        db.session.add(new_building)
        db.session.flush()
        
        # Log activity with details
        log_create('building', new_building.id, new_building.building_name, 
                   details={'building_name': new_building.building_name})
        
        db.session.commit()
        
        flash(f'Building "{new_building.building_name}" has been successfully added!', 'success')
        return redirect(url_for('building.index', building_id=new_building.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while adding the building: {str(e)}', 'error')
        return redirect(url_for('building.index'))


@building_bp.route('/edit', methods=['POST'])
@login_required
def edit():
    """Edit an existing building"""
    try:
        building_id = request.form.get('building_id', '').strip()
        building_name = request.form.get('building_name', '').strip()
        
        if not all([building_id, building_name]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('building.index'))
        
        building = Building.query.get(int(building_id))
        if not building:
            flash('Building not found.', 'error')
            return redirect(url_for('building.index'))
        
        # Check for duplicate building name (excluding current building)
        existing = Building.query.filter(
            Building.building_name == building_name,
            Building.id != building.id
        ).first()
        
        if existing:
            flash(f'Building name "{building_name}" is already in use.', 'error')
            return redirect(url_for('building.index', building_id=building_id))
        
        # Track changes
        old_name = building.building_name
        changes = {}
        
        if building_name != old_name:
            changes['name'] = f'{old_name} → {building_name}'
        
        # Update building
        building.building_name = building_name
        
        # Log activity with changes
        log_edit('building', building.id, building.building_name, details=changes if changes else None)
        
        db.session.commit()
        
        flash(f'Building has been successfully updated!', 'success')
        return redirect(url_for('building.index', building_id=building_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while updating the building: {str(e)}', 'error')
        return redirect(url_for('building.index'))


@building_bp.route('/archive', methods=['POST'])
@login_required
def archive():
    """Archive a building"""
    try:
        building_id = request.form.get('building_id', '').strip()
        archive_reason = request.form.get('archive_reason', 'Manual archive by user').strip()
        
        if not building_id:
            flash('Invalid building.', 'error')
            return redirect(url_for('building.index'))
        
        building = Building.query.get(int(building_id))
        if not building:
            flash('Building not found.', 'error')
            return redirect(url_for('building.index'))
        
        building_name = building.building_name
        room_count = building.room_count
        
        # Get all room IDs from this building
        room_ids = [room.id for room in building.rooms]
        
        # Count schedules that will be deleted
        class_schedules_count = 0
        exam_schedules_count = 0
        
        if room_ids:
            # Find and delete class schedules using rooms from this building
            class_schedules = Schedule.query.filter(
                Schedule.room_id.in_(room_ids),
                Schedule.is_active == True
            ).all()
            
            for schedule in class_schedules:
                # Log deletion
                log_delete('schedule', schedule.id, 
                          f'{schedule.subject.subject_code if schedule.subject else "N/A"} - {schedule.section.section_name if schedule.section else "N/A"}',
                          {'reason': f'Building archived: {building_name}', 'room': schedule.room.room_number if schedule.room else 'N/A'})
                db.session.delete(schedule)
                class_schedules_count += 1
            
            # Find and delete exam schedules using rooms from this building
            exam_schedules = ExamSchedule.query.filter(
                ExamSchedule.room_id.in_(room_ids),
                ExamSchedule.is_active == True
            ).all()
            
            for exam_schedule in exam_schedules:
                # Log deletion
                log_delete('exam_schedule', exam_schedule.id,
                          f'{exam_schedule.subject.subject_code if exam_schedule.subject else "N/A"} - {exam_schedule.section.section_name if exam_schedule.section else "N/A"}',
                          {'reason': f'Building archived: {building_name}', 'room': exam_schedule.room.room_number if exam_schedule.room else 'N/A'})
                db.session.delete(exam_schedule)
                exam_schedules_count += 1
        
        # Archive building using helper method
        building.archive(user_id=current_user.id, reason=archive_reason)
        
        # Log building archive activity
        log_archive('building', building.id, building_name, {
            'reason': archive_reason, 
            'room_count': room_count,
            'deleted_class_schedules': class_schedules_count,
            'deleted_exam_schedules': exam_schedules_count
        })
        
        db.session.commit()
        
        flash(f'Building "{building_name}" has been archived successfully!', 'success')
        return redirect(url_for('building.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while archiving the building: {str(e)}', 'error')
        return redirect(url_for('building.index'))


@building_bp.route('/delete', methods=['POST'])
@login_required
def delete():
    """Delete a building permanently (only for archived buildings)"""
    try:
        building_id = request.form.get('building_id', '').strip()
        
        if not building_id:
            flash('Invalid building.', 'error')
            return redirect(url_for('archive.index'))
        
        building = Building.query.get(int(building_id))
        if not building:
            flash('Building not found.', 'error')
            return redirect(url_for('archive.index'))
        
        if not building.is_archived:
            flash('Only archived buildings can be permanently deleted.', 'error')
            return redirect(url_for('building.index'))
        
        building_name = building.building_name
        room_count = building.room_count
        
        # Log activity before deletion
        log_delete('building', building.id, building_name, {'room_count': room_count})
        
        # Delete the building (cascade will delete all rooms)
        db.session.delete(building)
        db.session.commit()
        
        if room_count > 0:
            flash(f'Building "{building_name}" and {room_count} room(s) have been permanently deleted.', 'success')
        else:
            flash(f'Building "{building_name}" has been permanently deleted.', 'success')
        
        return redirect(url_for('archive.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the building: {str(e)}', 'error')
        return redirect(url_for('archive.index'))


# ============================================================================
# Room Routes
# ============================================================================

@building_bp.route('/room/add', methods=['POST'])
@login_required
def add_room():
    """Add a new room to a building"""
    try:
        building_id = request.form.get('building_id', '').strip()
        room_number = request.form.get('room_number', '').strip()
        
        # Validation
        if not all([building_id, room_number]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('building.index'))
        
        building = Building.query.get(int(building_id))
        if not building:
            flash('Building not found.', 'error')
            return redirect(url_for('building.index'))
        
        # Check for duplicate room number in this building
        existing_room = Room.query.filter_by(
            building_id=building_id,
            room_number=room_number
        ).first()
        
        if existing_room:
            flash(f'Room number "{room_number}" already exists in this building.', 'error')
            return redirect(url_for('building.index', building_id=building_id))
        
        # Create new room
        new_room = Room(
            building_id=building_id,
            room_number=room_number,
            is_available=True
        )
        
        db.session.add(new_room)
        db.session.flush()
        
        # Log activity
        log_create('room', new_room.id, room_number, {'building': building.building_name})
        
        db.session.commit()
        
        flash(f'Room "{room_number}" has been successfully added to {building.building_name}!', 'success')
        return redirect(url_for('building.index', building_id=building_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while adding the room: {str(e)}', 'error')
        return redirect(url_for('building.index'))


@building_bp.route('/room/edit', methods=['POST'])
@login_required
def edit_room():
    """Edit an existing room"""
    try:
        room_id = request.form.get('room_id', '').strip()
        room_number = request.form.get('room_number', '').strip()
        
        if not all([room_id, room_number]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('building.index'))
        
        room = Room.query.get(int(room_id))
        if not room:
            flash('Room not found.', 'error')
            return redirect(url_for('building.index'))
        
        building_id = room.building_id
        
        # Check for duplicate room number in this building (excluding current room)
        existing_room = Room.query.filter(
            Room.building_id == building_id,
            Room.room_number == room_number,
            Room.id != room.id
        ).first()
        
        if existing_room:
            flash(f'Room number "{room_number}" already exists in this building.', 'error')
            return redirect(url_for('building.index', building_id=building_id))
        
        # Track changes
        old_room_number = room.room_number
        details = {'building': room.building.building_name}
        
        if room_number != old_room_number:
            details['room_number'] = f'{old_room_number} → {room_number}'
        
        # Update room
        room.room_number = room_number
        
        # Log activity with changes
        log_edit('room', room.id, room_number, details)
        
        db.session.commit()
        
        flash(f'Room has been successfully updated!', 'success')
        return redirect(url_for('building.index', building_id=building_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while updating the room: {str(e)}', 'error')
        return redirect(url_for('building.index'))


@building_bp.route('/room/delete', methods=['POST'])
@login_required
def delete_room():
    """Delete a room"""
    try:
        room_id = request.form.get('room_id', '').strip()
        building_id = request.form.get('building_id', '').strip()
        
        if not room_id:
            flash('Invalid room ID.', 'error')
            return redirect(url_for('building.index'))
        
        room = Room.query.get(int(room_id))
        if not room:
            flash('Room not found.', 'error')
            return redirect(url_for('building.index'))
        
        # Get building_id from room if not provided
        if not building_id:
            building_id = room.building_id
        
        room_number = room.room_number
        building_name = room.building.building_name
        
        # Log activity before deletion
        log_delete('room', room.id, room_number, {'building': building_name})
        
        # Delete the room
        db.session.delete(room)
        db.session.commit()
        
        flash(f'Room "{room_number}" has been deleted.', 'success')
        return redirect(url_for('building.index', building_id=building_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the room: {str(e)}', 'error')
        return redirect(url_for('building.index'))
