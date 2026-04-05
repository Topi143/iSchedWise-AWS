"""
WebSocket event handlers for real-time schedule updates
Enables multi-user concurrent scheduling with live updates
"""
from flask import request
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from app.extensions import socketio, db
from app.models.schedule import Schedule
from app.models.exam_schedule import ExamSchedule
from datetime import datetime


# Track connected users by room (academic_year + semester)
connected_users = {}


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    if current_user.is_authenticated:
        emit('connected', {
            'user_id': current_user.id,
            'user_name': current_user.full_name,
            'message': 'Connected to schedule updates'
        })
    else:
        return False  # Reject unauthenticated connections


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection - release any locks held by this user"""
    if current_user.is_authenticated:
        # Release all locks held by this user
        try:
            Schedule.query.filter_by(locked_by=current_user.id).update({
                'locked_by': None,
                'locked_at': None
            })
            ExamSchedule.query.filter_by(locked_by=current_user.id).update({
                'locked_by': None,
                'locked_at': None
            })
            db.session.commit()
            
            # Notify others that locks were released
            emit('locks_released', {
                'user_id': current_user.id,
                'user_name': current_user.full_name
            }, broadcast=True)
        except Exception as e:
            db.session.rollback()
            print(f"Error releasing locks on disconnect: {e}")


@socketio.on('join_schedule_room')
def handle_join_room(data):
    """Join a room for specific academic year and semester"""
    if not current_user.is_authenticated:
        return
    
    academic_year = data.get('academic_year', '')
    semester = data.get('semester', '')
    room_name = f"schedule_{academic_year}_{semester}"
    
    join_room(room_name)
    
    # Track user in room
    if room_name not in connected_users:
        connected_users[room_name] = {}
    connected_users[room_name][current_user.id] = {
        'name': current_user.full_name,
        'connected_at': datetime.utcnow().isoformat()
    }
    
    # Notify room of new user
    emit('user_joined', {
        'user_id': current_user.id,
        'user_name': current_user.full_name,
        'users_count': len(connected_users[room_name]),
        'active_users': list(connected_users[room_name].values())
    }, room=room_name)


@socketio.on('leave_schedule_room')
def handle_leave_room(data):
    """Leave a schedule room"""
    if not current_user.is_authenticated:
        return
    
    academic_year = data.get('academic_year', '')
    semester = data.get('semester', '')
    room_name = f"schedule_{academic_year}_{semester}"
    
    leave_room(room_name)
    
    # Remove user from tracking
    if room_name in connected_users and current_user.id in connected_users[room_name]:
        del connected_users[room_name][current_user.id]
        
        # Notify room that user left
        emit('user_left', {
            'user_id': current_user.id,
            'user_name': current_user.full_name,
            'users_count': len(connected_users[room_name])
        }, room=room_name)


@socketio.on('acquire_schedule_lock')
def handle_acquire_lock(data):
    """Attempt to acquire edit lock on a schedule"""
    if not current_user.is_authenticated:
        emit('lock_error', {'message': 'Not authenticated'})
        return
    
    schedule_id = data.get('schedule_id')
    schedule_type = data.get('type', 'class')  # 'class' or 'exam'
    
    try:
        if schedule_type == 'exam':
            schedule = ExamSchedule.query.get(schedule_id)
        else:
            schedule = Schedule.query.get(schedule_id)
        
        if not schedule:
            emit('lock_error', {'message': 'Schedule not found'})
            return
        
        # Check if already locked by another user
        if schedule.is_locked_by_other(current_user.id):
            lock_info = schedule.get_lock_info()
            emit('lock_denied', {
                'schedule_id': schedule_id,
                'type': schedule_type,
                'locked_by': lock_info['locked_by_name'],
                'locked_at': lock_info['locked_at'],
                'expires_at': lock_info['expires_at']
            })
            return
        
        # Acquire lock
        if schedule.acquire_lock(current_user.id):
            db.session.commit()
            
            # Get room name for broadcasting
            academic_year = schedule.academic_year or ''
            semester = schedule.semester or ''
            room_name = f"schedule_{academic_year}_{semester}"
            
            # Notify everyone in the room
            emit('schedule_locked', {
                'schedule_id': schedule_id,
                'type': schedule_type,
                'locked_by': current_user.id,
                'locked_by_name': current_user.full_name,
                'locked_at': schedule.locked_at.isoformat()
            }, room=room_name)
            
            emit('lock_acquired', {
                'schedule_id': schedule_id,
                'type': schedule_type,
                'success': True
            })
        else:
            emit('lock_error', {'message': 'Failed to acquire lock'})
            
    except Exception as e:
        db.session.rollback()
        emit('lock_error', {'message': str(e)})


@socketio.on('release_schedule_lock')
def handle_release_lock(data):
    """Release edit lock on a schedule"""
    if not current_user.is_authenticated:
        return
    
    schedule_id = data.get('schedule_id')
    schedule_type = data.get('type', 'class')
    
    try:
        if schedule_type == 'exam':
            schedule = ExamSchedule.query.get(schedule_id)
        else:
            schedule = Schedule.query.get(schedule_id)
        
        if not schedule:
            return
        
        if schedule.release_lock(current_user.id):
            db.session.commit()
            
            # Get room name for broadcasting
            academic_year = schedule.academic_year or ''
            semester = schedule.semester or ''
            room_name = f"schedule_{academic_year}_{semester}"
            
            # Notify everyone in the room
            emit('schedule_unlocked', {
                'schedule_id': schedule_id,
                'type': schedule_type
            }, room=room_name)
            
    except Exception as e:
        db.session.rollback()
        print(f"Error releasing lock: {e}")


@socketio.on('heartbeat')
def handle_heartbeat(data):
    """Extend lock timeout by updating lock timestamp"""
    if not current_user.is_authenticated:
        return
    
    schedule_id = data.get('schedule_id')
    schedule_type = data.get('type', 'class')
    
    try:
        if schedule_type == 'exam':
            schedule = ExamSchedule.query.get(schedule_id)
        else:
            schedule = Schedule.query.get(schedule_id)
        
        if schedule and schedule.locked_by == current_user.id:
            schedule.locked_at = datetime.utcnow()
            db.session.commit()
            emit('heartbeat_ack', {'schedule_id': schedule_id})
            
    except Exception as e:
        db.session.rollback()


def broadcast_schedule_change(schedule, action, schedule_type='class'):
    """
    Broadcast schedule change to all users in the room
    Call this from route handlers after schedule CRUD operations
    
    Args:
        schedule: Schedule or ExamSchedule instance
        action: 'created', 'updated', or 'deleted'
        schedule_type: 'class' or 'exam'
    """
    academic_year = schedule.academic_year or ''
    semester = schedule.semester or ''
    room_name = f"schedule_{academic_year}_{semester}"
    
    schedule_data = schedule.to_dict() if hasattr(schedule, 'to_dict') else {'id': schedule.id}
    
    socketio.emit('schedule_changed', {
        'action': action,
        'type': schedule_type,
        'schedule': schedule_data,
        'changed_by': current_user.id if current_user.is_authenticated else None,
        'changed_by_name': current_user.full_name if current_user.is_authenticated else 'Unknown',
        'timestamp': datetime.utcnow().isoformat()
    }, room=room_name)


def get_active_users_in_room(academic_year, semester):
    """Get list of users currently viewing a specific schedule period"""
    room_name = f"schedule_{academic_year}_{semester}"
    return connected_users.get(room_name, {})


def broadcast_conflict_alert(schedule_data, conflicts, academic_year, semester, schedule_type='class'):
    """
    Broadcast conflict alert to users who might be affected
    
    This enables real-time conflict awareness - users editing overlapping
    time slots will receive notifications when another user creates or 
    updates a schedule that conflicts.
    
    Args:
        schedule_data: Dict with section_id, faculty_id, room_id, day_of_week, times
        conflicts: List of conflict dicts (from ConflictDetector)
        academic_year: Academic year for room routing
        semester: Semester for room routing
        schedule_type: 'class' or 'exam'
    """
    room_name = f"schedule_{academic_year}_{semester}"
    
    # Build alert message
    conflict_count = len(conflicts)
    affected_resources = []
    
    for conflict in conflicts:
        conflict_type = conflict.get('type', '')
        if conflict_type == 'section':
            affected_resources.append(f"Section (ID: {schedule_data.get('section_id')})")
        elif conflict_type == 'faculty':
            affected_resources.append(f"Faculty (ID: {schedule_data.get('faculty_id')})")
        elif conflict_type == 'room':
            affected_resources.append(f"Room (ID: {schedule_data.get('room_id')})")
    
    socketio.emit('conflict_alert', {
        'type': schedule_type,
        'day': schedule_data.get('day_of_week'),
        'start_time': str(schedule_data.get('start_time', '')),
        'end_time': str(schedule_data.get('end_time', '')),
        'affected_resources': list(set(affected_resources)),
        'conflict_count': conflict_count,
        'conflicts': conflicts,
        'severity': 'high' if conflict_count > 1 else 'medium',
        'message': f"Another user created a schedule with {conflict_count} potential conflict(s)",
        'created_by': current_user.full_name if current_user.is_authenticated else 'Unknown',
        'timestamp': datetime.utcnow().isoformat()
    }, room=room_name)


@socketio.on('request_conflict_recheck')
def handle_recheck_request(data):
    """
    Client requests a conflict recheck when notified of potential conflicts
    Triggers their local form to re-validate
    """
    if not current_user.is_authenticated:
        return
    
    # Just acknowledge - client will trigger their own recheck
    emit('recheck_confirmed', {
        'success': True,
        'message': 'Recheck your current form for updated conflicts'
    })
