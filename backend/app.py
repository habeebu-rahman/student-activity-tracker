"""
Student Activity Tracker - Backend API
Using Flask + SQLite
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Database configuration
DATABASE = 'activities.db'

# ============================================================================
# DATABASE SETUP
# ============================================================================

def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create activities table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            activity TEXT NOT NULL,
            hours REAL NOT NULL CHECK (hours > 0),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✓ Database initialized successfully")

# Initialize database on startup
init_db()

# ============================================================================
# DATABASE HELPER FUNCTIONS
# ============================================================================

def get_db_connection():
    """Get SQLite database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

def dict_from_row(row):
    """Convert sqlite3.Row to dictionary"""
    return dict(row) if row else None

# ============================================================================
# ERROR HANDLING & VALIDATION
# ============================================================================

class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

@app.errorhandler(ValidationError)
def handle_validation_error(error):
    """Handle validation errors"""
    return jsonify({
        'status': 'error',
        'message': error.message
    }), error.status_code

@app.errorhandler(500)
def handle_server_error(error):
    """Handle server errors"""
    return jsonify({
        'status': 'error',
        'message': 'Internal server error',
        'details': str(error)
    }), 500

def validate_activity_data(data):
    """Validate activity input data"""
    errors = []
    
    # Check if data exists
    if not data:
        raise ValidationError("Request body is empty")
    
    # Validate student_name
    if 'student_name' not in data or not data['student_name']:
        errors.append("student_name is required")
    elif not isinstance(data['student_name'], str) or len(data['student_name'].strip()) == 0:
        errors.append("student_name must be a non-empty string")
    elif len(data['student_name']) > 100:
        errors.append("student_name must be less than 100 characters")
    
    # Validate activity
    if 'activity' not in data or not data['activity']:
        errors.append("activity is required")
    elif not isinstance(data['activity'], str) or len(data['activity'].strip()) == 0:
        errors.append("activity must be a non-empty string")
    elif len(data['activity']) > 200:
        errors.append("activity must be less than 200 characters")
    
    # Validate hours
    if 'hours' not in data:
        errors.append("hours is required")
    else:
        try:
            hours = float(data['hours'])
            if hours <= 0:
                errors.append("hours must be greater than 0")
            elif hours > 24:
                errors.append("hours cannot exceed 24")
        except (ValueError, TypeError):
            errors.append("hours must be a valid number")
    
    if errors:
        raise ValidationError(f"Validation failed: {'; '.join(errors)}")

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Server is running'
    }), 200

