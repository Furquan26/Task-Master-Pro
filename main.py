import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pytesseract
from PIL import Image
import cv2
import numpy as np
import re
import os

# ====================== #
# Custom Theme Setup
# ====================== #
def setup_page_style():
    """Apply custom styling to make the app look professional"""
    st.markdown("""
    <style>
    /* Main background gradient */
    .stApp {
        background: linear-gradient(to bottom right, #1e3c72, #2a5298, #7e8ba3);
    }
    
    /* All text colors */
    h1, h2, h3, p, label, div {
        color: #ffffff !important;
    }
    
    /* Main heading */
    h1 {
        text-align: center;
        font-size: 3em;
        font-weight: bold;
        padding: 20px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    /* Section headings */
    h2 {
        font-size: 1.8em;
        padding: 15px 0;
        border-bottom: 3px solid #4CAF50;
        margin-top: 30px;
    }
    
    /* Card-like containers */
    .stExpander {
        background-color: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 10px;
        margin: 10px 0;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* Buttons styling */
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 8px 20px;
        font-weight: bold;
        transition: 0.3s;
    }
    
    .stButton>button:hover {
        background-color: #45a049;
        transform: scale(1.05);
    }
    
    /* Input fields */
    .stTextInput>div>div>input {
        background-color: rgba(255, 255, 255, 0.9);
        border-radius: 5px;
        color: #000000;
    }
    
    /* Metrics styling */
    [data-testid="stMetricValue"] {
        font-size: 2em;
        color: #FFD700 !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(to bottom, #2c3e50, #34495e);
    }
    </style>
    """, unsafe_allow_html=True)

