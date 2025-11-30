import os
import sqlite3
import shutil
from pathlib import Path

import face_recognition


DB_PATH = "attendance.db"
STUDENTS_DIR = "students"


def init_db():
    """Create SQLite database and required tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Students table: one row per student, one image path per student
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            image_path TEXT NOT NULL
        )
        """
    )

    # Attendance table: used by mark_attendance.py
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


def validate_and_copy_image(source_path: str, student_id: str, name: str) -> str:
    """Validate the uploaded image has exactly one face and copy it to students folder.

    Returns the destination image path.
    """
    ensure_directories()

    # Check if source file exists
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Image file not found: {source_path}")

    # Load and validate the image
    try:
        image = face_recognition.load_image_file(source_path)
    except Exception as e:
        raise RuntimeError(f"Failed to load image. Make sure it's a valid image file (jpg, png, etc.). Error: {e}")

    # Validate that exactly one face is present
    face_locations = face_recognition.face_locations(image)

    if len(face_locations) == 0:
        raise RuntimeError("No face detected in the image. Please use a clear photo with a visible face.")
    if len(face_locations) > 1:
        raise RuntimeError("Multiple faces detected. Please use a photo with only one person.")

    # Create destination filename
    filename_safe_name = name.strip().replace(" ", "_")
    source_ext = Path(source_path).suffix
    if not source_ext:
        source_ext = ".jpg"
    image_filename = f"{student_id}_{filename_safe_name}{source_ext}"
    dest_path = os.path.join(STUDENTS_DIR, image_filename)

    # Copy the image to students folder
    shutil.copy2(source_path, dest_path)
    print(f"[INFO] Image copied to: {dest_path}")

    return dest_path


def register_student():
    """CLI flow to register one student (one photo per student)."""
    student_id = input("Enter Student ID / Roll Number: ").strip()
    name = input("Enter Student Name: ").strip()

    if not student_id or not name:
        print("[ERROR] Student ID and Name cannot be empty.")
        return

    # Get image path from user
    print("\nEnter the full path to the student's photo.")
    print("Example: C:\\Users\\Photos\\student.jpg or D:\\Images\\photo.png")
    source_image_path = input("Image path: ").strip().strip('"').strip("'")

    if not source_image_path:
        print("[ERROR] Image path cannot be empty.")
        return

    init_db()

    try:
        dest_image_path = validate_and_copy_image(source_image_path, student_id, name)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"[ERROR] {e}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Upsert student record
    cur.execute(
        """
        INSERT INTO students (student_id, name, image_path)
        VALUES (?, ?, ?)
        ON CONFLICT(student_id) DO UPDATE SET
            name = excluded.name,
            image_path = excluded.image_path
        """,
        (student_id, name, dest_image_path),
    )

    conn.commit()
    conn.close()

    print("[SUCCESS] Student registered/updated successfully.")


def main_menu():
    while True:
        print("\n=== Smart Attendance System - Student Registration ===")
        print("1. Register New Student")
        print("2. Exit")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            register_student()
        elif choice == "2":
            print("Exiting registration module.")
            break
        else:
            print("[ERROR] Invalid choice. Please select 1 or 2.")


if __name__ == "__main__":
    main_menu()