@app.route('/activities', methods=['POST'])
def add_activity():
    """
    POST /activities
    Add a new student activity
    
    Request body:
    {
        "student_name": "John Doe",
        "activity": "Frontend Development",
        "hours": 4.5
    }
    """
    try:
        data = request.get_json()
        
        # Validate input
        validate_activity_data(data)
        
        # Extract and clean data
        student_name = data['student_name'].strip()
        activity = data['activity'].strip()
        hours = float(data['hours'])
        
        # Insert into database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO activities (student_name, activity, hours)
            VALUES (?, ?, ?)
        ''', (student_name, activity, hours))
        
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': 'Activity added successfully',
            'id': new_id
        }), 201
    
    except ValidationError as e:
        return jsonify({
            'status': 'error',
            'message': e.message
        }), e.status_code
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Failed to add activity',
            'details': str(e)
        }), 500

@app.route('/activities', methods=['GET'])
def get_activities():
    """
    GET /activities
    Fetch all student activities
    
    Optional query parameters:
    - sort: 'recent' (default) or 'oldest'
    - limit: number of records to return
    """
    try:
        sort = request.args.get('sort', 'recent')
        limit = request.args.get('limit', None)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query
        query = 'SELECT * FROM activities'
        
        # Add sorting
        if sort == 'oldest':
            query += ' ORDER BY created_at ASC'
        else:
            query += ' ORDER BY created_at DESC'
        
        # Add limit
        if limit:
            try:
                limit = int(limit)
                query += f' LIMIT {limit}'
            except ValueError:
                pass
        
        cursor.execute(query)
        activities = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        activities_list = [dict(activity) for activity in activities]
        
        return jsonify({
            'status': 'success',
            'data': activities_list,
            'count': len(activities_list)
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Failed to fetch activities',
            'details': str(e)
        }), 500

@app.route('/activities/<int:activity_id>', methods=['PUT'])
def update_activity(activity_id):
    """
    PUT /activities/<id>
    Update an existing activity (partial or full update)
    
    Request body (all fields optional):
    {
        "student_name": "Updated Name",
        "activity": "Updated Activity",
        "hours": 5.0
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            raise ValidationError("Request body is empty")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if activity exists
        cursor.execute('SELECT * FROM activities WHERE id = ?', (activity_id,))
        existing = cursor.fetchone()
        if not existing:
            conn.close()
            raise ValidationError(f"Activity with ID {activity_id} not found", 404)
        
        # Get values - use existing if not provided in request
        student_name = data.get('student_name', existing['student_name'])
        activity = data.get('activity', existing['activity'])
        hours = data.get('hours', existing['hours'])
        
        # Strip whitespace if strings
        if isinstance(student_name, str):
            student_name = student_name.strip()
        if isinstance(activity, str):
            activity = activity.strip()
        
        # Validate updated fields
        if not student_name or len(student_name) == 0:
            raise ValidationError("student_name cannot be empty")
        if len(student_name) > 100:
            raise ValidationError("student_name must be less than 100 characters")
        
        if not activity or len(activity) == 0:
            raise ValidationError("activity cannot be empty")
        if len(activity) > 200:
            raise ValidationError("activity must be less than 200 characters")
        
        try:
            hours = float(hours)
            if hours <= 0:
                raise ValidationError("hours must be greater than 0")
            elif hours > 24:
                raise ValidationError("hours cannot exceed 24")
        except (ValueError, TypeError):
            raise ValidationError("hours must be a valid number")
        
        # Update the activity
        cursor.execute('''
            UPDATE activities 
            SET student_name = ?, activity = ?, hours = ?
            WHERE id = ?
        ''', (student_name, activity, hours, activity_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': f'Activity {activity_id} updated successfully',
            'id': activity_id
        }), 200
    
    except ValidationError as e:
        return jsonify({
            'status': 'error',
            'message': e.message
        }), e.status_code
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Failed to update activity',
            'details': str(e)
        }), 500

@app.route('/activities/<int:activity_id>', methods=['DELETE'])
def delete_activity(activity_id):
    """
    DELETE /activities/<id>
    Delete a specific activity
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if activity exists
        cursor.execute('SELECT id FROM activities WHERE id = ?', (activity_id,))
        if not cursor.fetchone():
            conn.close()
            raise ValidationError(f"Activity with ID {activity_id} not found", 404)
        
        # Delete the activity
        cursor.execute('DELETE FROM activities WHERE id = ?', (activity_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': f'Activity {activity_id} deleted successfully'
        }), 200
    
    except ValidationError as e:
        return jsonify({
            'status': 'error',
            'message': e.message
        }), e.status_code
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Failed to delete activity',
            'details': str(e)
        }), 500

@app.route('/summary', methods=['GET'])
def get_summary():
    """
    GET /summary
    Return summary statistics:
    - total_entries: Total number of activities
    - total_hours: Sum of all hours
    - most_active_user: Student with most hours
    - average_hours_per_activity: Average hours per activity
    - students_count: Total unique students
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total entries and total hours
        cursor.execute('''
            SELECT COUNT(*) as total_entries, 
                   COALESCE(SUM(hours), 0) as total_hours
            FROM activities
        ''')
        result = cursor.fetchone()
        total_entries = result['total_entries']
        total_hours = result['total_hours']
        
        # Get most active user
        cursor.execute('''
            SELECT student_name, SUM(hours) as total_student_hours
            FROM activities
            GROUP BY student_name
            ORDER BY total_student_hours DESC
            LIMIT 1
        ''')
        most_active = cursor.fetchone()
        
        # Get average hours per activity
        cursor.execute('''
            SELECT COALESCE(AVG(hours), 0) as average_hours
            FROM activities
        ''')
        avg_result = cursor.fetchone()
        average_hours = round(avg_result['average_hours'], 2)
        
        # Get total unique students
        cursor.execute('SELECT COUNT(DISTINCT student_name) as students_count FROM activities')
        students_result = cursor.fetchone()
        students_count = students_result['students_count']
        
        conn.close()
        
        summary_data = {
            'total_entries': total_entries,
            'total_hours': round(total_hours, 2),
            'most_active_user': most_active['student_name'] if most_active else None,
            'most_active_user_hours': round(most_active['total_student_hours'], 2) if most_active else 0,
            'average_hours_per_activity': average_hours,
            'total_students': students_count
        }
        
        return jsonify({
            'status': 'success',
            'data': summary_data
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Failed to fetch summary',
            'details': str(e)
        }), 500

# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API documentation"""
    return jsonify({
        'message': 'Student Activity Tracker API',
        'version': '1.0.0',
        'endpoints': {
            'POST /activities': 'Add a new activity',
            'GET /activities': 'Fetch all activities',
            'PUT /activities/<id>': 'Update an activity',
            'DELETE /activities/<id>': 'Delete an activity',
            'GET /summary': 'Get summary statistics',
            'GET /health': 'Health check'
        }
    }), 200

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Student Activity Tracker - Backend Server")
    print("=" * 60)
    print("📍 Server running on: http://localhost:5000")
    print("📚 Database: activities.db")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)