import os
import shutil
import uuid
import json
import random
import time
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.database import get_db_connection, init_db
from app.ai_service import ai_engine

BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

app = FastAPI(title="FixTogether - Smart Road Repair System with AI", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.on_event("startup")
def on_startup():
    from app.seed_data import seed
    db_path = os.path.join(BASE_DIR, "fixtogether.db")
    if not os.path.exists(db_path):
        seed()
    else:
        init_db()

# ----------------- Models -----------------
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    citizen_id: str
    username: str
    password: str
    full_name: str
    phone: str

class VerifyOTPRequest(BaseModel):
    ref_code: str
    otp: str

# In-memory OTP store: ref_code -> { otp, user_data, expires_at }
otp_store = {}

class ApproveCaseRequest(BaseModel):
    technician_id: str
    approved_budget: float
    notes: Optional[str] = None

class RejectCaseRequest(BaseModel):
    reason: str

class InspectWorkOrderRequest(BaseModel):
    decision: str # 'pass' or 'revision'
    notes: Optional[str] = None

class FeedbackRequest(BaseModel):
    user_id: str
    user_name: str
    rating: int
    comments: Optional[str] = None

# ----------------- Auth Endpoints -----------------
@app.post("/api/auth/login")
def login(req: LoginRequest):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE (username = ? OR citizen_id = ?) AND password = ?", (req.username, req.username, req.password)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
    return {
        "status": "success",
        "user": dict(user)
    }

@app.post("/api/auth/register-otp/request")
def request_register_otp(req: RegisterRequest):
    citizen_clean = req.citizen_id.strip()
    if len(citizen_clean) != 13 or not citizen_clean.isdigit():
        raise HTTPException(status_code=400, detail="รหัสประจำตัวประชาชนต้องเป็นตัวเลข 13 หลัก")
    
    phone_clean = req.phone.replace("-", "").replace(" ", "").strip()
    if len(phone_clean) < 9 or not phone_clean.isdigit():
        raise HTTPException(status_code=400, detail="กรุณาระบุหมายเลขโทรศัพท์ให้ถูกต้อง (9-10 หลัก)")

    conn = get_db_connection()
    existing = conn.execute("SELECT user_id FROM users WHERE username = ? OR citizen_id = ?", (req.username.strip(), citizen_clean)).fetchone()
    conn.close()
    if existing:
        raise HTTPException(status_code=400, detail="ชื่อผู้ใช้งานหรือรหัสบัตรประชาชนนี้มีอยู่ในระบบแล้ว")

    otp = f"{random.randint(100000, 999999)}"
    ref_code = f"FT{random.randint(10, 99)}"
    while ref_code in otp_store and time.time() < otp_store[ref_code]["expires_at"]:
        ref_code = f"FT{random.randint(10, 99)}"

    if len(phone_clean) >= 10:
        masked_phone = f"{phone_clean[:3]}-xxx-{phone_clean[-4:]}"
    elif len(phone_clean) >= 9:
        masked_phone = f"{phone_clean[:2]}-xxx-{phone_clean[-4:]}"
    else:
        masked_phone = req.phone

    otp_store[ref_code] = {
        "otp": otp,
        "user_data": {
            "citizen_id": citizen_clean,
            "username": req.username.strip(),
            "password": req.password,
            "full_name": req.full_name.strip(),
            "phone": req.phone.strip()
        },
        "expires_at": time.time() + 300
    }

    return {
        "status": "success",
        "ref_code": ref_code,
        "masked_phone": masked_phone,
        "phone": req.phone,
        "otp": otp,
        "expires_in": 300,
        "message": f"ส่งรหัส OTP ไปยังหมายเลข {masked_phone} แล้ว (Ref: {ref_code})"
    }

@app.post("/api/auth/register-otp/verify")
def verify_register_otp(req: VerifyOTPRequest):
    ref = req.ref_code.strip()
    otp_input = req.otp.strip()

    if ref not in otp_store:
        raise HTTPException(status_code=400, detail="รหัสอ้างอิง OTP ไม่ถูกต้องหรือหมดอายุแล้ว กรุณาขอรหัสใหม่")

    record = otp_store[ref]
    if time.time() > record["expires_at"]:
        del otp_store[ref]
        raise HTTPException(status_code=400, detail="รหัส OTP หมดอายุแล้ว กรุณากดขอรหัสใหม่")

    if otp_input != record["otp"]:
        raise HTTPException(status_code=400, detail="รหัส OTP ไม่ถูกต้อง กรุณาตรวจสอบและลองใหม่อีกครั้ง")

    user_data = record["user_data"]
    conn = get_db_connection()
    existing = conn.execute("SELECT user_id FROM users WHERE username = ? OR citizen_id = ?", (user_data["username"], user_data["citizen_id"])).fetchone()
    if existing:
        conn.close()
        del otp_store[ref]
        raise HTTPException(status_code=400, detail="ชื่อผู้ใช้งานหรือรหัสบัตรประชาชนนี้มีอยู่ในระบบแล้ว")

    user_id = f"U{uuid.uuid4().hex[:6].upper()}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?,?)",
        (user_id, user_data["citizen_id"], user_data["username"], user_data["password"], user_data["full_name"], user_data["phone"], "citizen", None, None, now_str)
    )
    conn.commit()
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    del otp_store[ref]

    return {
        "status": "success",
        "message": "ยืนยันรหัส OTP และลงทะเบียนสำเร็จ!",
        "user": dict(user)
    }

