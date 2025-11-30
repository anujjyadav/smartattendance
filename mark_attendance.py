import csv
import os
import sqlite3
from datetime import datetime, date

import cv2
import face_recognition
import numpy as np


DB_PATH = "attendance.db"
STUDENTS_DIR = "students"
ATTENDANCE_DIR = "attendance"
ATTENDANCE_CSV = os.path.join(ATTENDANCE_DIR, "attendance.csv")

# Stricter than default (0.6) as requested
FACE_RECOGNITION_TOLERANCE = 0.5


def init_db():
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


def load_registered_faces():
    """Load all registered student face encodings from their stored images."""
    init_db()
    ensure_directories()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT student_id, name, image_path FROM students")
    rows = cur.fetchall()
    conn.close()

    known_face_encodings = []
    known_face_ids = []
    known_face_names = []

    if not rows:
        print("[WARN] No registered students found. Please run register_student.py first.")
        return known_face_encodings, known_face_ids, known_face_names

    print(f"[INFO] Loading {len(rows)} registered student(s)...")

    for student_id, name, image_path in rows:
        if not os.path.exists(image_path):
            print(f"[WARN] Image file not found for {student_id} - {name}: {image_path}")
            continue

        image = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(image)

        if not encodings:
            print(f"[WARN] No face encoding found in image for {student_id} - {name}. Skipping.")
            continue

        known_face_encodings.append(encodings[0])
        known_face_ids.append(student_id)
        known_face_names.append(name)

    print(f"[INFO] Loaded encodings for {len(known_face_encodings)} student(s).")
    return known_face_encodings, known_face_ids, known_face_names


def load_marked_students_today() -> set:
    today_str = date.today().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT student_id FROM attendance WHERE date = ?", (today_str,))
    rows = cur.fetchall()
    conn.close()

    return {r[0] for r in rows}


def append_to_csv(name: str, student_id: str, date_str: str, time_str: str):
    ensure_directories()
    file_exists = os.path.exists(ATTENDANCE_CSV)

    with open(ATTENDANCE_CSV, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Name", "Student ID", "Date", "Time"])
        writer.writerow([name, student_id, date_str, time_str])


def mark_attendance(student_id: str, name: str):
    """Insert attendance into SQLite and append to CSV, avoiding duplicates via caller logic."""
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

    append_to_csv(name, student_id, date_str, time_str)
    print(f"[MARKED] {name} ({student_id}) at {date_str} {time_str}")


def run_attendance():
    init_db()
    ensure_directories()

    known_face_encodings, known_face_ids, known_face_names = load_registered_faces()
    if not known_face_encodings:
        print("[ERROR] No valid student encodings loaded. Exiting.")
        return

    students_marked_today = load_marked_students_today()
    print(f"[INFO] Already marked today: {len(students_marked_today)} student(s).")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Could not open camera. Make sure it is connected and not used by another app.")
        return

    print("\n[INFO] Attendance system started.\n" \
          "Stand in front of the camera. Recognized faces will be marked automatically.\n" \
          "Green rectangle = Recognized, Red rectangle = Unknown.\n" \
          "Press 'q' to quit.\n")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Failed to read from camera.")
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

            face_labels = []  # for display

            for face_encoding in face_encodings:
                if not known_face_encodings:
                    face_labels.append("Unknown")
                    continue

                distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                best_match_index = int(np.argmin(distances))
                best_distance = distances[best_match_index]

                if best_distance <= FACE_RECOGNITION_TOLERANCE:
                    student_id = known_face_ids[best_match_index]
                    name = known_face_names[best_match_index]
                    face_labels.append(name)

                    # Duplicate prevention for the current day
                    if student_id not in students_marked_today:
                        mark_attendance(student_id, name)
                        students_marked_today.add(student_id)
                else:
                    face_labels.append("Unknown")

            # Draw rectangles and labels
            for (top, right, bottom, left), label in zip(face_locations, face_labels):
                if label == "Unknown":
                    color = (0, 0, 255)  # Red
                else:
                    color = (0, 255, 0)  # Green

                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(frame, (left, bottom - 25), (right, bottom), color, cv2.FILLED)
                cv2.putText(
                    frame,
                    label,
                    (left + 6, bottom - 6),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )

            cv2.imshow("Smart Attendance - Press 'q' to quit", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q")):
                print("[INFO] Quitting attendance system.")
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    run_attendance()
