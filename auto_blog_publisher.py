#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║       AUTO BLOG PUBLISHER v2 — teerapuch.com                     ║
║       Phase 1: WordPress Only (Social Media มาทีหลัง)            ║
╠══════════════════════════════════════════════════════════════════╣
║  Google Sheets → Claude → (Image) → WordPress REST API           ║
║                                                                  ║
║  ภาพประกอบ 3 แบบ (เลือกอัตโนมัติตาม availability):              ║
║  1. image_url ใน Google Sheet  ← ใช้ก่อน (ไม่ต้องมี API)        ║
║  2. Google Imagen 3 API        ← ถ้ามี GOOGLE_AI_API_KEY         ║
║  3. ไม่มีภาพ                   ← fallback ถ้าไม่มีทั้งสองอย่าง   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import base64
import requests
import anthropic
from datetime import datetime


# ─────────────────────────────────────────────────────────────────
# ENV VARS  (ใส่ใน GitHub Actions Secrets)
# ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY        = os.environ["ANTHROPIC_API_KEY"]
GOOGLE_SHEETS_CREDS_JSON = os.environ["GOOGLE_SHEETS_CREDS_JSON"]
GOOGLE_SHEET_ID          = os.environ["GOOGLE_SHEET_ID"]

WP_URL                   = os.environ.get("WP_URL", "https://teerapuch.com")
WP_USERNAME              = os.environ.get("WP_USERNAME", "teerapuch")
WP_APP_PASSWORD          = os.environ["WP_APP_PASSWORD"]  # Application Password (ไม่ใช่ password ปกติ)

# Optional — ถ้ามีจะ generate ภาพอัตโนมัติ, ถ้าไม่มีจะใช้จาก Google Sheet
GOOGLE_AI_API_KEY        = os.environ.get("GOOGLE_AI_API_KEY", "")


# ═══════════════════════════════════════════════════════════════
# 1. GOOGLE SHEETS — อ่านไอเดียถัดไป
# ═══════════════════════════════════════════════════════════════
def get_next_idea() -> dict | None:
    """คืนค่า dict ของไอเดียถัดไปที่ status = pending (หรือว่างเปล่า)"""
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(GOOGLE_SHEETS_CREDS_JSON), scope
    )
    client = gspread.authorize(creds)
    sheet  = client.open_by_key(GOOGLE_SHEET_ID).sheet1
    rows   = sheet.get_all_records()

    for i, row in enumerate(rows, start=2):  # row 1 = header
        if str(row.get("status", "")).strip().lower() in ("", "pending"):
            return {
                "row"      : i,
                "idea"     : str(row.get("idea", "")).strip(),
                "category" : str(row.get("category", "")).strip(),
                "tags"     : str(row.get("tags", "")).strip(),
                "lang"     : str(row.get("lang", "th")).strip() or "th",
                "image_url": str(row.get("image_url", "")).strip(),  # Google Drive URL หรือ URL รูปใดก็ได้
                "sheet"    : sheet,
            }
    return None


def mark_as_posted(sheet, row: int, post_url: str):
    """อัปเดต status → published + บันทึก URL + timestamp"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.update(f"C{row}", [["published"]])
    sheet.update(f"D{row}", [[now]])
    sheet.update(f"E{row}", [[post_url]])


# ═══════════════════════════════════════════════════════════════
# 2. CLAUDE — เขียนบทความ
# ═══════════════════════════════════════════════════════════════
def generate_article(idea_data: dict) -> dict:
    """ส่งไอเดียให้ Claude Opus เขียนบทความฉบับเต็ม คืนค่า dict"""
    client    = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    lang_name = "ภาษาไทย" if idea_data["lang"] == "th" else "English"
    category  = idea_data.get("category", "")
    tags      = idea_data.get("tags", "")

    prompt = f"""คุณคือ Senior Content Writer เชี่ยวชาญ Blog ที่น่าอ่าน SEO-friendly ใน{lang_name}

**แนวคิด/ต้นเรื่อง:**
{idea_data["idea"]}
{"**หมวดหมู่:** " + category if category else ""}
{"**แท็ก:** " + tags if tags else ""}

**ข้อกำหนดบทความ:**
- ความยาว 800–1,200 คำ
- Introduction ที่ดึงดูดความสนใจตั้งแต่ประโยคแรก
- แบ่ง sections ชัดเจนด้วย <h2> และ <h3>
- มี practical tips หรือ actionable insights ที่ผู้อ่านทำตามได้จริง
- Conclusion ที่ inspire และจบสวยงาม
- Tone: Professional แต่อ่านสบาย เป็นกันเอง ไม่ทางการจนเกินไป
- ใส่ keyword เป็นธรรมชาติ (ไม่ keyword stuffing)

