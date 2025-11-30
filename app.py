import os
import sqlite3
import shutil
from datetime import date, datetime
from pathlib import Path

import cv2
import face_recognition
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image


# Configuration
DB_PATH = "attendance.db"
STUDENTS_DIR = "students"
ATTENDANCE_DIR = "attendance"
FACE_RECOGNITION_TOLERANCE = 0.5


# Database Functions
def init_db():
    """Initialize SQLite database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            image_path TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            date       TEXT NOT NULL,
            time       TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
        """
    )

    conn.commit()
    conn.close()


def ensure_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(STUDENTS_DIR, exist_ok=True)
    os.makedirs(ATTENDANCE_DIR, exist_ok=True)


# Initialize
init_db()
ensure_directories()


# Page Configuration
st.set_page_config(
    page_title="Smart Attendance System",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS for formal styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 600;
        color: #1f2937;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 2px solid #e5e7eb;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: 500;
        color: #374151;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid #3b82f6;
        padding-left: 0.75rem;
    }
    .info-box {
        background-color: #f3f4f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3b82f6;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d1fae5;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #10b981;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #fee2e2;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ef4444;
        margin: 1rem 0;
    }
    .stButton>button {
        width: 100%;
        background-color: #3b82f6;
        color: white;
        font-weight: 500;
        padding: 0.5rem 1rem;
        border-radius: 0.375rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #2563eb;
    }