@app.post("/api/auth/register")
def register(req: RegisterRequest):
    conn = get_db_connection()
    # Check duplicate citizen_id or username
    existing = conn.execute("SELECT user_id FROM users WHERE username = ? OR citizen_id = ?", (req.username, req.citizen_id)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="ชื่อผู้ใช้งานหรือรหัสบัตรประชาชนนี้มีอยู่ในระบบแล้ว")
    
    user_id = f"U{uuid.uuid4().hex[:6].upper()}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?,?)",
        (user_id, req.citizen_id, req.username, req.password, req.full_name, req.phone, "citizen", None, None, now_str)
    )
    conn.commit()
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return {"status": "success", "user": dict(user)}

# ----------------- Dashboard & Stats -----------------
@app.get("/api/dashboard/stats")
def get_stats():
    conn = get_db_connection()
    total_cases = conn.execute("SELECT COUNT(*) FROM damage_reports").fetchone()[0]
    pending_review = conn.execute("SELECT COUNT(*) FROM damage_reports WHERE status = 'รอตรวจสอบ'").fetchone()[0]
    in_progress = conn.execute("SELECT COUNT(*) FROM damage_reports WHERE status IN ('เคสถูกสร้าง', 'มอบหมายงานแล้ว', 'กำลังดำเนินการซ่อม', 'รอตรวจรับงาน')").fetchone()[0]
    completed = conn.execute("SELECT COUNT(*) FROM damage_reports WHERE status = 'ปิดงานซ่อมบำรุง'").fetchone()[0]
    rejected = conn.execute("SELECT COUNT(*) FROM damage_reports WHERE status = 'ปฏิเสธเคส'").fetchone()[0]
    
    total_budget = conn.execute("SELECT COALESCE(SUM(approved_budget), 0) FROM work_orders").fetchone()[0]
    avg_rating = conn.execute("SELECT COALESCE(AVG(rating), 0) FROM feedbacks").fetchone()[0]
    total_ratings = conn.execute("SELECT COUNT(*) FROM feedbacks").fetchone()[0]
    
    # Severity breakdown from AI reports
    sev_rows = conn.execute("SELECT severity_level, COUNT(*) as cnt FROM ai_reports GROUP BY severity_level").fetchall()
    severity_dist = {r["severity_level"]: r["cnt"] for r in sev_rows}

    conn.close()
    return {
        "total_cases": total_cases,
        "pending_review": pending_review,
        "in_progress": in_progress,
        "completed": completed,
        "rejected": rejected,
        "total_budget": round(total_budget, 2),
        "avg_rating": round(avg_rating, 1),
        "total_ratings": total_ratings,
        "severity_dist": severity_dist
    }

