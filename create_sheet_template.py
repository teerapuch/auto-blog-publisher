#!/usr/bin/env python3
"""
สร้าง Google Sheet template สำหรับเก็บไอเดียบทความ (v2 — มี image_url column)

วิธีใช้:
  python create_sheet_template.py

ต้องการ:
  - GOOGLE_SHEETS_CREDS_JSON  (Service Account JSON แบบ single-line)
  - GOOGLE_SHEET_ID           (ID ของ Google Sheet)
"""

import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

GOOGLE_SHEETS_CREDS_JSON = os.environ["GOOGLE_SHEETS_CREDS_JSON"]
GOOGLE_SHEET_ID          = os.environ["GOOGLE_SHEET_ID"]


def setup_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds  = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(GOOGLE_SHEETS_CREDS_JSON), scope
    )
    client = gspread.authorize(creds)
    sheet  = client.open_by_key(GOOGLE_SHEET_ID).sheet1

    # ─── Header row ────────────────────────────────────────────
    headers = [
        "idea",        # A — ไอเดีย/ต้นเรื่องสั้นๆ
        "category",    # B — หมวดหมู่
        "status",      # C — pending | published
        "date_posted", # D — auto-fill
        "post_url",    # E — auto-fill
        "tags",        # F — แท็กคั่นด้วย comma (optional)
        "lang",        # G — th / en (default: th)
        "image_url",   # H — URL รูปภาพ (Google Drive หรือ URL ใดก็ได้) ← ใหม่!
    ]
    sheet.update("A1:H1", [headers])

    # ─── ตัวอย่าง ideas ─────────────────────────────────────────
    examples = [
        [
            "AI กำลังเปลี่ยนแปลงวงการ Digital Marketing อย่างไร ธุรกิจต้องปรับตัวยังไง",
            "Technology",
            "pending",
            "",
            "",
            "AI, Marketing, Digital",
            "th",
            "",  # วาง Google Drive URL ตรงนี้ เช่น https://drive.google.com/file/d/1abc.../view
        ],
        [
            "5 นิสัยของคนที่ประสบความสำเร็จก่อนอายุ 40 ที่คนส่วนใหญ่ไม่รู้",
            "Lifestyle",
            "pending",
            "",
            "",
            "Success, Habits, Mindset",
            "th",
            "",
        ],
    ]
    sheet.update("A2:H3", examples)

    # Format header
    sheet.format("A1:H1", {
        "backgroundColor": {"red": 0.12, "green": 0.47, "blue": 0.71},
        "textFormat": {
            "bold": True,
            "foregroundColor": {"red": 1, "green": 1, "blue": 1},
        },
        "horizontalAlignment": "CENTER",
    })
    sheet.format("A2:A1000", {"wrapStrategy": "WRAP"})

    print("✅ Google Sheet template สร้างเสร็จแล้ว!")
    print(f"   URL: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}")
    print()
    print("📋 คำอธิบาย Columns:")
    print("   A: idea       — ไอเดีย/ต้นเรื่องสั้นๆ (Claude จะขยายเป็นบทความยาว)")
    print("   B: category   — หมวดหมู่ (Technology, Business, Lifestyle, ...)")
    print("   C: status     — pending = รอโพสต์ | published = โพสต์แล้ว")
    print("   D: date_posted — ระบบใส่ให้อัตโนมัติ")
    print("   E: post_url   — ระบบใส่ให้อัตโนมัติ")
    print("   F: tags       — แท็ก คั่นด้วย comma")
    print("   G: lang       — th หรือ en")
    print("   H: image_url  — URL รูปภาพที่เตรียมไว้ล่วงหน้า (Google Drive หรือ URL อื่นๆ)")
    print()
    print("💡 วิธีใส่รูปภาพจาก Google Drive:")
    print("   1. Upload รูปไป Google Drive")
    print("   2. คลิกขวา → Share → Change to 'Anyone with the link'")
    print("   3. Copy link → วางใน Column H")
    print("   รูปแบบที่รองรับ:")
    print("   - https://drive.google.com/file/d/FILE_ID/view?usp=sharing")
    print("   - https://drive.google.com/open?id=FILE_ID")


if __name__ == "__main__":
    setup_sheet()