</style>
""", unsafe_allow_html=True)


# Sidebar Navigation
st.sidebar.title("📋 Navigation")
page = st.sidebar.radio(
    "Select Module",
    ["Register Student", "Mark Attendance", "View Records"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.info(
    "**Smart Attendance System**\n\n"
    "Using Face Recognition Technology\n\n"
    f"Recognition Tolerance: {FACE_RECOGNITION_TOLERANCE}"
)


# ============================================================================
# PAGE 1: REGISTER STUDENT
# ============================================================================
if page == "Register Student":
    st.markdown('<div class="main-header">Register Student</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-header">Student Information</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        student_id = st.text_input("Student ID / Roll Number", placeholder="e.g., BTech001")
    
    with col2:
        student_name = st.text_input("Full Name", placeholder="e.g., John Doe")
    
    st.markdown('<div class="section-header">Upload Photo</div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Select a clear photo with only one face visible",
        type=["jpg", "jpeg", "png"],
        help="Supported formats: JPG, JPEG, PNG"
    )
    
    if uploaded_file is not None:
        # Display uploaded image
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Photo", width=300)
    
    st.markdown("---")
    
    if st.button("Register Student", type="primary"):
        if not student_id or not student_name:
            st.markdown('<div class="error-box">❌ Please enter both Student ID and Name.</div>', unsafe_allow_html=True)
        elif uploaded_file is None:
            st.markdown('<div class="error-box">❌ Please upload a student photo.</div>', unsafe_allow_html=True)
        else:
            with st.spinner("Validating photo..."):
                try:
                    # Save uploaded file temporarily
                    temp_path = f"temp_{uploaded_file.name}"
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Load and validate the image
                    image = face_recognition.load_image_file(temp_path)
                    face_locations = face_recognition.face_locations(image)
                    
                    if len(face_locations) == 0:
                        st.markdown('<div class="error-box">❌ No face detected in the image. Please use a clear photo.</div>', unsafe_allow_html=True)
                        os.remove(temp_path)
                    elif len(face_locations) > 1:
                        st.markdown('<div class="error-box">❌ Multiple faces detected. Please use a photo with only one person.</div>', unsafe_allow_html=True)
                        os.remove(temp_path)
                    else:
                        # Copy image to students folder
                        filename_safe_name = student_name.strip().replace(" ", "_")
                        source_ext = Path(temp_path).suffix or ".jpg"
                        image_filename = f"{student_id}_{filename_safe_name}{source_ext}"
                        dest_path = os.path.join(STUDENTS_DIR, image_filename)
                        
                        shutil.copy2(temp_path, dest_path)
                        os.remove(temp_path)
                        
                        # Save to database
                        conn = sqlite3.connect(DB_PATH)
                        cur = conn.cursor()
                        cur.execute(
                            """
                            INSERT INTO students (student_id, name, image_path)
                            VALUES (?, ?, ?)
                            ON CONFLICT(student_id) DO UPDATE SET
                                name = excluded.name,
                                image_path = excluded.image_path
                            """,
                            (student_id, student_name, dest_path),
                        )
                        conn.commit()
                        conn.close()
                        
                        st.markdown('<div class="success-box">✅ Student registered successfully!</div>', unsafe_allow_html=True)
                        st.balloons()
                        
                except Exception as e:
                    st.markdown(f'<div class="error-box">❌ Error: {str(e)}</div>', unsafe_allow_html=True)
                    if os.path.exists(temp_path):
                        os.remove(temp_path)


# ============================================================================
# PAGE 2: MARK ATTENDANCE
# ============================================================================
elif page == "Mark Attendance":
    st.markdown('<div class="main-header">Mark Attendance</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="info-box">📸 Use your webcam to mark attendance automatically through face recognition.</div>', unsafe_allow_html=True)
    
    # Load registered students
    @st.cache_data
    def load_registered_students():
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT student_id, name, image_path FROM students")
        rows = cur.fetchall()
        conn.close()
        return rows
    
    students = load_registered_students()
    
    if not students:
        st.markdown('<div class="error-box">❌ No registered students found. Please register students first.</div>', unsafe_allow_html=True)
    else:
        st.success(f"✅ {len(students)} student(s) registered in the system")
        
        # Load face encodings
        def load_face_encodings():
            known_face_encodings = []
            known_face_ids = []
            known_face_names = []
            
            for student_id, name, image_path in students:
                if not os.path.exists(image_path):
                    continue
                
                image = face_recognition.load_image_file(image_path)
                encodings = face_recognition.face_encodings(image)
                
                if encodings:
                    known_face_encodings.append(encodings[0])
                    known_face_ids.append(student_id)
                    known_face_names.append(name)
            
            return known_face_encodings, known_face_ids, known_face_names
        
        # Check who has already marked attendance today
        def get_marked_students_today():
            today_str = date.today().strftime("%Y-%m-%d")
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT student_id FROM attendance WHERE date = ?", (today_str,))
            rows = cur.fetchall()
            conn.close()
            return {r[0] for r in rows}
        
        marked_today = get_marked_students_today()
        st.info(f"📊 Already marked today: {len(marked_today)} student(s)")
        
        st.markdown("---")
        st.markdown('<div class="section-header">Camera Control</div>', unsafe_allow_html=True)
        
        run_camera = st.checkbox("Start Camera", value=False)
        
        if run_camera:
            with st.spinner("Loading face encodings..."):
                known_face_encodings, known_face_ids, known_face_names = load_face_encodings()
            
            st.markdown("**Instructions:**")
            st.markdown("- Position your face clearly in front of the camera")
            st.markdown("- Green box = Recognized | Red box = Unknown")
            st.markdown("- Attendance will be marked automatically")
            
            # Create placeholders
            camera_placeholder = st.empty()
            status_placeholder = st.empty()
            
            # Open camera
            cap = cv2.VideoCapture(0)
            
            if not cap.isOpened():
                st.error("❌ Cannot access camera. Please check camera permissions.")
            else:
                students_marked_session = set(marked_today)
                
                stop_button = st.button("Stop Camera", type="primary")
                
                while run_camera and not stop_button:
                    ret, frame = cap.read()
                    if not ret:
                        st.error("❌ Failed to read from camera")
                        break
                    
                    # Resize for faster processing
                    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                    rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                    
                    # Detect faces
                    face_locations = face_recognition.face_locations(rgb_frame)
                    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                    
                    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                        # Scale back to original size
                        top *= 2
                        right *= 2
                        bottom *= 2
                        left *= 2
                        
                        label = "Unknown"
                        color = (255, 0, 0)  # Red
                        
                        if known_face_encodings:
                            distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                            best_match_index = int(np.argmin(distances))
                            best_distance = distances[best_match_index]
                            
                            if best_distance <= FACE_RECOGNITION_TOLERANCE:
                                student_id = known_face_ids[best_match_index]
                                name = known_face_names[best_match_index]
                                label = name
                                color = (0, 255, 0)  # Green
                                
                                # Mark attendance if not already marked
                                if student_id not in students_marked_session:
                                    now = datetime.now()
                                    date_str = now.strftime("%Y-%m-%d")
                                    time_str = now.strftime("%H:%M:%S")
                                    
                                    conn = sqlite3.connect(DB_PATH)
                                    cur = conn.cursor()
                                    cur.execute(
                                        "INSERT INTO attendance (student_id, date, time) VALUES (?, ?, ?)",
                                        (student_id, date_str, time_str),
                                    )
                                    conn.commit()
                                    conn.close()
                                    
                                    students_marked_session.add(student_id)
                                    status_placeholder.success(f"✅ Attendance marked: {name} at {time_str}")
                        
                        # Draw rectangle and label
                        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                        cv2.rectangle(frame, (left, bottom - 25), (right, bottom), color, cv2.FILLED)
                        cv2.putText(frame, label, (left + 6, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                    
                    # Display frame
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    camera_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
                
                cap.release()


# ============================================================================
# PAGE 3: VIEW RECORDS
# ============================================================================
elif page == "View Records":
    st.markdown('<div class="main-header">Attendance Records</div>', unsafe_allow_html=True)
    
    # Filter options
    st.markdown('<div class="section-header">Filters</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_option = st.selectbox(
            "Filter by",
            ["All Records", "Today", "Specific Date", "Specific Student"]
        )
    
    with col2:
        if filter_option == "Specific Date":
            selected_date = st.date_input("Select Date")
        elif filter_option == "Specific Student":
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT student_id, name FROM students ORDER BY name")
            students = cur.fetchall()
            conn.close()
            student_options = {f"{name} ({sid})": sid for sid, name in students}
            selected_student = st.selectbox("Select Student", list(student_options.keys()))
    
    with col3:
        if st.button("Export Report", type="primary"):
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query(
                """
                SELECT s.name AS Name, a.student_id AS 'Student ID', 
                       a.date AS Date, a.time AS Time
                FROM attendance a
                JOIN students s ON a.student_id = s.student_id
                ORDER BY a.date DESC, a.time DESC
                """,
                conn
            )
            conn.close()
            
            if not df.empty:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_path = os.path.join(ATTENDANCE_DIR, f"attendance_report_{timestamp}.csv")
                df.to_csv(report_path, index=False)
                st.success(f"✅ Report exported to: {report_path}")
            else:
                st.warning("⚠️ No records to export")
    
    st.markdown("---")
    
    # Fetch and display records
    conn = sqlite3.connect(DB_PATH)
    
    if filter_option == "All Records":
        query = """
            SELECT s.name AS Name, a.student_id AS 'Student ID', 
                   a.date AS Date, a.time AS Time
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            ORDER BY a.date DESC, a.time DESC
        """
        df = pd.read_sql_query(query, conn)
        st.markdown('<div class="section-header">All Attendance Records</div>', unsafe_allow_html=True)
    
    elif filter_option == "Today":
        today_str = date.today().strftime("%Y-%m-%d")
        query = """
            SELECT s.name AS Name, a.student_id AS 'Student ID', 
                   a.date AS Date, a.time AS Time
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            WHERE a.date = ?
            ORDER BY a.time DESC
        """
        df = pd.read_sql_query(query, conn, params=(today_str,))
        st.markdown(f'<div class="section-header">Today\'s Attendance ({today_str})</div>', unsafe_allow_html=True)
    
    elif filter_option == "Specific Date":
        date_str = selected_date.strftime("%Y-%m-%d")
        query = """
            SELECT s.name AS Name, a.student_id AS 'Student ID', 
                   a.date AS Date, a.time AS Time
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            WHERE a.date = ?
            ORDER BY a.time DESC
        """
        df = pd.read_sql_query(query, conn, params=(date_str,))
        st.markdown(f'<div class="section-header">Attendance for {date_str}</div>', unsafe_allow_html=True)
    
    elif filter_option == "Specific Student":
        student_id = student_options[selected_student]
        query = """
            SELECT s.name AS Name, a.student_id AS 'Student ID', 
                   a.date AS Date, a.time AS Time
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            WHERE a.student_id = ?
            ORDER BY a.date DESC, a.time DESC
        """
        df = pd.read_sql_query(query, conn, params=(student_id,))
        st.markdown(f'<div class="section-header">Attendance History: {selected_student}</div>', unsafe_allow_html=True)
    
    conn.close()
    
    # Display results
    if df.empty:
        st.info("ℹ️ No attendance records found")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown(f"**Total Records:** {len(df)}")
        
        # Summary statistics
        if filter_option != "Specific Student":
            st.markdown("---")
            st.markdown('<div class="section-header">Summary Statistics</div>', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                unique_students = df['Student ID'].nunique()
                st.metric("Unique Students", unique_students)
            
            with col2:
                unique_dates = df['Date'].nunique()
                st.metric("Days Recorded", unique_dates)
            
            with col3:
                total_records = len(df)
                st.metric("Total Records", total_records)


# Footer
st.sidebar.markdown("---")
st.sidebar.markdown(
    "<div style='text-align: center; color: #6b7280; font-size: 0.875rem;'>"
    "Smart Attendance System<br>© 2024"
    "</div>",
    unsafe_allow_html=True
)