# ----------------- Technicians list -----------------
@app.get("/api/technicians")
def list_technicians():
    conn = get_db_connection()
    techs = conn.execute("SELECT user_id, full_name, team_name, phone FROM users WHERE role = 'technician'").fetchall()
    conn.close()
    return [dict(t) for t in techs]

# ----------------- Cases Endpoints -----------------
@app.get("/api/cases")
def list_cases(status: Optional[str] = None, reporter_id: Optional[str] = None):
    conn = get_db_connection()
    query = """
    SELECT c.*, 
           a.damage_type, a.severity_level, a.estimated_budget, a.confidence_score,
           w.work_order_id, w.technician_name, w.team_name, w.after_image_url,
           f.rating as feedback_rating, f.comments as feedback_comments
    FROM damage_reports c
    LEFT JOIN ai_reports a ON c.case_id = a.case_id
    LEFT JOIN work_orders w ON c.case_id = w.case_id
    LEFT JOIN feedbacks f ON c.case_id = f.case_id
    WHERE 1=1
    """
    params = []
    if status:
        query += " AND c.status = ?"
        params.append(status)
    if reporter_id:
        query += " AND c.reporter_id = ?"
        params.append(reporter_id)
        
    query += " ORDER BY c.created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/cases/{case_id}")
def get_case_detail(case_id: str):
    conn = get_db_connection()
    c = conn.execute("SELECT * FROM damage_reports WHERE case_id = ?", (case_id,)).fetchone()
    if not c:
        conn.close()
        raise HTTPException(status_code=404, detail="ไม่พบเคสที่ระบุ")
    
    ai = conn.execute("SELECT * FROM ai_reports WHERE case_id = ?", (case_id,)).fetchone()
    wo = conn.execute("SELECT * FROM work_orders WHERE case_id = ?", (case_id,)).fetchone()
    fb = conn.execute("SELECT * FROM feedbacks WHERE case_id = ?", (case_id,)).fetchone()
    conn.close()

    result = dict(c)
    result["ai_report"] = dict(ai) if ai else None
    result["work_order"] = dict(wo) if wo else None
    result["feedback"] = dict(fb) if fb else None
    return result

@app.post("/api/cases")
async def create_case(
    reporter_id: str = Form(...),
    reporter_name: str = Form(...),
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    location_address: str = Form(...),
    image: UploadFile = File(None),
    sample_image_url: Optional[str] = Form(None)
):
    """
    สร้างรายงานแจ้งถนนเสียหาย + วิเคราะห์ด้วย AI ทันที (อัตโนมัติตาม Use Case และ Activity Diagram)
    """
    image_url = "/static/sample_images/pothole_1.jpg"
    local_img_path = os.path.join(STATIC_DIR, "sample_images", "pothole_1.jpg")

    if image and image.filename:
        ext = os.path.splitext(image.filename)[1] or ".jpg"
        unique_name = f"report_{uuid.uuid4().hex[:8]}{ext}"
        save_path = os.path.join(UPLOADS_DIR, unique_name)
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = f"/static/uploads/{unique_name}"
        local_img_path = save_path
    elif sample_image_url:
        image_url = sample_image_url
        filename = os.path.basename(sample_image_url)
        local_img_path = os.path.join(STATIC_DIR, "sample_images", filename)

    # Generate Case ID
    conn = get_db_connection()
    count_row = conn.execute("SELECT COUNT(*) FROM damage_reports").fetchone()[0]
    case_id = f"CASE-2026-{count_row + 1:03d}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Save Damage Report
    conn.execute("""
    INSERT INTO damage_reports VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        case_id, reporter_id, reporter_name, image_url, description,
        latitude, longitude, location_address, "รอตรวจสอบ", None, now_str, now_str
    ))

    # Run AI Analysis
    ai_result = ai_engine.analyze_image(local_img_path, description)
    ai_report_id = f"AIR-2026-{count_row + 1:03d}"
    conn.execute("""
    INSERT INTO ai_reports VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        ai_report_id, case_id, ai_result["model_version"],
        ai_result["damage_type"], ai_result["severity_level"],
        ai_result["estimated_budget"], ai_result["estimated_days"],
        ai_result["confidence_score"], ai_result["detection_boxes"],
        ai_result["recommendation"], ai_result["evaluated_at"]
    ))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "case_id": case_id,
        "ai_report_id": ai_report_id,
        "ai_result": ai_result
    }

