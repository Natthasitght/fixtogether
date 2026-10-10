import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "fixtogether.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. D1 ข้อมูลส่วนตัว / ผู้ใช้งาน (Users)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        citizen_id TEXT UNIQUE,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT,
        role TEXT NOT NULL, -- 'citizen', 'authority', 'technician'
        department TEXT,
        team_name TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # 2. D2 ข้อมูลความเสียหาย / เคสแจ้งซ่อม (Damage Reports)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS damage_reports (
        case_id TEXT PRIMARY KEY,
        reporter_id TEXT NOT NULL,
        reporter_name TEXT NOT NULL,
        image_url TEXT NOT NULL,
        description TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        location_address TEXT,
        status TEXT NOT NULL, -- 'รอตรวจสอบ', 'เคสถูกสร้าง', 'ปฏิเสธเคส', 'มอบหมายงานแล้ว', 'กำลังดำเนินการซ่อม', 'รอตรวจรับงาน', 'ปิดงานซ่อมบำรุง', 'ยกเลิกเคส'
        reject_reason TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (reporter_id) REFERENCES users (user_id)
    );
    """)

    # 3. D3 ข้อมูลสถิติและการประเมิน AI (AI Reports)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_reports (
        ai_report_id TEXT PRIMARY KEY,
        case_id TEXT UNIQUE NOT NULL,
        model_version TEXT NOT NULL,
        damage_type TEXT NOT NULL,
        severity_level TEXT NOT NULL, -- 'ต่ำ', 'ปานกลาง', 'สูง', 'วิกฤต'
        estimated_budget REAL NOT NULL,
        estimated_days INTEGER NOT NULL,
        confidence_score REAL NOT NULL,
        detection_boxes TEXT, -- JSON array of box coordinates
        recommendation TEXT,
        evaluated_at TEXT NOT NULL,
        FOREIGN KEY (case_id) REFERENCES damage_reports (case_id)
    );
    """)

    # 4. D4 ข้อมูลหน่วยงานผู้ดูแลพื้นที่ (Departments)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        dept_id TEXT PRIMARY KEY,
        dept_name TEXT NOT NULL,
        area_name TEXT NOT NULL,
        contact_phone TEXT
    );
    """)

    # 5. D5 ข้อมูลการซ่อม / ใบงานซ่อม (Repair Work Orders)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS work_orders (
        work_order_id TEXT PRIMARY KEY,
        case_id TEXT UNIQUE NOT NULL,
        technician_id TEXT NOT NULL,
        technician_name TEXT NOT NULL,
        team_name TEXT,
        approved_budget REAL NOT NULL,
        status TEXT NOT NULL, -- 'มอบหมายแล้ว', 'กำลังดำเนินการซ่อม', 'ส่งตรวจรับงาน', 'สั่งแก้ไขงาน', 'ปิดงานซ่อมบำรุงแล้ว'
        issued_at TEXT NOT NULL,
        started_at TEXT,
        completed_at TEXT,
        after_image_url TEXT,
        repair_notes TEXT,
        inspection_notes TEXT,
        FOREIGN KEY (case_id) REFERENCES damage_reports (case_id),
        FOREIGN KEY (technician_id) REFERENCES users (user_id)
    );
    """)

    # 6. D6 ข้อมูลความพึงพอใจ (Feedbacks)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedbacks (
        feedback_id TEXT PRIMARY KEY,
        case_id TEXT UNIQUE NOT NULL,
        user_id TEXT NOT NULL,
        user_name TEXT NOT NULL,
        rating INTEGER NOT NULL, -- 1-5
        comments TEXT,
        submitted_at TEXT NOT NULL,
        FOREIGN KEY (case_id) REFERENCES damage_reports (case_id),
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    );
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database schema initialized successfully.")
