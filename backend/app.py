"""
Student Activity Tracker - Production Backend
Using Flask + PostgreSQL for deployment
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)

# CORS - Allow frontend domain (update after deployment)
CORS(app, origins=[
    "http://localhost:3000",
    "https://student-activity-tracker.onrender.com"
    "https://student-activity-tracker-xr6l.onrender.com" 
])

# Database configuration - Use PostgreSQL in production, SQLite in development
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Production: PostgreSQL
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    # Fix for Render.com's postgres:// to postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    def get_db_connection():
        """Get PostgreSQL database connection"""
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    
    def init_db():
        """Initialize PostgreSQL database with required tables"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activities (
                id SERIAL PRIMARY KEY,
                student_name VARCHAR(100) NOT NULL,
                activity VARCHAR(200) NOT NULL,
                hours DECIMAL(5,2) NOT NULL CHECK (hours > 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✓ PostgreSQL Database initialized successfully")
else:
    # Development: SQLite
    import sqlite3
    DATABASE = 'activities.db'
    
    def get_db_connection():
        """Get SQLite database connection"""
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db():
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
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
        print("✓ SQLite Database initialized successfully")

# Initialize database on startup
init_db()

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
        'message': 'Internal server error'
    }), 500

def validate_activity_data(data):
    """Validate activity input data"""
    errors = []
    
    if not data:
        raise ValidationError("Request body is empty")
    
    if 'student_name' not in data or not data['student_name']:
        errors.append("student_name is required")
    elif not isinstance(data['student_name'], str) or len(data['student_name'].strip()) == 0:
        errors.append("student_name must be a non-empty string")
    elif len(data['student_name']) > 100:
        errors.append("student_name must be less than 100 characters")
    
    if 'activity' not in data or not data['activity']:
        errors.append("activity is required")
    elif not isinstance(data['activity'], str) or len(data['activity'].strip()) == 0:
        errors.append("activity must be a non-empty string")
    elif len(data['activity']) > 200:
        errors.append("activity must be less than 200 characters")
    
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
    db_type = "PostgreSQL" if DATABASE_URL else "SQLite"
    return jsonify({
        'status': 'healthy',
        'message': 'Server is running',
        'database': db_type
    }), 200

@app.route('/activities', methods=['POST'])
def add_activity():
    """POST /activities - Add a new student activity"""
    try:
        data = request.get_json()
        validate_activity_data(data)
        
        student_name = data['student_name'].strip()
        activity = data['activity'].strip()
        hours = float(data['hours'])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO activities (student_name, activity, hours)
            VALUES (%s, %s, %s) RETURNING id
        ''' if DATABASE_URL else '''
            INSERT INTO activities (student_name, activity, hours)
            VALUES (?, ?, ?)
        ''', (student_name, activity, hours))
        
        if DATABASE_URL:
            new_id = cursor.fetchone()['id']
        else:
            new_id = cursor.lastrowid
        
        conn.commit()
        cursor.close()
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
    """GET /activities - Fetch all student activities"""
    try:
        sort = request.args.get('sort', 'recent')
        limit = request.args.get('limit', None)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM activities'
        
        if sort == 'oldest':
            query += ' ORDER BY created_at ASC'
        else:
            query += ' ORDER BY created_at DESC'
        
        if limit:
            try:
                limit = int(limit)
                query += f' LIMIT {limit}'
            except ValueError:
                pass
        
        cursor.execute(query)
        activities = cursor.fetchall()
        cursor.close()
        conn.close()
        
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
    """PUT /activities/<id> - Update an existing activity"""
    try:
        data = request.get_json()
        
        if not data:
            raise ValidationError("Request body is empty")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM activities WHERE id = %s' if DATABASE_URL else 'SELECT * FROM activities WHERE id = ?', (activity_id,))
        existing = cursor.fetchone()
        if not existing:
            cursor.close()
            conn.close()
            raise ValidationError(f"Activity with ID {activity_id} not found", 404)
        
        student_name = data.get('student_name', existing['student_name'])
        activity = data.get('activity', existing['activity'])
        hours = data.get('hours', existing['hours'])
        
        if isinstance(student_name, str):
            student_name = student_name.strip()
        if isinstance(activity, str):
            activity = activity.strip()
        
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
        
        cursor.execute('''
            UPDATE activities 
            SET student_name = %s, activity = %s, hours = %s
            WHERE id = %s
        ''' if DATABASE_URL else '''
            UPDATE activities 
            SET student_name = ?, activity = ?, hours = ?
            WHERE id = ?
        ''', (student_name, activity, hours, activity_id))
        
        conn.commit()
        cursor.close()
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
    """DELETE /activities/<id> - Delete a specific activity"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM activities WHERE id = %s' if DATABASE_URL else 'SELECT id FROM activities WHERE id = ?', (activity_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            raise ValidationError(f"Activity with ID {activity_id} not found", 404)
        
        cursor.execute('DELETE FROM activities WHERE id = %s' if DATABASE_URL else 'DELETE FROM activities WHERE id = ?', (activity_id,))
        conn.commit()
        cursor.close()
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
    """GET /summary - Return summary statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) as total_entries, 
                   COALESCE(SUM(hours), 0) as total_hours
            FROM activities
        ''')
        result = cursor.fetchone()
        total_entries = result['total_entries']
        total_hours = result['total_hours']
        
        cursor.execute('''
            SELECT student_name, SUM(hours) as total_student_hours
            FROM activities
            GROUP BY student_name
            ORDER BY total_student_hours DESC
            LIMIT 1
        ''')
        most_active = cursor.fetchone()
        
        cursor.execute('''
            SELECT COALESCE(AVG(hours), 0) as average_hours
            FROM activities
        ''')
        avg_result = cursor.fetchone()
        average_hours = round(float(avg_result['average_hours']), 2)
        
        cursor.execute('SELECT COUNT(DISTINCT student_name) as students_count FROM activities')
        students_result = cursor.fetchone()
        students_count = students_result['students_count']
        
        cursor.close()
        conn.close()
        
        summary_data = {
            'total_entries': total_entries,
            'total_hours': round(float(total_hours), 2),
            'most_active_user': most_active['student_name'] if most_active else None,
            'most_active_user_hours': round(float(most_active['total_student_hours']), 2) if most_active else 0,
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)