# ----------------- Authority Actions -----------------
@app.post("/api/cases/{case_id}/approve")
def approve_case(case_id: str, req: ApproveCaseRequest):
    """
    หน่วยงานอนุมัติเคส + ออกใบงานซ่อม + มอบหมายช่าง (Use Case: อนุมัติการซ่อมบำรุง & ออกใบงานซ่อม)
    """
    conn = get_db_connection()
    case = conn.execute("SELECT * FROM damage_reports WHERE case_id = ?", (case_id,)).fetchone()
    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="ไม่พบเคส")

    tech = conn.execute("SELECT * FROM users WHERE user_id = ?", (req.technician_id,)).fetchone()
    if not tech:
        conn.close()
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลเจ้าหน้าที่ซ่อมบำรุง")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    wo_count = conn.execute("SELECT COUNT(*) FROM work_orders").fetchone()[0]
    work_order_id = f"WO-2026-{wo_count + 1:03d}"

    # Update case status
    conn.execute("""
    UPDATE damage_reports 
    SET status = 'มอบหมายงานแล้ว', updated_at = ?
    WHERE case_id = ?
    """, (now_str, case_id))

    # Insert work order
    conn.execute("""
    INSERT INTO work_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        work_order_id, case_id, tech["user_id"], tech["full_name"],
        tech["team_name"], req.approved_budget, "มอบหมายแล้ว",
        now_str, None, None, None, None, None
    ))

    conn.commit()
    conn.close()
    return {"status": "success", "work_order_id": work_order_id, "message": "อนุมัติและออกใบงานซ่อมเรียบร้อยแล้ว"}

@app.post("/api/cases/{case_id}/approve-create")
def approve_create_case(case_id: str):
    """
    หน่วยงานอนุมัติเคส -> เปลี่ยนสถานะเป็น 'เคสถูกสร้าง' (State Diagram: รอตรวจสอบเคส -> เคสถูกสร้าง)
    """
    conn = get_db_connection()
    case = conn.execute("SELECT * FROM damage_reports WHERE case_id = ?", (case_id,)).fetchone()
    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="ไม่พบเคส")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
    UPDATE damage_reports 
    SET status = 'เคสถูกสร้าง', updated_at = ?
    WHERE case_id = ?
    """, (now_str, case_id))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "อนุมัติเคสเรียบร้อยแล้ว (สถานะเปลี่ยนเป็น 'เคสถูกสร้าง')"}

@app.post("/api/cases/{case_id}/authority-cancel")
def authority_cancel_case(case_id: str):
    """
    หน่วยงานยกเลิกเคส (กรณีไม่พบช่างที่พร้อมปฏิบัติงาน ตาม State Diagram)
    """
    conn = get_db_connection()
    case = conn.execute("SELECT * FROM damage_reports WHERE case_id = ?", (case_id,)).fetchone()
    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="ไม่พบเคส")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
    UPDATE damage_reports 
    SET status = 'ยกเลิกเคส', updated_at = ?
    WHERE case_id = ?
    """, (now_str, case_id))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "ยกเลิกเคสเรียบร้อยแล้ว (รหัสเคสถูกยกเลิก)"}

@app.post("/api/cases/{case_id}/reject")
def reject_case(case_id: str, req: RejectCaseRequest):
    conn = get_db_connection()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
    UPDATE damage_reports 
    SET status = 'ปฏิเสธเคส', reject_reason = ?, updated_at = ?
    WHERE case_id = ?
    """, (req.reason, now_str, case_id))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "ปฏิเสธเคสเรียบร้อยแล้ว"}