# ====================== #
# Database Functions
# ====================== #
def setup_database():
    """Initialize database with required tables"""
    db = sqlite3.connect('tasks.db')
    cursor = db.cursor()
    
    # Create tasks table if not exists
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks 
                (id INTEGER PRIMARY KEY, 
                name TEXT, 
                intensity TEXT, 
                date DATE, 
                completed BOOLEAN,
                carry_forward BOOLEAN)''')
    
    # Create streaks table
    cursor.execute('''CREATE TABLE IF NOT EXISTS streaks 
                (id INTEGER PRIMARY KEY,
                last_updated DATE,
                current_streak INTEGER,
                emergency_skips INTEGER,
                last_skip_date DATE)''')
    
    # Add initial streak record if table is empty
    cursor.execute("SELECT COUNT(*) FROM streaks")
    if cursor.fetchone()[0] == 0:
        today = datetime.now().date()
        cursor.execute("INSERT INTO streaks (last_updated, current_streak, emergency_skips, last_skip_date) VALUES (?, ?, ?, ?)",
                     (today, 0, 0, None))
    
    db.commit()
    db.close()

def fetch_all_tasks():
    """Get all tasks from database"""
    db = sqlite3.connect('tasks.db')
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tasks ORDER BY date DESC")
    result = cursor.fetchall()
    db.close()
    
    # Convert to dictionary format for easier access
    task_list = []
    for row in result:
        task_list.append({
            'id': row[0],
            'name': row[1],
            'intensity': row[2],
            'date': row[3],
            'completed': row[4],
            'carry_forward': row[5]
        })
    return task_list

def create_new_task(task_name, task_intensity, task_date=None, is_carried=False):
    """Add a new task to the database"""
    if task_date is None:
        task_date = datetime.now().date()
    
    db = sqlite3.connect('tasks.db')
    cursor = db.cursor()
    cursor.execute("INSERT INTO tasks (name, intensity, date, completed, carry_forward) VALUES (?, ?, ?, ?, ?)",
                  (task_name, task_intensity, task_date, False, is_carried))
    db.commit()
    db.close()

def modify_task_details(task_id, updated_name, updated_intensity):
    """Update existing task information"""
    db = sqlite3.connect('tasks.db')
    cursor = db.cursor()
    cursor.execute("UPDATE tasks SET name = ?, intensity = ? WHERE id = ?",
                  (updated_name, updated_intensity, task_id))
    db.commit()
    db.close()

def remove_task(task_id):
    """Delete a task from database"""
    db = sqlite3.connect('tasks.db')
    cursor = db.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    db.close()

def mark_task_complete(task_id):
    """Mark a task as completed"""
    db = sqlite3.connect('tasks.db')
    cursor = db.cursor()
    cursor.execute("UPDATE tasks SET completed = 1, carry_forward = 0 WHERE id = ?", (task_id,))
    db.commit()
    db.close()

def mark_task_incomplete(task_id):
    """Mark a task as incomplete (undo completion)"""
    db = sqlite3.connect('tasks.db')
    cursor = db.cursor()
    cursor.execute("UPDATE tasks SET completed = 0 WHERE id = ?", (task_id,))
    db.commit()
    db.close()

def get_todays_tasks():
    """Fetch tasks scheduled for today"""
    today = datetime.now().date()
    db = sqlite3.connect('tasks.db')
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tasks WHERE date = ?", (today,))
    result = cursor.fetchall()
    db.close()
    
    task_list = []
    for row in result:
        task_list.append({
            'id': row[0],
            'name': row[1],
            'intensity': row[2],
            'date': row[3],
            'completed': row[4],
            'carry_forward': row[5]
        })
    return task_list

def get_completed_tasks_today():
    """Get list of tasks completed today"""
    today = datetime.now().date()
    db = sqlite3.connect('tasks.db')
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tasks WHERE completed = 1 AND date = ?", (today,))
    result = cursor.fetchall()
    db.close()
    
    task_list = []
    for row in result:
        task_list.append({
            'id': row[0],
            'name': row[1],
            'intensity': row[2],
            'date': row[3],
            'completed': row[4],
            'carry_forward': row[5]
        })
    return task_list

def get_pending_tasks():
    """Get tasks that are overdue"""
    today = datetime.now().date()
    db = sqlite3.connect('tasks.db')
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tasks WHERE completed = 0 AND date < ?", (today,))
    result = cursor.fetchall()
    db.close()
    
    task_list = []
    for row in result:
        task_list.append({
            'id': row[0],
            'name': row[1],
            'intensity': row[2],
            'date': row[3],
            'completed': row[4],
            'carry_forward': row[5]
        })
    return task_list

def handle_overdue_tasks():
    """Automatically carry forward incomplete tasks from previous days"""
    overdue = get_pending_tasks()
    for task in overdue:
        # Only carry forward if not already carried
        if not task['carry_forward']:
            create_new_task(task['name'], task['intensity'], datetime.now().date(), True)

def refresh_streak_count():
    """Update streak based on task completion"""
    db = sqlite3.connect('tasks.db')
    cursor = db.cursor()
    cursor.execute("SELECT * FROM streaks ORDER BY id DESC LIMIT 1")
    streak_record = cursor.fetchone()
    
    if streak_record:
        # Parse the last updated date
        last_update = datetime.strptime(streak_record[1], "%Y-%m-%d").date() if isinstance(streak_record[1], str) else streak_record[1]
        today = datetime.now().date()
        days_diff = (today - last_update).days
        
        if days_diff == 1:
            # Consecutive day - increment streak
            updated_streak = streak_record[2] + 1
        elif days_diff > 1:
            # Missed days - reset streak
            updated_streak = 1
        else:
            # Same day - keep current streak
            updated_streak = streak_record[2]
    else:
        updated_streak = 1
    
    cursor.execute("UPDATE streaks SET last_updated = ?, current_streak = ? WHERE id = ?",
                  (datetime.now().date(), updated_streak, streak_record[0]))
    db.commit()
    db.close()
    return updated_streak

def try_emergency_skip():
    """Use emergency skip if available (once per week)"""
    db = sqlite3.connect('tasks.db')
    cursor = db.cursor()
    cursor.execute("SELECT * FROM streaks ORDER BY id DESC LIMIT 1")
    streak_record = cursor.fetchone()
    
    skip_available = False
    if streak_record:
        last_skip_date = datetime.strptime(streak_record[4], "%Y-%m-%d").date() if streak_record[4] else None
        today = datetime.now().date()
        
        # Check if 7 days have passed since last skip
        if not last_skip_date or (today - last_skip_date).days >= 7:
            skip_available = True
    
    if skip_available:
        cursor.execute("UPDATE streaks SET emergency_skips = ?, last_skip_date = ? WHERE id = ?",
                     (streak_record[3] + 1, datetime.now().date(), streak_record[0]))
        db.commit()
    
    db.close()
    return skip_available

def calculate_weekly_stats():
    """Calculate completion percentage for last 7 days"""
    week_ago = datetime.now().date() - timedelta(days=7)
    
    db = sqlite3.connect('tasks.db')
    cursor = db.cursor()
    
    # Count completed tasks
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE completed = 1 AND date >= ?", (week_ago,))
    done_count = cursor.fetchone()[0]
    
    # Count total tasks
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE date >= ?", (week_ago,))
    total_count = cursor.fetchone()[0]
    
    db.close()
    
    if total_count > 0:
        percentage = (done_count / total_count) * 100
        return round(percentage, 1)
    return 0

# ====================== #
# Screen Time OCR Function
# ====================== #
def read_screen_time_from_image(image_file):
    """Extract screen time duration from uploaded screenshot using OCR"""
    try:
        # Read image using OpenCV
        image_data = cv2.imread(image_file)
        # Convert to grayscale for better OCR
        gray_image = cv2.cvtColor(image_data, cv2.COLOR_BGR2GRAY)
        # Apply threshold to make text clearer
        _, processed_image = cv2.threshold(gray_image, 150, 255, cv2.THRESH_BINARY_INV)
        # Extract text using Tesseract
        extracted_text = pytesseract.image_to_string(processed_image)
        
        # Find time patterns in extracted text (e.g., "3h 45m" or "2.5 hours")
        time_patterns = re.findall(r'(\d+)\s*h\s*(\d+)\s*m|(\d+\.?\d*)\s*hours?', extracted_text, re.IGNORECASE)
        
        if time_patterns:
            if time_patterns[0][2]:  # Format: "3.5 hours"
                return float(time_patterns[0][2])
            else:  # Format: "3h 15m"
                hrs = int(time_patterns[0][0])
                mins = int(time_patterns[0][1])
                return hrs + (mins / 60)
        return 0.0
    except Exception as error:
        st.error(f"Error reading image: {error}")
        return 0.0

# ====================== #
# Main Application
# ====================== #
st.set_page_config(page_title="Task Master Pro", page_icon="⚡", layout="wide")

# Apply custom styling
setup_page_style()

# Initialize database
setup_database()
handle_overdue_tasks()
current_streak = refresh_streak_count()

# ====================== #
# Page Header
# ====================== #
st.title("⚡ TASK MASTER PRO")

# Display current date and time
current_time = datetime.utcnow() + timedelta(hours=5, minutes=30)  # IST timezone
st.markdown(f"<h3 style='text-align: center;'>📅 {current_time.strftime('%A, %d %B %Y | %I:%M %p IST')}</h3>", unsafe_allow_html=True)

# ====================== #
# Sidebar Section
# ====================== #
st.sidebar.title("🎯 Your Progress")
st.sidebar.metric("🔥 Current Streak", f"{current_streak} Days", delta="Keep Going!")

if st.sidebar.button("🚨 Use Emergency Skip"):
    if try_emergency_skip():
        st.sidebar.success("✅ Emergency skip activated! Streak protected.")
    else:
        st.sidebar.error("❌ Emergency skip already used this week!")

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** Consistency is the key to success. Complete at least one task daily!")

# ====================== #
# Statistics Dashboard
# ====================== #
st.header("📊 Performance Dashboard")
col1, col2, col3 = st.columns(3)

with col1:
    weekly_completion = calculate_weekly_stats()
    st.metric("Weekly Completion", f"{weekly_completion}%", delta="Last 7 Days")

with col2:
    todays_tasks = get_todays_tasks()
    st.metric("Today's Tasks", len(todays_tasks))

with col3:
    completed_today = get_completed_tasks_today()
    st.metric("Completed Today", len(completed_today), delta=f"{len(completed_today)}/{len(todays_tasks)}")

st.markdown("---")

# ====================== #
# Task Management Section
# ====================== #
st.header("📝 Manage Your Tasks")

# Add New Task
with st.expander("➕ Create New Task", expanded=False):
    with st.form("task_creation_form", clear_on_submit=True):
        new_task = st.text_input("📌 Task Name (e.g., Morning Workout)")
        task_duration = st.text_input("⏱️ Duration (e.g., 30 minutes)")
        
        submit_btn = st.form_submit_button("Add Task", use_container_width=True)
        if submit_btn:
            if new_task and task_duration:
                create_new_task(new_task, task_duration)
                st.success(f"✅ Task '{new_task}' added successfully!")
                st.rerun()
            else:
                st.warning("⚠️ Please fill in all fields!")

# Modify Existing Task
with st.expander("✏️ Edit Task"):
    all_tasks = fetch_all_tasks()
    if not all_tasks:
        st.info("No tasks available to edit")
    else:
        task_options = [f"{t['id']}: {t['name']} ({t['intensity']})" for t in all_tasks]
        selected = st.selectbox("Select Task", task_options, key="edit_selector")
        
        selected_id = int(selected.split(":")[0])
        selected_task = next(t for t in all_tasks if t['id'] == selected_id)
        
        with st.form("task_edit_form"):
            edited_name = st.text_input("Task Name", value=selected_task['name'])
            edited_duration = st.text_input("Duration", value=selected_task['intensity'])
            
            if st.form_submit_button("Update Task", use_container_width=True):
                modify_task_details(selected_id, edited_name, edited_duration)
                st.success("✅ Task updated successfully!")
                st.rerun()

# Delete Task
with st.expander("🗑️ Remove Task"):
    all_tasks = fetch_all_tasks()
    if not all_tasks:
        st.info("No tasks available to delete")
    else:
        task_options = [f"{t['id']}: {t['name']} ({t['intensity']})" for t in all_tasks]
        to_delete = st.selectbox("Select Task to Delete", task_options, key="delete_selector")
        
        delete_id = int(to_delete.split(":")[0])
        if st.button("🗑️ Confirm Delete", key=f"confirm_delete_{delete_id}", use_container_width=True):
            remove_task(delete_id)
            st.success("✅ Task deleted!")
            st.rerun()

st.markdown("---")

# ====================== #
# Active Tasks Display
# ====================== #
st.header("📋 Today's Active Tasks")

active_tasks = [t for t in get_todays_tasks() if not t['completed']]

if not active_tasks:
    st.success("🎉 Great! No pending tasks for today!")
else:
    for idx, task in enumerate(active_tasks):
        col1, col2, col3, col4 = st.columns([5, 2, 2, 2])
        
        with col1:
            st.markdown(f"**{task['name']}** - *{task['intensity']}*")
        
        with col2:
            if st.button("✅ Done", key=f"complete_active_{task['id']}_{idx}"):
                mark_task_complete(task['id'])
                st.rerun()
        
        with col3:
            if st.button("✏️ Edit", key=f"edit_active_{task['id']}_{idx}"):
                st.info(f"Edit task #{task['id']}")
        
        with col4:
            if st.button("🗑️ Remove", key=f"delete_active_{task['id']}_{idx}"):
                remove_task(task['id'])
                st.rerun()

st.markdown("---")

# ====================== #
# Completed Tasks
# ====================== #
finished_tasks = get_completed_tasks_today()
if finished_tasks:
    st.header("✅ Completed Tasks Today")
    for idx, task in enumerate(finished_tasks):
        col1, col2 = st.columns([6, 2])
        
        with col1:
            st.markdown(f"~~{task['name']} - {task['intensity']}~~")
        
        with col2:
            if st.button("↩️ Undo", key=f"undo_complete_{task['id']}_{idx}"):
                mark_task_incomplete(task['id'])
                st.rerun()
    
    st.markdown("---")

# ====================== #
# Overdue Tasks
# ====================== #
pending_tasks = get_pending_tasks()
if pending_tasks:
    st.header("⚠️ Pending Tasks (Overdue)")
    for idx, task in enumerate(pending_tasks):
        col1, col2, col3, col4 = st.columns([5, 2, 2, 2])
        
        with col1:
            st.markdown(f"**{task['name']}** - *{task['intensity']}* (Due: {task['date']})")
        
        with col2:
            if st.button("✅ Complete", key=f"complete_pending_{task['id']}_{idx}"):
                mark_task_complete(task['id'])
                st.rerun()
        
        with col3:
            if st.button("✏️ Edit", key=f"edit_pending_{task['id']}_{idx}"):
                st.info(f"Edit task #{task['id']}")
        
        with col4:
            if st.button("🗑️ Remove", key=f"delete_pending_{task['id']}_{idx}"):
                remove_task(task['id'])
                st.rerun()
    
    st.markdown("---")

# ====================== #
# Screen Time Tracker
# ====================== #
st.header("📱 Screen Time Monitor")
st.info("Upload a screenshot of your screen time to track daily usage")

uploaded_screenshot = st.file_uploader("Choose Screenshot", type=["png", "jpg", "jpeg"])

if uploaded_screenshot:
    # Save uploaded file temporarily
    screenshot_dir = "assets/screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)
    file_location = os.path.join(screenshot_dir, uploaded_screenshot.name)
    
    with open(file_location, "wb") as file:
        file.write(uploaded_screenshot.getbuffer())
    
    # Display uploaded image
    st.image(uploaded_screenshot, caption="Uploaded Screenshot", width=300)
    
    # Extract screen time
    detected_time = read_screen_time_from_image(file_location)
    
    # Check against limit (2.5 hours)
    limit = 2.5
    if detected_time > limit:
        st.error(f"🚨 Screen Time Alert: {detected_time:.1f} hours / {limit} hours (Exceeded!)")
    else:
        st.success(f"✅ Screen Time: {detected_time:.1f} hours / {limit} hours (Within Limit)")
        st.progress(detected_time / limit)