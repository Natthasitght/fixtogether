import os
import json
from datetime import datetime, timedelta
from app.database import init_db, get_db_connection

def seed():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing demo data
    cursor.execute("DELETE FROM feedbacks")
    cursor.execute("DELETE FROM work_orders")
    cursor.execute("DELETE FROM ai_reports")
    cursor.execute("DELETE FROM damage_reports")
    cursor.execute("DELETE FROM departments")
    cursor.execute("DELETE FROM users")

    now = datetime.now()

    # 1. Users (Citizen, Authority, Technicians)
    users = [
        ("U001", "1100500123456", "somchai", "1234", "นายสมชาย รักสะอาด", "081-234-5678", "citizen", None, None, now.strftime("%Y-%m-%d %H:%M:%S")),
        ("U002", "3100100987654", "admin_bma", "1234", "น.ส.วิภาดา โยธาธิการ", "02-224-4681", "authority", "สำนักการโยธาและผังเมือง", None, now.strftime("%Y-%m-%d %H:%M:%S")),
        ("U003", "3101400554433", "mechanic_jack", "1234", "นายเอกชัย มุ่งมั่น", "089-876-5432", "technician", None, "ทีมช่างซ่อมบำรุง 01 (จตุจักร-พหลโยธิน)", now.strftime("%Y-%m-%d %H:%M:%S")),
        ("U004", "3101400998877", "mechanic_sompong", "1234", "นายสมพงษ์ ฝีมือดี", "086-555-4321", "technician", None, "ทีมช่างซ่อมบำรุง 02 (สุขุมวิท-พระราม4)", now.strftime("%Y-%m-%d %H:%M:%S"))
    ]
    cursor.executemany("INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?,?)", users)

    # 2. Departments
    departments = [
        ("DEPT-01", "สำนักการโยธาและผังเมือง", "เขตพื้นที่ชั้นใน", "02-224-4681"),
        ("DEPT-02", "ฝ่ายโยธา สำนักงานเขตจตุจักร", "เขตจตุจักร และพื้นที่เชื่อมต่อ", "02-513-3444")
    ]
    cursor.executemany("INSERT INTO departments VALUES (?,?,?,?)", departments)

    # 3. Cases & Comprehensive State coverage (State Diagram: รอตรวจสอบ, ปฏิเสธเคส, มอบหมายงานแล้ว, กำลังดำเนินการซ่อม, รอตรวจรับงาน, ปิดงานซ่อมบำรุง, ยกเลิกเคส)

    # Case 1: ปิดงานซ่อมบำรุงแล้ว (Closed) + ประเมินความพึงพอใจ 5 ดาว + รูปก่อน-หลังซ่อม
    c1_time = (now - timedelta(days=6)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO damage_reports VALUES (
        'CASE-2026-001', 'U001', 'นายสมชาย รักสะอาด',
        '/static/sample_images/pothole_1.jpg',
        'พบหลุมบ่อขนาดใหญ่กลางเลนซ้าย รถจักรยานยนต์และรถยนต์ต้องหักหลบกะทันหัน เสี่ยงอุบัติเหตุมากครับ',
        13.8034, 100.5538, 'ถ.พหลโยธิน หน้าสวนจตุจักร เขตจตุจักร',
        'ปิดงานซ่อมบำรุง', NULL, ?, ?
    )""", (c1_time, (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")))

    cursor.execute("""
    INSERT INTO ai_reports VALUES (
        'AIR-2026-001', 'CASE-2026-001', 'RoadVision-v2.4-DeepSense',
        'หลุมบ่อบนผิวจราจร (Standard Pothole)', 'สูง',
        15000.0, 2, 95.8,
        '[{"x": 210, "y": 140, "width": 220, "height": 150, "label": "Pothole", "confidence": 95.8}]',
        'ตัดแต่งขอบหลุมเป็นแนวตรง ลงหินคลุกบดอัดแน่น และปูผิวแอสฟัลต์คอนกรีตผสมร้อน บดอัดเรียบเสมอผิวเดิม',
        ?
    )""", (c1_time,))

    cursor.execute("""
    INSERT INTO work_orders VALUES (
        'WO-2026-001', 'CASE-2026-001', 'U003', 'นายเอกชัย มุ่งมั่น',
        'ทีมช่างซ่อมบำรุง 01 (จตุจักร-พหลโยธิน)', 15000.0,
        'ปิดงานซ่อมบำรุงแล้ว',
        ?, ?, ?,
        '/static/sample_images/pothole_1_repaired.jpg',
        'ดำเนินการปรับพื้นผิวทาง ลงยางมะตอยผสมร้อน บดอัดเรียบเนียน และเปิดการจราจรตามปกติแล้วครับ',
        'เจ้าหน้าที่เขตเข้าตรวจสอบแล้ว งานเรียบร้อย ผิวทางราบเรียบเสมอกัน อนุมัติปิดงานซ่อมบำรุง'
    )""", (
        (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"),
        (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S"),
        (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    ))

    cursor.execute("""
    INSERT INTO feedbacks VALUES (
        'FB-2026-001', 'CASE-2026-001', 'U001', 'นายสมชาย รักสะอาด',
        5, 'ซ่อมรวดเร็วมากครับ ทีมช่างทำงานเรียบร้อย ถนนกลับมาใช้งานได้ปลอดภัย ขอบคุณครับ',
        ?
    )""", ((now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),))

    # Case 2: กำลังดำเนินการซ่อม (In Progress)
    c2_time = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO damage_reports VALUES (
        'CASE-2026-002', 'U001', 'นายสมชาย รักสะอาด',
        '/static/sample_images/crack_1.jpg',
        'ผิวถนนแตกลายงาเป็นบริเวณกว้าง เลี้ยวเข้าซอยแล้วสะเทือนมาก มีเศษหินกระเด็น',
        13.7383, 100.5604, 'ถ.สุขุมวิท ซอย 21 (อโศกมนตรี) วัฒนา',
        'กำลังดำเนินการซ่อม', NULL, ?, ?
    )""", (c2_time, (now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")))

    cursor.execute("""
    INSERT INTO ai_reports VALUES (
        'AIR-2026-002', 'CASE-2026-002', 'RoadVision-v2.4-DeepSense',
        'รอยแตกลายจระเข้ (Alligator Cracking)', 'ปานกลาง',
        11000.0, 2, 93.4,
        '[{"x": 160, "y": 90, "width": 300, "height": 220, "label": "Alligator Cracking", "confidence": 93.4}]',
        'ขูดไสผิวทางแตกร่อนออก (Cold Milling) หนา 3-5 ซม. แล้วปูแอสฟัลต์ทับหน้าใหม่',
        ?
    )""", (c2_time,))

    cursor.execute("""
    INSERT INTO work_orders VALUES (
        'WO-2026-002', 'CASE-2026-002', 'U004', 'นายสมพงษ์ ฝีมือดี',
        'ทีมช่างซ่อมบำรุง 02 (สุขุมวิท-พระราม4)', 11000.0,
        'กำลังดำเนินการซ่อม',
        ?, ?, NULL, NULL,
        'นำเครื่องจักรเข้าพื้นที่แล้ว กำลังขูดลอกผิวถนนที่แตกร้าว และเตรียมราดยางมะตอยช่วงดึก',
        NULL
    )""", (
        (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        (now - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
    ))

    # Case 3: รอตรวจรับงาน (Under Inspection) + มีรูปหลังซ่อมจากช่างพร้อมตรวจรับ
    c3_time = (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO damage_reports VALUES (
        'CASE-2026-003', 'U001', 'นายสมชาย รักสะอาด',
        '/static/sample_images/depression_1.jpg',
        'ถนนทรุดตัวเป็นแอ่งกว้าง ฝนตกแล้วน้ำขัง รถวิ่งผ่านน้ำสาดคนเดินเท้า',
        13.7297, 100.5365, 'ถ.พระราม 4 หน้าสวนลุมพินี ปทุมวัน',
        'รอตรวจรับงาน', NULL, ?, ?
    )""", (c3_time, (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")))

    cursor.execute("""
    INSERT INTO ai_reports VALUES (
        'AIR-2026-003', 'CASE-2026-003', 'RoadVision-v2.4-DeepSense',
        'ผิวทางทรุดตัว (Road Depression)', 'สูง',
        26000.0, 3, 91.5,
        '[{"x": 170, "y": 120, "width": 300, "height": 190, "label": "Depression", "confidence": 91.5}]',
        'เสริมระดับชั้นโครงสร้างทาง เติมวัสดุรองพื้นทางและปูทับด้วยแอสฟัลต์คอนกรีตเสริมแรง',
        ?
    )""", (c3_time,))

    cursor.execute("""
    INSERT INTO work_orders VALUES (
        'WO-2026-003', 'CASE-2026-003', 'U004', 'นายสมพงษ์ ฝีมือดี',
        'ทีมช่างซ่อมบำรุง 02 (สุขุมวิท-พระราม4)', 26000.0,
        'ส่งตรวจรับงาน',
        ?, ?, ?,
        '/static/sample_images/depression_1_repaired.jpg',
        'ปรับระดับแอ่งทรุดและลาดยางมะตอยใหม่เรียบร้อยแล้ว ผิวถนนได้ระดับเสมอแนวท่อระบายน้ำ พร้อมเปิดการจราจร',
        NULL
    )""", (
        (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
        (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
    ))

    # Case 4: รอตรวจสอบ (Pending Review by Authority)
    c4_time = (now - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO damage_reports VALUES (
        'CASE-2026-004', 'U001', 'นายสมชาย รักสะอาด',
        '/static/sample_images/pothole_1.jpg',
        'หลุมลึกใต้สะพานลอยคนข้าม รถยนต์กระแทกเสียงดังมาก กลางคืนมองไม่เห็นไฟส่องสว่างน้อย',
        13.8185, 100.5623, 'ถ.วิภาวดีรังสิต ขาเข้า ใกล้แยกลาดพร้าว จตุจักร',
        'รอตรวจสอบ', NULL, ?, ?
    )""", (c4_time, c4_time))

    cursor.execute("""
    INSERT INTO ai_reports VALUES (
        'AIR-2026-004', 'CASE-2026-004', 'RoadVision-v2.4-DeepSense',
        'หลุมบ่อขนาดใหญ่และลึก (Severe Pothole)', 'วิกฤต',
        32000.0, 3, 96.2,
        '[{"x": 200, "y": 130, "width": 240, "height": 170, "label": "Severe Pothole", "confidence": 96.2}]',
        'จัดส่งทีมซ่อมเร่งด่วน ติดตั้งป้ายเตือนชั่วคราว ขุดเปิดปากหลุมและปูแอสฟัลต์ผสมร้อน Hot Mix',
        ?
    )""", (c4_time,))

    # Case 5: ปฏิเสธเคส (Rejected)
    c5_time = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO damage_reports VALUES (
        'CASE-2026-005', 'U001', 'นายสมชาย รักสะอาด',
        '/static/sample_images/crack_1.jpg',
        'ถนนในซอยมีรอยแตกเป็นแนวยาว',
        13.7820, 100.6280, 'ซอยลาดพร้าว 101 แยก 3 เขตวังทองหลาง',
        'ปฏิเสธเคส', 'เนื่องจากเป็นถนนส่วนบุคคลในหมู่บ้านจัดสรร ไม่อยู่ในพื้นที่รับผิดชอบของหน่วยงาน ขอให้ประสานงานนิติบุคคลหมู่บ้าน', ?, ?
    )""", (c5_time, (now - timedelta(days=6)).strftime("%Y-%m-%d %H:%M:%S")))

    # Case 6: ปิดงานซ่อมบำรุงแล้ว (Closed) + ประเมินความพึงพอใจ 4 ดาว + รูปหลังซ่อม
    c6_time = (now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO damage_reports VALUES (
        'CASE-2026-006', 'U001', 'นายสมชาย รักสะอาด',
        '/static/sample_images/crack_1.jpg',
        'ผิวทางแตกร่อนบริเวณโค้งอันตราย รถชะลอแล้วลื่นไถล',
        13.7540, 100.5340, 'ถ.พญาไท มุ่งหน้าอนุสาวรีย์ชัยฯ ราชเทวี',
        'ปิดงานซ่อมบำรุง', NULL, ?, ?
    )""", (c6_time, (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S")))

    cursor.execute("""
    INSERT INTO ai_reports VALUES (
        'AIR-2026-006', 'CASE-2026-006', 'RoadVision-v2.4-DeepSense',
        'รอยแตกลายจระเข้ (Alligator Cracking)', 'ปานกลาง',
        14000.0, 2, 94.1,
        '[{"x": 160, "y": 90, "width": 300, "height": 220, "label": "Alligator Cracking", "confidence": 94.1}]',
        'ขูดไสผิวทางเดิมและปูผิวแอสฟัลต์คอนกรีตกันลื่นพิเศษ',
        ?
    )""", (c6_time,))

    cursor.execute("""
    INSERT INTO work_orders VALUES (
        'WO-2026-004', 'CASE-2026-006', 'U003', 'นายเอกชัย มุ่งมั่น',
        'ทีมช่างซ่อมบำรุง 01 (จตุจักร-พหลโยธิน)', 14000.0,
        'ปิดงานซ่อมบำรุงแล้ว',
        ?, ?, ?,
        '/static/sample_images/repair_overlay_smooth.jpg',
        'ลงน้ำยางแอสฟัลต์ไพรม์โค้ท ปูทับด้วยผิวทางแอสฟัลต์ผสมร้อนและบดอัดเรียบเนียน',
        'ตรวจรับงานผ่านเกณฑ์ ผิวทางยึดเกาะดี ปิดงานซ่อมบำรุง'
    )""", (
        (now - timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S"),
        (now - timedelta(days=6)).strftime("%Y-%m-%d %H:%M:%S"),
        (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S")
    ))

    cursor.execute("""
    INSERT INTO feedbacks VALUES (
        'FB-2026-002', 'CASE-2026-006', 'U001', 'นายสมชาย รักสะอาด',
        4, 'แก้ไขได้เรียบเนียนดีมากครับ รถเข้าโค้งได้อย่างมั่นใจ ฝากช่วยเก็บกวาดเศษหินข้างทางอีกนิดจะสมบูรณ์แบบมากครับ',
        ?
    )""", ((now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),))

    # Case 7: ปิดงานซ่อมบำรุงแล้ว (Closed) + ประเมินความพึงพอใจ 5 ดาว
    c7_time = (now - timedelta(days=12)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO damage_reports VALUES (
        'CASE-2026-007', 'U001', 'นายสมชาย รักสะอาด',
        '/static/sample_images/pothole_1.jpg',
        'หลุมผิวทางหน้าโรงเรียน เด็กนักเรียนเดินข้ามถนนสะดุดบ่อยครั้ง',
        13.7650, 100.5700, 'ถ.รัชดาภิเษก หน้า รร.เตรียมอุดมฯ ดินแดง',
        'ปิดงานซ่อมบำรุง', NULL, ?, ?
    )""", (c7_time, (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")))

    cursor.execute("""
    INSERT INTO ai_reports VALUES (
        'AIR-2026-007', 'CASE-2026-007', 'RoadVision-v2.4-DeepSense',
        'หลุมบ่อบนผิวจราจร (Standard Pothole)', 'สูง',
        18000.0, 2, 96.7,
        '[{"x": 210, "y": 140, "width": 220, "height": 150, "label": "Pothole", "confidence": 96.7}]',
        'ซ่อมแซมหลุมด่วนพิเศษเพื่อความปลอดภัยหน้าสถานศึกษา',
        ?
    )""", (c7_time,))

    cursor.execute("""
    INSERT INTO work_orders VALUES (
        'WO-2026-005', 'CASE-2026-007', 'U003', 'นายเอกชัย มุ่งมั่น',
        'ทีมช่างซ่อมบำรุง 01 (จตุจักร-พหลโยธิน)', 18000.0,
        'ปิดงานซ่อมบำรุงแล้ว',
        ?, ?, ?,
        '/static/sample_images/repair_asphalt_hotmix.jpg',
        'ดำเนินการซ่อมเสร็จสิ้นภายใน 24 ชม. ตีเส้นชะลอความเร็วให้ใหม่เรียบร้อย',
        'ตรวจรับงานผ่านเกณฑ์อย่างดีเยี่ยม ปิดงาน'
    )""", (
        (now - timedelta(days=11)).strftime("%Y-%m-%d %H:%M:%S"),
        (now - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S"),
        (now - timedelta(days=6)).strftime("%Y-%m-%d %H:%M:%S")
    ))

    cursor.execute("""
    INSERT INTO feedbacks VALUES (
        'FB-2026-003', 'CASE-2026-007', 'U001', 'นายสมชาย รักสะอาด',
        5, 'แจ้งเช้า ดึกซ่อมเสร็จเลย ไวมากกก หน้าโรงเรียนปลอดภัยแล้ว ขอบคุณทีมงานทุกคนครับ',
        ?
    )""", ((now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"),))

    # Case 8: มอบหมายงานแล้ว (Assigned - waiting for technician to start work)
    c8_time = (now - timedelta(hours=14)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO damage_reports VALUES (
        'CASE-2026-008', 'U001', 'นายสมชาย รักสะอาด',
        '/static/sample_images/depression_1.jpg',
        'ผิวถนนหน้าป้ายรถเมล์ทรุดเป็นหลุมยาว ล้อรถเมล์ตกหลุมน้ำกระเด็น',
        13.7900, 100.5400, 'ถ.พหลโยธิน สะพานควาย พญาไท',
        'มอบหมายงานแล้ว', NULL, ?, ?
    )""", (c8_time, (now - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")))

    cursor.execute("""
    INSERT INTO ai_reports VALUES (
        'AIR-2026-008', 'CASE-2026-008', 'RoadVision-v2.4-DeepSense',
        'ผิวทางทรุดตัว (Road Depression)', 'สูง',
        22000.0, 3, 92.8,
        '[{"x": 170, "y": 120, "width": 300, "height": 190, "label": "Depression", "confidence": 92.8}]',
        'บดอัดปรับระดับชั้นทางและลงแอสฟัลต์คอนกรีตเสริมแรง',
        ?
    )""", (c8_time,))

    cursor.execute("""
    INSERT INTO work_orders VALUES (
        'WO-2026-006', 'CASE-2026-008', 'U003', 'นายเอกชัย มุ่งมั่น',
        'ทีมช่างซ่อมบำรุง 01 (จตุจักร-พหลโยธิน)', 22000.0,
        'มอบหมายแล้ว',
        ?, NULL, NULL, NULL,
        NULL, NULL
    )""", ((now - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S"),))

    # Case 9: สั่งแก้ไขงาน (Ordered Revision - Inspector requested re-work)
    c9_time = (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO damage_reports VALUES (
        'CASE-2026-009', 'U001', 'นายสมชาย รักสะอาด',
        '/static/sample_images/crack_1.jpg',
        'ผิวทางแตกร่อนเป็นแนวยาว รถจักรยานยนต์ลื่นไถลช่วงฝนตกอันตรายมาก',
        13.7510, 100.5650, 'ถ.พระราม 9 ขาเข้า ใกล้แยก อสมท ห้วยขวาง',
        'สั่งแก้ไขงาน', NULL, ?, ?
    )""", (c9_time, (now - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")))

    cursor.execute("""
    INSERT INTO ai_reports VALUES (
        'AIR-2026-009', 'CASE-2026-009', 'RoadVision-v2.4-DeepSense',
        'รอยแตกลายจระเข้ (Alligator Cracking)', 'ปานกลาง',
        15000.0, 2, 94.5,
        '[{"x": 160, "y": 90, "width": 300, "height": 220, "label": "Alligator Cracking", "confidence": 94.5}]',
        'ขูดไสผิวทางแตกร่อนและปูทับด้วยผิวทางแอสฟัลต์คอนกรีตผสมร้อน บดอัดเรียบแน่น',
        ?
    )""", (c9_time,))

    cursor.execute("""
    INSERT INTO work_orders VALUES (
        'WO-2026-007', 'CASE-2026-009', 'U003', 'นายเอกชัย มุ่งมั่น',
        'ทีมช่างซ่อมบำรุง 01 (จตุจักร-พหลโยธิน)', 15000.0,
        'สั่งแก้ไขงาน',
        ?, ?, ?,
        '/static/sample_images/crack_1_repaired.jpg',
        'ปูผิวแอสฟัลต์แล้วรอบแรก ขอส่งตรวจรับงาน',
        'ผลการตรวจรับรอบแรก: การบดอัดยังไม่สม่ำเสมอ ผิวทางยังมีรอยคลื่นและเศษหินค้างบนไหล่ทาง กรุณาเข้าบดอัดซ้ำและทำความสะอาดก่อนส่งตรวจรับใหม่'
    )""", (
        (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
        (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
        (now - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    ))

    # Case 10: ยกเลิกเคส (Cancelled by Citizen / Duplicate)
    c10_time = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO damage_reports VALUES (
        'CASE-2026-010', 'U001', 'นายสมชาย รักสะอาด',
        '/static/sample_images/pothole_1.jpg',
        'แจ้งหลุมผิวจราจร ปากซอยสุขุมวิท 55 (ทองหล่อ)',
        13.7250, 100.5790, 'ปากซอยสุขุมวิท 55 (ทองหล่อ) วัฒนา',
        'ยกเลิกเคส', 'ผู้แจ้งขอยกเลิกรายการ เนื่องจากโครงการก่อสร้างข้างเคียงได้ดำเนินการปรับผิวจราจรให้เรียบร้อยแล้ว', ?, ?
    )""", (c10_time, (now - timedelta(hours=12)).strftime("%Y-%m-%d %H:%M:%S")))

    # Case 11: ปิดงานซ่อมบำรุงแล้ว แต่ "รอประชาชนมาประเมินความพึงพอใจ" (ยังไม่มี Feedback)
    c11_time = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO damage_reports VALUES (
        'CASE-2026-011', 'U001', 'นายสมชาย รักสะอาด',
        '/static/sample_images/pothole_1.jpg',
        'ผิวถนนแตกลึกเป็นหลุมกว้าง ปากซอยเอกมัย 12 รถยนต์แล่นผ่านกระแทกแรง เสี่ยงเกิดอุบัติเหตุ',
        13.7315, 100.5852, 'ถ.สุขุมวิท 63 (เอกมัย ซอย 12) วัฒนา กรุงเทพฯ',
        'ปิดงานซ่อมบำรุง', NULL, ?, ?
    )""", (c11_time, (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")))

    cursor.execute("""
    INSERT INTO ai_reports VALUES (
        'AIR-2026-011', 'CASE-2026-011', 'RoadVision-v2.4-DeepSense',
        'หลุมบ่อบนผิวจราจร (Standard Pothole)', 'สูง',
        17500.0, 2, 95.8,
        '[{"x": 210, "y": 140, "width": 220, "height": 150, "label": "Pothole", "confidence": 95.8}]',
        'ตัดแต่งขอบหลุมเป็นแนวตรง ลงหินคลุกบดอัดแน่น และปูผิวแอสฟัลต์คอนกรีตผสมร้อน บดอัดเรียบเสมอผิวเดิม',
        ?
    )""", (c11_time,))

    cursor.execute("""
    INSERT INTO work_orders VALUES (
        'WO-2026-008', 'CASE-2026-011', 'U003', 'นายเอกชัย มุ่งมั่น',
        'ทีมช่างซ่อมบำรุง 01 (จตุจักร-พหลโยธิน)', 17500.0,
        'ปิดงานซ่อมบำรุงแล้ว',
        ?, ?, ?,
        '/static/sample_images/repair_asphalt_hotmix.jpg',
        'ดำเนินการปูผิวทางแอสฟัลต์คอนกรีตผสมร้อน บดอัดเรียบเนียน เสมอผิวถนนเดิม พร้อมเปิดการจราจรแล้วครับ',
        'เจ้าหน้าที่เขตเข้าตรวจสอบหน้างานแล้ว ผลการซ่อมเรียบร้อยตามมาตรฐานทางหลวงท้องถิ่น อนุมัติปิดงานซ่อมบำรุง (รอประชาชนผู้แจ้งประเมินความพึงพอใจ)'
    )""", (
        (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
        (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    ))
    # หมายเหตุ: CASE-2026-011 ไม่มีการ INSERT ลงตาราง feedbacks เพื่อให้เป็นตัวอย่างเคสที่รอประชาชนมาประเมินความพึงพอใจ

    conn.commit()
    conn.close()
    print("Seeded demo database with all cases including pending-feedback sample successfully!")

if __name__ == "__main__":
    seed()