# ----------------- Technician Actions -----------------
@app.get("/api/work-orders")
def get_work_orders(technician_id: Optional[str] = None):
    conn = get_db_connection()
    query = """
    SELECT w.*, c.description, c.image_url as before_image_url, c.location_address, c.latitude, c.longitude,
           a.damage_type, a.severity_level, a.estimated_budget, a.estimated_days
    FROM work_orders w
    JOIN damage_reports c ON w.case_id = c.case_id
    LEFT JOIN ai_reports a ON w.case_id = a.case_id
    WHERE 1=1
    """
    params = []
    if technician_id:
        query += " AND w.technician_id = ?"
        params.append(technician_id)
        
    query += " ORDER BY w.issued_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/work-orders/{wo_id}/start")
def start_work_order(wo_id: str):
    conn = get_db_connection()
    wo = conn.execute("SELECT * FROM work_orders WHERE work_order_id = ?", (wo_id,)).fetchone()
    if not wo:
        conn.close()
        raise HTTPException(status_code=404, detail="ไม่พบใบงาน")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
    UPDATE work_orders SET status = 'กำลังดำเนินการซ่อม', started_at = ? WHERE work_order_id = ?
    """, (now_str, wo_id))
    
    conn.execute("""
    UPDATE damage_reports SET status = 'กำลังดำเนินการซ่อม', updated_at = ? WHERE case_id = ?
    """, (now_str, wo["case_id"]))

    conn.commit()
    conn.close()
    return {"status": "success", "message": "เริ่มดำเนินการซ่อมเรียบร้อยแล้ว"}

@app.post("/api/work-orders/{wo_id}/submit")
async def submit_work_order(
    wo_id: str,
    repair_notes: str = Form(...),
    image: UploadFile = File(None),
    sample_after_image_url: Optional[str] = Form(None)
):
    """
    ช่างส่งมอบผลงานซ่อมเสร็จ พร้อมรูปถ่ายหลังซ่อม (Use Case: อัพเดทสถานะงานซ่อม)
    """
    conn = get_db_connection()
    wo = conn.execute("SELECT * FROM work_orders WHERE work_order_id = ?", (wo_id,)).fetchone()
    if not wo:
        conn.close()
        raise HTTPException(status_code=404, detail="ไม่พบใบงาน")

    after_image_url = "/static/sample_images/pothole_1_repaired.jpg"
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1] or ".jpg"
        fname = f"repaired_{uuid.uuid4().hex[:8]}{ext}"
        fpath = os.path.join(UPLOADS_DIR, fname)
        with open(fpath, "wb") as buf:
            shutil.copyfileobj(image.file, buf)
        after_image_url = f"/static/uploads/{fname}"
    elif sample_after_image_url:
        after_image_url = sample_after_image_url

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
    UPDATE work_orders 
    SET status = 'ส่งตรวจรับงาน', completed_at = ?, after_image_url = ?, repair_notes = ?
    WHERE work_order_id = ?
    """, (now_str, after_image_url, repair_notes, wo_id))

    conn.execute("""
    UPDATE damage_reports
    SET status = 'รอตรวจรับงาน', updated_at = ?
    WHERE case_id = ?
    """, (now_str, wo["case_id"]))

    conn.commit()
    conn.close()
    return {"status": "success", "message": "ส่งมอบผลงานซ่อมเสร็จเพื่อรอการตรวจรับแล้ว"}

