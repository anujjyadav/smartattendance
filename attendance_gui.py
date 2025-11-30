import os
import sqlite3
import shutil
from datetime import date, datetime
from pathlib import Path
from tkinter import Tk, Frame, Label, Entry, Button, Text, Scrollbar, filedialog, messagebox
from tkinter import ttk
from tkinter import END, VERTICAL, RIGHT, LEFT, BOTH, Y, X, TOP, BOTTOM, W, E

import cv2
import face_recognition
import numpy as np
from PIL import Image, ImageTk


DB_PATH = "attendance.db"
STUDENTS_DIR = "students"
ATTENDANCE_DIR = "attendance"
FACE_RECOGNITION_TOLERANCE = 0.5


def init_db():
    """Create SQLite database and required tables if they don't exist."""
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
    os.makedirs(STUDENTS_DIR, exist_ok=True)
    os.makedirs(ATTENDANCE_DIR, exist_ok=True)


class AttendanceSystemGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Attendance System - Face Recognition")
        self.root.geometry("900x650")
        self.root.resizable(False, False)

        init_db()
        ensure_directories()

        # Variables for attendance marking
        self.camera_running = False
        self.cap = None
        self.known_face_encodings = []
        self.known_face_ids = []
        self.known_face_names = []
        self.students_marked_today = set()

        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # Create tabs
        self.tab_register = Frame(self.notebook, bg="#f0f0f0")
        self.tab_attendance = Frame(self.notebook, bg="#f0f0f0")
        self.tab_view = Frame(self.notebook, bg="#f0f0f0")

        self.notebook.add(self.tab_register, text="📝 Register Student")
        self.notebook.add(self.tab_attendance, text="📸 Mark Attendance")
        self.notebook.add(self.tab_view, text="📊 View Records")

        # Build each tab
        self.build_register_tab()
        self.build_attendance_tab()
        self.build_view_tab()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def build_register_tab(self):
        """Build the student registration tab."""
        frame = Frame(self.tab_register, bg="#f0f0f0")
        frame.pack(padx=20, pady=20, fill=BOTH, expand=True)

        # Title
        title = Label(frame, text="Register New Student", font=("Arial", 18, "bold"), bg="#f0f0f0", fg="#333")
        title.pack(pady=(0, 20))

        # Student ID
        Label(frame, text="Student ID / Roll Number:", font=("Arial", 12), bg="#f0f0f0").pack(anchor=W, pady=(10, 5))
        self.entry_student_id = Entry(frame, font=("Arial", 12), width=40)
        self.entry_student_id.pack(pady=(0, 10))

        # Student Name
        Label(frame, text="Student Name:", font=("Arial", 12), bg="#f0f0f0").pack(anchor=W, pady=(10, 5))
        self.entry_student_name = Entry(frame, font=("Arial", 12), width=40)
        self.entry_student_name.pack(pady=(0, 10))

        # Image path
        Label(frame, text="Student Photo:", font=("Arial", 12), bg="#f0f0f0").pack(anchor=W, pady=(10, 5))
        
        file_frame = Frame(frame, bg="#f0f0f0")
        file_frame.pack(fill=X, pady=(0, 10))
        
        self.entry_image_path = Entry(file_frame, font=("Arial", 10), width=50)
        self.entry_image_path.pack(side=LEFT, padx=(0, 10))
        
        btn_browse = Button(file_frame, text="Browse...", font=("Arial", 10), command=self.browse_image, bg="#4CAF50", fg="white", relief="raised", cursor="hand2")
        btn_browse.pack(side=LEFT)

        # Register button
        btn_register = Button(frame, text="Register Student", font=("Arial", 14, "bold"), command=self.register_student, bg="#2196F3", fg="white", relief="raised", cursor="hand2", padx=30, pady=10)
        btn_register.pack(pady=(20, 10))

        # Status text
        self.register_status = Text(frame, height=8, width=70, font=("Arial", 10), bg="#fff", fg="#333", relief="sunken", bd=2)
        self.register_status.pack(pady=(10, 0))
        scrollbar = Scrollbar(self.register_status)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.register_status.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.register_status.yview)

    def build_attendance_tab(self):
        """Build the attendance marking tab."""
        frame = Frame(self.tab_attendance, bg="#f0f0f0")
        frame.pack(padx=20, pady=20, fill=BOTH, expand=True)

        # Title
        title = Label(frame, text="Mark Attendance - Face Recognition", font=("Arial", 18, "bold"), bg="#f0f0f0", fg="#333")
        title.pack(pady=(0, 20))

        # Camera display
        self.camera_label = Label(frame, bg="#000", width=640, height=480)
        self.camera_label.pack(pady=(0, 20))

        # Control buttons
        btn_frame = Frame(frame, bg="#f0f0f0")
        btn_frame.pack()

        self.btn_start_camera = Button(btn_frame, text="▶ Start Camera", font=("Arial", 12, "bold"), command=self.start_attendance, bg="#4CAF50", fg="white", relief="raised", cursor="hand2", padx=20, pady=10)
        self.btn_start_camera.pack(side=LEFT, padx=10)

        self.btn_stop_camera = Button(btn_frame, text="⬛ Stop Camera", font=("Arial", 12, "bold"), command=self.stop_attendance, bg="#f44336", fg="white", relief="raised", cursor="hand2", padx=20, pady=10, state="disabled")
        self.btn_stop_camera.pack(side=LEFT, padx=10)

        # Status text
        self.attendance_status = Text(frame, height=6, width=80, font=("Arial", 10), bg="#fff", fg="#333", relief="sunken", bd=2)
        self.attendance_status.pack(pady=(20, 0))
        scrollbar = Scrollbar(self.attendance_status)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.attendance_status.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.attendance_status.yview)

    def build_view_tab(self):
        """Build the view records tab."""
        frame = Frame(self.tab_view, bg="#f0f0f0")
        frame.pack(padx=20, pady=20, fill=BOTH, expand=True)

        # Title
        title = Label(frame, text="Attendance Records", font=("Arial", 18, "bold"), bg="#f0f0f0", fg="#333")
        title.pack(pady=(0, 20))

        # Filter options
        filter_frame = Frame(frame, bg="#f0f0f0")
        filter_frame.pack(fill=X, pady=(0, 10))

        Label(filter_frame, text="Filter by:", font=("Arial", 11), bg="#f0f0f0").pack(side=LEFT, padx=(0, 10))

        btn_all = Button(filter_frame, text="All Records", font=("Arial", 10), command=lambda: self.view_records("all"), bg="#2196F3", fg="white", cursor="hand2", padx=10, pady=5)
        btn_all.pack(side=LEFT, padx=5)

        btn_today = Button(filter_frame, text="Today", font=("Arial", 10), command=lambda: self.view_records("today"), bg="#FF9800", fg="white", cursor="hand2", padx=10, pady=5)
        btn_today.pack(side=LEFT, padx=5)

        btn_export = Button(filter_frame, text="💾 Export Report", font=("Arial", 10), command=self.export_report, bg="#4CAF50", fg="white", cursor="hand2", padx=10, pady=5)
        btn_export.pack(side=LEFT, padx=5)

        # Records display
        self.records_text = Text(frame, height=25, width=100, font=("Courier", 10), bg="#fff", fg="#333", relief="sunken", bd=2)
        self.records_text.pack(pady=(10, 0), fill=BOTH, expand=True)
        
        scrollbar = Scrollbar(self.records_text)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.records_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.records_text.yview)

    def browse_image(self):
        """Open file dialog to select student image."""
        file_path = filedialog.askopenfilename(
            title="Select Student Photo",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All Files", "*.*")]
        )
        if file_path:
            self.entry_image_path.delete(0, END)
            self.entry_image_path.insert(0, file_path)

    def register_student(self):
        """Register a student with manual photo upload."""
        student_id = self.entry_student_id.get().strip()
        name = self.entry_student_name.get().strip()
        image_path = self.entry_image_path.get().strip()

        self.register_status.delete(1.0, END)

        if not student_id or not name:
            self.register_status.insert(END, "[ERROR] Student ID and Name cannot be empty.\n")
            return

        if not image_path:
            self.register_status.insert(END, "[ERROR] Please select a student photo.\n")
            return

        if not os.path.exists(image_path):
            self.register_status.insert(END, f"[ERROR] Image file not found: {image_path}\n")
            return

        self.register_status.insert(END, "[INFO] Validating image...\n")
        self.root.update()

        try:
            # Load and validate the image
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)

            if len(face_locations) == 0:
                self.register_status.insert(END, "[ERROR] No face detected in the image. Please use a clear photo.\n")
                return
            if len(face_locations) > 1:
                self.register_status.insert(END, "[ERROR] Multiple faces detected. Please use a photo with only one person.\n")
                return

            # Copy image to students folder
            filename_safe_name = name.strip().replace(" ", "_")
            source_ext = Path(image_path).suffix or ".jpg"
            image_filename = f"{student_id}_{filename_safe_name}{source_ext}"
            dest_path = os.path.join(STUDENTS_DIR, image_filename)

            shutil.copy2(image_path, dest_path)
            self.register_status.insert(END, f"[INFO] Image copied to: {dest_path}\n")

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
                (student_id, name, dest_path),
            )
            conn.commit()
            conn.close()

            self.register_status.insert(END, "[SUCCESS] Student registered successfully!\n")
            messagebox.showinfo("Success", f"Student {name} registered successfully!")

            # Clear fields
            self.entry_student_id.delete(0, END)
            self.entry_student_name.delete(0, END)
            self.entry_image_path.delete(0, END)

        except Exception as e:
            self.register_status.insert(END, f"[ERROR] {str(e)}\n")
            messagebox.showerror("Error", str(e))

    def load_registered_faces(self):
        """Load all registered student face encodings."""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT student_id, name, image_path FROM students")
        rows = cur.fetchall()
        conn.close()

        self.known_face_encodings = []
        self.known_face_ids = []
        self.known_face_names = []

        if not rows:
            return False

        for student_id, name, image_path in rows:
            if not os.path.exists(image_path):
                continue

            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)

            if encodings:
                self.known_face_encodings.append(encodings[0])
                self.known_face_ids.append(student_id)
                self.known_face_names.append(name)

        return len(self.known_face_encodings) > 0

    def load_marked_students_today(self):
        """Load students who already marked attendance today."""
        today_str = date.today().strftime("%Y-%m-%d")
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT student_id FROM attendance WHERE date = ?", (today_str,))
        rows = cur.fetchall()
        conn.close()
        self.students_marked_today = {r[0] for r in rows}

    def mark_attendance(self, student_id, name):
        """Mark attendance in database and log to status."""
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

        msg = f"[MARKED] {name} ({student_id}) at {time_str}\n"
        self.attendance_status.insert(END, msg)
        self.attendance_status.see(END)

    def start_attendance(self):
        """Start the camera and face recognition for attendance."""
        self.attendance_status.delete(1.0, END)
        self.attendance_status.insert(END, "[INFO] Loading registered students...\n")
        self.root.update()

        if not self.load_registered_faces():
            self.attendance_status.insert(END, "[ERROR] No registered students found. Please register students first.\n")
            messagebox.showerror("Error", "No registered students found!")
            return

        self.attendance_status.insert(END, f"[INFO] Loaded {len(self.known_face_encodings)} student(s).\n")
        self.load_marked_students_today()
        self.attendance_status.insert(END, f"[INFO] Already marked today: {len(self.students_marked_today)} student(s).\n")
        self.attendance_status.insert(END, "[INFO] Starting camera...\n")
        self.root.update()

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.attendance_status.insert(END, "[ERROR] Could not open camera.\n")
            messagebox.showerror("Error", "Could not open camera!")
            return

        self.camera_running = True
        self.btn_start_camera.config(state="disabled")
        self.btn_stop_camera.config(state="normal")

        self.attendance_status.insert(END, "[INFO] Camera started. Stand in front of camera.\n")
        self.attendance_status.insert(END, "Green = Recognized | Red = Unknown\n")

        # Start camera processing loop
        self.process_camera()

    def process_camera(self):
        """Process camera frames for face recognition."""
        if not self.camera_running:
            return
            
        ret, frame = self.cap.read()
        if not ret:
            self.stop_attendance()
            return

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
            color = (0, 0, 255)  # Red

            if self.known_face_encodings:
                distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                best_match_index = int(np.argmin(distances))
                best_distance = distances[best_match_index]

                if best_distance <= FACE_RECOGNITION_TOLERANCE:
                    student_id = self.known_face_ids[best_match_index]
                    name = self.known_face_names[best_match_index]
                    label = name
                    color = (0, 255, 0)  # Green

                    # Mark attendance if not already marked today
                    if student_id not in self.students_marked_today:
                        self.mark_attendance(student_id, name)
                        self.students_marked_today.add(student_id)

            # Draw rectangle and label
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom - 25), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame, label, (left + 6, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        # Display frame in GUI
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        img = img.resize((640, 480))
        imgtk = ImageTk.PhotoImage(image=img)
        self.camera_label.imgtk = imgtk
        self.camera_label.configure(image=imgtk)
        
        # Schedule next frame (approx 30 FPS)
        self.root.after(33, self.process_camera)

    def stop_attendance(self):
        """Stop the camera."""
        self.camera_running = False
        if self.cap:
            self.cap.release()
        self.camera_label.configure(image="")
        self.btn_start_camera.config(state="normal")
        self.btn_stop_camera.config(state="disabled")
        self.attendance_status.insert(END, "[INFO] Camera stopped.\n")

    def view_records(self, filter_type):
        """Display attendance records based on filter."""
        self.records_text.delete(1.0, END)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        if filter_type == "all":
            cur.execute(
                "SELECT s.name, a.student_id, a.date, a.time FROM attendance a "
                "JOIN students s ON a.student_id = s.student_id ORDER BY a.date DESC, a.time DESC"
            )
            self.records_text.insert(END, "=== All Attendance Records ===\n\n")
        elif filter_type == "today":
            today_str = date.today().strftime("%Y-%m-%d")
            cur.execute(
                "SELECT s.name, a.student_id, a.date, a.time FROM attendance a "
                "JOIN students s ON a.student_id = s.student_id WHERE a.date = ? ORDER BY a.time DESC",
                (today_str,)
            )
            self.records_text.insert(END, f"=== Today's Attendance ({today_str}) ===\n\n")

        rows = cur.fetchall()
        conn.close()

        if not rows:
            self.records_text.insert(END, "No records found.\n")
            return

        self.records_text.insert(END, f"{'Name':<30} | {'Student ID':<15} | {'Date':<12} | {'Time'}\n")
        self.records_text.insert(END, "-" * 80 + "\n")

        for name, student_id, d, t in rows:
            self.records_text.insert(END, f"{name:<30} | {student_id:<15} | {d:<12} | {t}\n")

        self.records_text.insert(END, f"\nTotal records: {len(rows)}\n")

    def export_report(self):
        """Export attendance records to a text file."""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT s.name, a.student_id, a.date, a.time FROM attendance a "
            "JOIN students s ON a.student_id = s.student_id ORDER BY a.date, a.time"
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            messagebox.showinfo("Info", "No records to export.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(ATTENDANCE_DIR, f"attendance_report_{timestamp}.txt")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("Smart Attendance System - Attendance Report\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"{'Name':<30} | {'Student ID':<15} | {'Date':<12} | {'Time'}\n")
            f.write("-" * 80 + "\n")
            for name, student_id, d, t in rows:
                f.write(f"{name:<30} | {student_id:<15} | {d:<12} | {t}\n")
            f.write(f"\nTotal records: {len(rows)}\n")

        messagebox.showinfo("Success", f"Report exported to:\n{report_path}")

    def on_closing(self):
        """Handle window close event."""
        if self.camera_running:
            self.stop_attendance()
        self.root.destroy()


if __name__ == "__main__":
    root = Tk()
    app = AttendanceSystemGUI(root)
    root.mainloop()