**ตอบเป็น JSON เท่านั้น** (ไม่มี markdown wrapper ไม่มีข้อความอื่น):
{{
  "title": "ชื่อบทความที่น่าสนใจ ดึงดูดความสนใจ ไม่เกิน 70 ตัวอักษร",
  "meta_description": "คำอธิบาย SEO ภาษาธรรมชาติ 150-160 ตัวอักษร",
  "content_html": "เนื้อหาบทความ HTML ใช้ <h2> <h3> <p> <ul> <li> <strong> <em> — ห้ามใส่ <html><body><head>",
  "excerpt": "สรุปบทความสั้นๆ 2-3 ประโยค สำหรับแสดงใน WordPress listing",
  "image_prompt": "Prompt ภาษาอังกฤษสำหรับ AI สร้าง Cover Image — professional, cinematic, no text in image, describe scene/mood/colors/composition clearly"
}}"""

    msg = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    return json.loads(raw)


# ═══════════════════════════════════════════════════════════════
# 3a. ดาวน์โหลดภาพจาก URL (Google Drive หรือ URL อื่นๆ)
# ═══════════════════════════════════════════════════════════════
def download_image_from_url(url: str) -> bytes | None:
    """
    รองรับ Google Drive URL ทั้งสองรูปแบบ:
      - https://drive.google.com/file/d/FILE_ID/view?...
      - https://drive.google.com/open?id=FILE_ID
    และ URL รูปภาพทั่วไป (jpg, png, webp, ...)
    """
    if not url:
        return None

    # แปลง Google Drive share link → direct download URL
    if "drive.google.com" in url:
        file_id = None
        if "/file/d/" in url:
            file_id = url.split("/file/d/")[1].split("/")[0].split("?")[0]
        elif "id=" in url:
            file_id = url.split("id=")[1].split("&")[0]

        if file_id:
            url = f"https://drive.google.com/uc?export=download&id={file_id}"
            print(f"   → Google Drive direct URL: {url}")

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
        resp.raise_for_status()

        # ตรวจสอบว่าเป็นรูปภาพจริง
        content_type = resp.headers.get("Content-Type", "")
        if "image" in content_type or len(resp.content) > 1000:
            return resp.content
        else:
            print(f"   ⚠️  URL ไม่ใช่รูปภาพ (Content-Type: {content_type})")
            return None
    except Exception as e:
        print(f"   ⚠️  ดาวน์โหลดภาพไม่สำเร็จ: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# 3b. Google Imagen 3 — สร้างภาพอัตโนมัติ (ถ้ามี API Key)
# ═══════════════════════════════════════════════════════════════
def generate_image_with_imagen(image_prompt: str) -> bytes | None:
    """เรียก Google Imagen 3 API — คืน None ถ้าไม่มี API Key หรือ error"""
    if not GOOGLE_AI_API_KEY:
        return None

    url = (
        "https://generativelanguage.googleapis.com/v1beta"
        "/models/imagen-3.0-generate-002:predict"
    )
    try:
        resp = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": GOOGLE_AI_API_KEY,
            },
            json={
                "instances": [{
                    "prompt": (
                        image_prompt
                        + ", professional blog cover photo, cinematic lighting, "
                          "high resolution, 16:9 aspect ratio, no text overlay, no watermark"
                    )
                }],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "16:9",
                    "safetyFilterLevel": "BLOCK_SOME",
                },
            },
            timeout=60,
        )
        resp.raise_for_status()
        img_b64 = resp.json()["predictions"][0]["bytesBase64Encoded"]
        return base64.b64decode(img_b64)
    except Exception as e:
        print(f"   ⚠️  Imagen API error: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# 4. WORDPRESS — helper functions
# ═══════════════════════════════════════════════════════════════
def _wp_auth() -> dict:
    """Basic Auth header สำหรับ WordPress Application Password"""
    token = base64.b64encode(f"{WP_USERNAME}:{WP_APP_PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def wp_upload_image(image_bytes: bytes, filename: str, alt_text: str) -> tuple[int, str]:
    """อัปโหลดรูปไป WordPress Media Library → คืน (media_id, source_url)"""
    # ตรวจหา content-type จากไฟล์
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                "webp": "image/webp", "gif": "image/gif"}
    mime = mime_map.get(ext, "image/png")

    resp = requests.post(
        f"{WP_URL}/wp-json/wp/v2/media",
        headers={
            **_wp_auth(),
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": mime,
        },
        data=image_bytes,
        timeout=120,
    )
    resp.raise_for_status()
    media = resp.json()

    # อัปเดต alt text + title
    requests.post(
        f"{WP_URL}/wp-json/wp/v2/media/{media['id']}",
        headers={**_wp_auth(), "Content-Type": "application/json"},
        json={"alt_text": alt_text, "title": alt_text},
        timeout=30,
    )
    return media["id"], media["source_url"]


def wp_get_or_create_category(name: str) -> int:
    """หา Category ID จากชื่อ ถ้าไม่มีสร้างใหม่ คืน ID"""
    if not name:
        return 1  # Uncategorized

    resp = requests.get(
        f"{WP_URL}/wp-json/wp/v2/categories",
        params={"search": name, "per_page": 20},
        headers=_wp_auth(),
        timeout=15,
    )
    for cat in resp.json():
        if cat["name"].lower() == name.lower():
            return cat["id"]

    # สร้างใหม่
    resp = requests.post(
        f"{WP_URL}/wp-json/wp/v2/categories",
        headers={**_wp_auth(), "Content-Type": "application/json"},
        json={"name": name},
        timeout=15,
    )
    if resp.status_code in (200, 201):
        return resp.json()["id"]
    return 1


def wp_create_post(article: dict, featured_image_id: int | None, category_id: int) -> dict:
    """สร้าง WordPress Post → คืน response dict พร้อม link"""
    post_data = {
        "title"   : article["title"],
        "content" : article["content_html"],
        "excerpt" : article["excerpt"],
        "status"  : "publish",
        "categories": [category_id],
        "meta"    : {},
    }
    if featured_image_id:
        post_data["featured_media"] = featured_image_id

    # Yoast SEO meta (ถ้ามี plugin)
    if article.get("meta_description"):
        post_data["meta"]["_yoast_wpseo_metadesc"] = article["meta_description"]
        post_data["meta"]["_yoast_wpseo_title"]    = article["title"]

    resp = requests.post(
        f"{WP_URL}/wp-json/wp/v2/posts",
        headers={**_wp_auth(), "Content-Type": "application/json"},
        json=post_data,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print(f"🚀 Auto Blog Publisher v2")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Bangkok Time)")
    print("=" * 60)

    # ── Step 1: อ่านไอเดียจาก Google Sheets ──────────────────
    print("\n📋 [1/4] อ่านไอเดียจาก Google Sheets...")
    idea_data = get_next_idea()
    if not idea_data:
        print("✅ ไม่มีไอเดียที่ pending — หยุดการทำงาน (ไม่มี error)")
        sys.exit(0)

    print(f"   ✅ Row {idea_data['row']}: {idea_data['idea'][:100]}...")
    print(f"   📁 Category: {idea_data['category'] or '(ไม่ระบุ)'}")
    print(f"   🖼  Image URL: {idea_data['image_url'][:60] + '...' if len(idea_data['image_url']) > 60 else idea_data['image_url'] or '(ไม่มี)'}")

    # ── Step 2: Claude เขียนบทความ ───────────────────────────
    print("\n✍️  [2/4] Claude กำลังเขียนบทความ (อาจใช้เวลา 20-40 วินาที)...")
    article = generate_article(idea_data)
    print(f"   ✅ Title: {article['title']}")
    print(f"   📝 Content: {len(article['content_html'])} chars")

    # ── Step 3: จัดการภาพ ───────────────────────────────────
    print("\n🎨 [3/4] จัดการภาพ...")
    image_bytes    : bytes | None = None
    image_filename : str          = ""

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Priority 1: URL จาก Google Sheet
    if idea_data["image_url"]:
        print(f"   📥 ดาวน์โหลดภาพจาก URL ที่กำหนด...")
        image_bytes = download_image_from_url(idea_data["image_url"])
        if image_bytes:
            ext = "jpg" if idea_data["image_url"].split("?")[0].lower().endswith(("jpg","jpeg")) else "png"
            image_filename = f"cover-{ts}.{ext}"
            print(f"   ✅ ดาวน์โหลดสำเร็จ ({len(image_bytes):,} bytes)")
        else:
            print("   ⚠️  ดาวน์โหลดไม่สำเร็จ → ลอง Imagen API...")

    # Priority 2: Google Imagen API (ถ้ามี key)
    if not image_bytes and GOOGLE_AI_API_KEY:
        print(f"   🤖 สร้างภาพด้วย Google Imagen 3...")
        image_bytes    = generate_image_with_imagen(article["image_prompt"])
        image_filename = f"cover-{ts}.png"
        if image_bytes:
            print(f"   ✅ สร้างภาพสำเร็จ ({len(image_bytes):,} bytes)")

    # Priority 3: ไม่มีภาพ
    if not image_bytes:
        print("   ℹ️  ไม่มีภาพ — บทความจะถูกโพสต์โดยไม่มี Featured Image")

    # อัปโหลดภาพไป WordPress
    featured_image_id: int | None = None
    if image_bytes:
        print(f"   📤 อัปโหลดภาพไป WordPress Media Library...")
        featured_image_id, img_url = wp_upload_image(image_bytes, image_filename, article["title"])
        print(f"   ✅ Media ID: {featured_image_id}")

    # ── Step 4: สร้าง WordPress Post ─────────────────────────
    print("\n📰 [4/4] สร้าง WordPress Post...")
    cat_id  = wp_get_or_create_category(idea_data["category"])
    wp_post = wp_create_post(article, featured_image_id, cat_id)
    post_url = wp_post["link"]
    print(f"   ✅ Post ID: {wp_post['id']}")
    print(f"   🔗 URL: {post_url}")

    # อัปเดต Google Sheets
    mark_as_posted(idea_data["sheet"], idea_data["row"], post_url)
    print("   ✅ อัปเดต Google Sheets → published")

    print("\n" + "=" * 60)
    print(f"🎉 บทความใหม่เผยแพร่แล้ว!")
    print(f"   {post_url}")
    print("=" * 60)


if __name__ == "__main__":
    main()