@app.post("/api/work-orders/{wo_id}/inspect")
def inspect_work_order(wo_id: str, req: InspectWorkOrderRequest):
    """
    หน่วยงานตรวจรับงาน: ผ่านเกณฑ์ (ปิดเคส) หรือ สั่งแก้ไขงาน (Use Case: ปิดงานซ่อมบำรุง)
    """
    conn = get_db_connection()
    wo = conn.execute("SELECT * FROM work_orders WHERE work_order_id = ?", (wo_id,)).fetchone()
    if not wo:
        conn.close()
        raise HTTPException(status_code=404, detail="ไม่พบใบงาน")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if req.decision == "pass":
        conn.execute("""
        UPDATE work_orders 
        SET status = 'ปิดงานซ่อมบำรุงแล้ว', inspection_notes = ?
        WHERE work_order_id = ?
        """, (req.notes or "ตรวจรับงานผ่านเกณฑ์เรียบร้อย", wo_id))

        conn.execute("""
        UPDATE damage_reports
        SET status = 'ปิดงานซ่อมบำรุง', updated_at = ?
        WHERE case_id = ?
        """, (now_str, wo["case_id"]))
        msg = "อนุมัติปิดงานซ่อมบำรุงเรียบร้อยแล้ว"
    else:
        conn.execute("""
        UPDATE work_orders 
        SET status = 'สั่งแก้ไขงาน', inspection_notes = ?
        WHERE work_order_id = ?
        """, (req.notes or "ผลงานยังไม่ผ่านเกณฑ์ ขอให้เข้าแก้ไขเพิ่มเติม", wo_id))

        conn.execute("""
        UPDATE damage_reports
        SET status = 'สั่งแก้ไขงาน', updated_at = ?
        WHERE case_id = ?
        """, (now_str, wo["case_id"]))
        msg = "ส่งคำสั่งแก้ไขงานกลับไปยังทีมช่างแล้ว (สถานะ: สั่งแก้ไขงาน)"

    conn.commit()
    conn.close()
    return {"status": "success", "message": msg}

# ----------------- Cancel Case -----------------
@app.post("/api/cases/{case_id}/cancel")
def cancel_case(case_id: str):
    """
    ประชาชนยกเลิกเคสที่แจ้ง (Use Case: ยกเลิกคำขอแจ้งซ่อม ก่อนหน่วยงานดำเนินการ)
    """
    conn = get_db_connection()
    case = conn.execute("SELECT * FROM damage_reports WHERE case_id = ?", (case_id,)).fetchone()
    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="ไม่พบเคส")

    if case["status"] not in ("รอตรวจสอบ", "เคสถูกสร้าง"):
        conn.close()
        raise HTTPException(status_code=400, detail="สามารถยกเลิกได้เฉพาะเคสที่อยู่ในสถานะ 'รอตรวจสอบ' หรือ 'เคสถูกสร้าง' เท่านั้น")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
    UPDATE damage_reports
    SET status = 'ยกเลิกเคส', updated_at = ?
    WHERE case_id = ?
    """, (now_str, case_id))

    conn.commit()
    conn.close()
    return {"status": "success", "message": "ยกเลิกการแจ้งเคสเรียบร้อยแล้ว"}

# ----------------- Citizen Feedback -----------------
@app.post("/api/cases/{case_id}/feedback")
def submit_feedback(case_id: str, req: FeedbackRequest):
    conn = get_db_connection()
    case = conn.execute("SELECT * FROM damage_reports WHERE case_id = ?", (case_id,)).fetchone()
    if not case:
        conn.close()
        raise HTTPException(status_code=404, detail="ไม่พบเคส")

    if case["status"] != "ปิดงานซ่อมบำรุง":
        conn.close()
        raise HTTPException(status_code=400, detail="สามารถประเมินความพึงพอใจได้เฉพาะเคสที่ปิดงานซ่อมบำรุงแล้วเท่านั้น")

    existing = conn.execute("SELECT feedback_id FROM feedbacks WHERE case_id = ?", (case_id,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="เคสนี้ได้รับการประเมินความพึงพอใจไปแล้ว")

    fb_id = f"FB{uuid.uuid4().hex[:6].upper()}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("""
    INSERT INTO feedbacks VALUES (?,?,?,?,?,?,?)
    """, (fb_id, case_id, req.user_id, req.user_name, req.rating, req.comments or "", now_str))

    conn.commit()
    conn.close()
    return {"status": "success", "feedback_id": fb_id, "message": "บันทึกผลการประเมินความพึงพอใจสำเร็จ"}

# ----------------- Main Web Page -----------------
@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})

