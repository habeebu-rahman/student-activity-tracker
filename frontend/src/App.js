import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

// API base URL
const API_BASE_URL = 'http://localhost:5000';

const App = () => {
  // =========================================================================
  // STATE MANAGEMENT
  // =========================================================================
  
  const [activities, setActivities] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    student_name: '',
    activity: '',
    hours: ''
  });
  
  const [formErrors, setFormErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingId, setEditingId] = useState(null); // Track which activity is being edited

  // =========================================================================
  // AXIOS CONFIGURATION
  // =========================================================================

  const axiosInstance = axios.create({
    baseURL: API_BASE_URL,
    headers: {
      'Content-Type': 'application/json'
    },
    timeout: 5000
  });

  // =========================================================================
  // FETCH FUNCTIONS
  // =========================================================================

  const fetchActivities = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axiosInstance.get('/activities?sort=recent');
      setActivities(response.data.data || []);
    } catch (err) {
      const errorMsg = err.response?.data?.message || 'Failed to fetch activities';
      setError(errorMsg);
      console.error('Error fetching activities:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    try {
      const response = await axiosInstance.get('/summary');
      setSummary(response.data.data);
    } catch (err) {
      console.error('Error fetching summary:', err);
    }
  };

  // Fetch both activities and summary when component mounts
  useEffect(() => {
    fetchActivities();
    fetchSummary();
  }, []);

  // =========================================================================
  // FORM VALIDATION
  // =========================================================================

  const validateForm = () => {
    const newErrors = {};

    // Validate student_name
    if (!formData.student_name.trim()) {
      newErrors.student_name = 'Student name is required';
    } else if (formData.student_name.length > 100) {
      newErrors.student_name = 'Student name must be less than 100 characters';
    }

    // Validate activity
    if (!formData.activity.trim()) {
      newErrors.activity = 'Activity is required';
    } else if (formData.activity.length > 200) {
      newErrors.activity = 'Activity must be less than 200 characters';
    }

    // Validate hours
    if (!formData.hours) {
      newErrors.hours = 'Hours is required';
    } else {
      const hoursNum = parseFloat(formData.hours);
      if (isNaN(hoursNum)) {
        newErrors.hours = 'Hours must be a valid number';
      } else if (hoursNum <= 0) {
        newErrors.hours = 'Hours must be greater than 0';
      } else if (hoursNum > 24) {
        newErrors.hours = 'Hours cannot exceed 24';
      }
    }

    setFormErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // =========================================================================
  // FORM HANDLERS
  // =========================================================================

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error for this field when user starts typing
    if (formErrors[name]) {
      setFormErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validate form
    if (!validateForm()) {
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);

      const activityData = {
        student_name: formData.student_name.trim(),
        activity: formData.activity.trim(),
        hours: parseFloat(formData.hours)
      };

      let response;
      
      if (editingId) {
        // Update existing activity (PUT)
        response = await axiosInstance.put(`/activities/${editingId}`, activityData);
        setSuccessMessage('Activity updated successfully! ✓');
      } else {
        // Add new activity (POST)
        response = await axiosInstance.post('/activities', activityData);
        setSuccessMessage('Activity added successfully! ✓');
      }

      // Reset form
      setFormData({
        student_name: '',
        activity: '',
        hours: ''
      });
      setEditingId(null);

      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);

      // Refresh activities and summary
      await fetchActivities();
      await fetchSummary();

    } catch (err) {
      const errorMsg = err.response?.data?.message || 'Failed to save activity';
      setError(errorMsg);
      console.error('Error saving activity:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteActivity = async (id) => {
    if (window.confirm('Are you sure you want to delete this activity?')) {
      try {
        setError(null);
        await axiosInstance.delete(`/activities/${id}`);
        setSuccessMessage('Activity deleted successfully!');
        setTimeout(() => setSuccessMessage(null), 3000);
        
        // Refresh activities and summary
        await fetchActivities();
        await fetchSummary();
      } catch (err) {
        const errorMsg = err.response?.data?.message || 'Failed to delete activity';
        setError(errorMsg);
        console.error('Error deleting activity:', err);
      }
    }
  };

  const handleEditActivity = (activity) => {
    setFormData({
      student_name: activity.student_name,
      activity: activity.activity,
      hours: activity.hours.toString()
    });
    setEditingId(activity.id);
    window.scrollTo(0, 0); // Scroll to form
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setFormData({
      student_name: '',
      activity: '',
      hours: ''
    });
    setFormErrors({});
  };

  // =========================================================================
  // RENDER
  // =========================================================================

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <h1>Student Activity Tracker</h1>
          <p className="subtitle">Track and manage student learning activities</p>
        </div>
      </header>

      <main className="main-container">
        {/* Messages */}
        {error && <div className="alert alert-error">{error}</div>}
        {successMessage && <div className="alert alert-success">{successMessage}</div>}

        <div className="container-grid">
          {/* LEFT COLUMN: Form */}
          <section className="form-section">
            <div className="card">
              <h2>➕ Add New Activity</h2>
              <form onSubmit={handleSubmit} className="activity-form">
                {/* Student Name */}
                <div className="form-group">
                  <label htmlFor="student_name">Student Name *</label>
                  <input
                    type="text"
                    id="student_name"
                    name="student_name"
                    value={formData.student_name}
                    onChange={handleInputChange}
                    placeholder="e.g., Habeebu Rahman"
                    className={formErrors.student_name ? 'input-error' : ''}
                    disabled={isSubmitting}
                  />
                  {formErrors.student_name && (
                    <span className="error-text">{formErrors.student_name}</span>
                  )}
                </div>

                {/* Activity */}
                <div className="form-group">
                  <label htmlFor="activity">Activity *</label>
                  <input
                    type="text"
                    id="activity"
                    name="activity"
                    value={formData.activity}
                    onChange={handleInputChange}
                    placeholder="e.g., Frontend Development"
                    className={formErrors.activity ? 'input-error' : ''}
                    disabled={isSubmitting}
                  />
                  {formErrors.activity && (
                    <span className="error-text">{formErrors.activity}</span>
                  )}
                </div>

                {/* Hours */}
                <div className="form-group">
                  <label htmlFor="hours">Hours *</label>
                  <input
                    type="number"
                    id="hours"
                    name="hours"
                    value={formData.hours}
                    onChange={handleInputChange}
                    placeholder="e.g., 4.5"
                    step="0.5"
                    min="0"
                    max="24"
                    className={formErrors.hours ? 'input-error' : ''}
                    disabled={isSubmitting}
                  />
                  {formErrors.hours && (
                    <span className="error-text">{formErrors.hours}</span>
                  )}
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <span className="spinner"></span>
                      {editingId ? 'Updating...' : 'Adding...'}
                    </>
                  ) : (
                    editingId ? 'Update Activity' : 'Add Activity'
                  )}
                </button>

                {/* Cancel Button (only show when editing) */}
                {editingId && (
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={handleCancelEdit}
                    disabled={isSubmitting}
                  >
                    Cancel Edit
                  </button>
                )}
              </form>
            </div>
          </section>

          {/* RIGHT COLUMN: Summary and Activities */}
          <section className="content-section">
            {/* Summary Cards */}
            {summary && (
              <div className="summary-cards">
                <div className="card card-summary">
                  <div className="summary-item">
                    <span className="summary-icon">📊</span>
                    <div>
                      <p className="summary-label">Total Activities</p>
                      <p className="summary-value">{summary.total_entries}</p>
                    </div>
                  </div>
                </div>

                <div className="card card-summary">
                  <div className="summary-item">
                    <span className="summary-icon">⏱️</span>
                    <div>
                      <p className="summary-label">Total Hours</p>
                      <p className="summary-value">{summary.total_hours}</p>
                    </div>
                  </div>
                </div>

                <div className="card card-summary">
                  <div className="summary-item">
                    <span className="summary-icon">🏆</span>
                    <div>
                      <p className="summary-label">Most Active</p>
                      <p className="summary-value">
                        {summary.most_active_user || 'N/A'}
                      </p>
                      {summary.most_active_user && (
                        <p className="summary-subtext">
                          {summary.most_active_user_hours} hours
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                <div className="card card-summary">
                  <div className="summary-item">
                    <span className="summary-icon">👥</span>
                    <div>
                      <p className="summary-label">Total Students</p>
                      <p className="summary-value">{summary.total_students}</p>
                    </div>
                  </div>
                </div>

                <div className="card card-summary">
                  <div className="summary-item">
                    <span className="summary-icon">📈</span>
                    <div>
                      <p className="summary-label">Avg Hours/Activity</p>
                      <p className="summary-value">
                        {summary.average_hours_per_activity}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Activities List */}
            <div className="card">
              <h2>📋 Activities List</h2>

              {loading ? (
                <div className="loading-state">
                  <div className="spinner"></div>
                  <p>Loading activities...</p>
                </div>
              ) : activities.length === 0 ? (
                <div className="empty-state">
                  <p>No activities yet. Add your first activity above! 👆</p>
                </div>
              ) : (
                <div className="activities-table-wrapper">
                  <table className="activities-table">
                    <thead>
                      <tr>
                        <th>Student Name</th>
                        <th>Activity</th>
                        <th>Hours</th>
                        <th>Date</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {activities.map((activity) => (
                        <tr key={activity.id} className="activity-row">
                          <td className="cell-name">{activity.student_name}</td>
                          <td className="cell-activity">{activity.activity}</td>
                          <td className="cell-hours">
                            <span className="badge-hours">{activity.hours}h</span>
                          </td>
                          <td className="cell-date">
                            {new Date(activity.created_at).toLocaleDateString()}
                          </td>
                          <td className="cell-action">
                            <button
                              className="btn-edit"
                              onClick={() => handleEditActivity(activity)}
                              title="Edit activity"
                            >
                              ✎
                            </button>
                            <button
                              className="btn-delete"
                              onClick={() => handleDeleteActivity(activity.id)}
                              title="Delete activity"
                            >
                              ↩
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>
        </div>
      </main>

      <footer className="footer">
        <p>Student Activity Tracker © 2024 | Interview Project</p>
      </footer>
    </div>
  );
};

export default App;