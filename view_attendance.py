import os
import sqlite3
from datetime import date, datetime


DB_PATH = "attendance.db"
ATTENDANCE_DIR = "attendance"


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
    os.makedirs(ATTENDANCE_DIR, exist_ok=True)


def fetch_records_where(where_clause: str = "", params=()):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    base_query = (
        "SELECT s.name, a.student_id, a.date, a.time "
        "FROM attendance a JOIN students s ON a.student_id = s.student_id "
    )

    if where_clause:
        base_query += f"WHERE {where_clause} "

    base_query += "ORDER BY a.date, a.time"

    cur.execute(base_query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def print_records(rows):
    if not rows:
        print("[INFO] No records found.")
        return

    print("\nName                           | Student ID       | Date       | Time")
    print("-" * 70)
    for name, student_id, d, t in rows:
        print(f"{name:<30} | {student_id:<15} | {d:<10} | {t}")
    print("-" * 70)
    print(f"Total records: {len(rows)}\n")


def view_all_records():
    rows = fetch_records_where()
    print_records(rows)


def view_today_records():
    today_str = date.today().strftime("%Y-%m-%d")
    rows = fetch_records_where("a.date = ?", (today_str,))
    print(f"\n[INFO] Showing attendance for today: {today_str}")
    print_records(rows)


def view_by_date():
    d = input("Enter date (YYYY-MM-DD): ").strip()
    if not d:
        print("[ERROR] Date cannot be empty.")
        return

    rows = fetch_records_where("a.date = ?", (d,))
    print(f"\n[INFO] Showing attendance for date: {d}")
    print_records(rows)


def view_by_student():
    sid = input("Enter Student ID / Roll Number: ").strip()
    if not sid:
        print("[ERROR] Student ID cannot be empty.")
        return

    rows = fetch_records_where("a.student_id = ?", (sid,))
    print(f"\n[INFO] Showing attendance history for: {sid}")
    print_records(rows)


def generate_summary_report():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT s.name, a.student_id, COUNT(*) AS total_present
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        GROUP BY a.student_id
        ORDER BY s.name
        """
    )

    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("[INFO] No attendance data to summarize.")
        return

    print("\nName                           | Student ID       | Total Present")
    print("-" * 70)
    for name, student_id, total in rows:
        print(f"{name:<30} | {student_id:<15} | {total}")
    print("-" * 70)
    print(f"Total students with records: {len(rows)}\n")


def export_report_to_file():
    """Export full attendance records to a timestamped text report file."""
    ensure_directories()
    rows = fetch_records_where()
    if not rows:
        print("[INFO] No records to export.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(ATTENDANCE_DIR, f"attendance_report_{timestamp}.txt")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("Name                           | Student ID       | Date       | Time\n")
        f.write("-" * 70 + "\n")
        for name, student_id, d, t in rows:
            f.write(f"{name:<30} | {student_id:<15} | {d:<10} | {t}\n")
        f.write("-" * 70 + "\n")
        f.write(f"Total records: {len(rows)}\n")

    print(f"[SUCCESS] Exported attendance report to: {report_path}")


def main_menu():
    while True:
        print("\n=== Smart Attendance System - View & Reports ===")
        print("1. View all records")
        print("2. View today's attendance")
        print("3. View by specific date")
        print("4. View individual student history")
        print("5. Generate summary report")
        print("6. Export all records to report file")
        print("7. Exit")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            view_all_records()
        elif choice == "2":
            view_today_records()
        elif choice == "3":
            view_by_date()
        elif choice == "4":
            view_by_student()
        elif choice == "5":
            generate_summary_report()
        elif choice == "6":
            export_report_to_file()
        elif choice == "7":
            print("Exiting viewer module.")
            break
        else:
            print("[ERROR] Invalid choice. Please select from 1 to 7.")


if __name__ == "__main__":
    main_menu()
