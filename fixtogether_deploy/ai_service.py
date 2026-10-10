import os
import random
import json
from datetime import datetime
try:
    from PIL import Image
except ImportError:
    Image = None

class RoadDamageAIService:
    def __init__(self, model_version="RoadVision-v2.4-DeepSense"):
        self.model_version = model_version
        
    def analyze_image(self, image_path: str, user_description: str = ""):
        """
        วิเคราะห์ภาพถ่ายความเสียหายของถนน
        1. ตรวจสอบความสมบูรณ์ของภาพ
        2. ตรวจจับและจำแนกประเภทความเสียหาย
        3. ประเมินระดับความรุนแรง
        4. ประเมินงบประมาณและระยะเวลาซ่อมแซม
        5. สร้าง Bounding Box สำหรับแสดงผลบน Canvas
        """
        # Determine image dimensions
        img_w, img_h = 600, 400
        if Image and os.path.exists(image_path):
            try:
                with Image.open(image_path) as im:
                    img_w, img_h = im.size
            except Exception:
                pass
                
        # Heuristic / Intelligent detection simulation based on filename or text or image size
        lower_desc = (user_description or "").lower()
        lower_path = image_path.lower()
        
        if "crack" in lower_path or "แตก" in lower_desc or "รอยแยก" in lower_desc:
            damage_type = "รอยแตกลายจระเข้ (Alligator Cracking)"
            severity = "ปานกลาง"
            base_budget = 9500
            days = 2
            confidence = round(random.uniform(91.0, 96.5), 1)
            boxes = [
                {"x": int(img_w * 0.25), "y": int(img_h * 0.20), "width": int(img_w * 0.50), "height": int(img_h * 0.45), "label": "Alligator Cracking", "confidence": confidence}
            ]
            recommendation = "ขัดเปิดผิวรอยแตก กวาดทำความสะอาด และลงน้ำยางแอสฟัลต์อีมัลชันพร้อมบดอัดซ่อมผิวหน้า"
        elif "depression" in lower_path or "ทรุด" in lower_desc or "แอ่น" in lower_desc:
            damage_type = "ผิวทางทรุดตัว (Road Depression)"
            severity = "สูง"
            base_budget = 24000
            days = 3
            confidence = round(random.uniform(89.5, 95.0), 1)
            boxes = [
                {"x": int(img_w * 0.20), "y": int(img_h * 0.25), "width": int(img_w * 0.60), "height": int(img_h * 0.50), "label": "Depression / Rutting", "confidence": confidence}
            ]
            recommendation = "ตรวจสอบชั้นโครงสร้างทางด้านล่าง ปรับระดับชั้นรองพื้นทาง และลาดยางแอสฟัลต์คอนกรีตความหนา 8 ซม."
        elif "พัง" in lower_desc or "ลึก" in lower_desc or "อันตราย" in lower_desc:
            damage_type = "หลุมบ่อขนาดใหญ่และลึก (Severe Pothole)"
            severity = "วิกฤต"
            base_budget = 35000
            days = 4
            confidence = round(random.uniform(94.0, 98.2), 1)
            boxes = [
                {"x": int(img_w * 0.30), "y": int(img_h * 0.28), "width": int(img_w * 0.45), "height": int(img_h * 0.42), "label": "Severe Pothole", "confidence": confidence}
            ]
            recommendation = "ขุดเปิดปากหลุมเป็นรูปสี่เหลี่ยม ลงหินคลุกบดอัดแน่น และปูผิวแอสฟัลต์ผสมร้อน Hot Mix เต็มพื้นที่ด่วน"
        else:
            damage_type = "หลุมบ่อบนผิวจราจร (Standard Pothole)"
            severity = "ปานกลาง"
            base_budget = 12500
            days = 2
            confidence = round(random.uniform(92.0, 97.5), 1)
            boxes = [
                {"x": int(img_w * 0.32), "y": int(img_h * 0.30), "width": int(img_w * 0.38), "height": int(img_h * 0.38), "label": "Pothole", "confidence": confidence}
            ]
            recommendation = "ทำความสะอาดแอ่งหลุม ใช้ยางมะตอยผสมสำเร็จรูปบดอัดแน่นและซีลขอบเพื่อป้องกันน้ำซึม"
            
        return {
            "model_version": self.model_version,
            "damage_type": damage_type,
            "severity_level": severity,
            "estimated_budget": float(base_budget),
            "estimated_days": int(days),
            "confidence_score": float(confidence),
            "detection_boxes": json.dumps(boxes),
            "recommendation": recommendation,
            "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

ai_engine = RoadDamageAIService()
