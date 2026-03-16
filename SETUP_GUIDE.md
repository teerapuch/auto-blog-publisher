# 🤖 Auto Blog Publisher — คู่มือตั้งค่าทั้งหมด

ระบบนี้จะทำงานอัตโนมัติทุกวัน: อ่านไอเดียจาก Google Sheets → Claude เขียนบทความ → Google Imagen สร้างภาพ → โพสต์ WordPress → แชร์ Facebook / LinkedIn / X

---

## ภาพรวม Architecture

```
Google Sheets (ไอเดีย)
       │
       ▼
  GitHub Actions (Cron ทุกวัน 09:00 น.)
       │
       ├─→ Claude API       → เขียนบทความ HTML เต็ม
       ├─→ Google Imagen 3  → สร้าง Cover Image
       ├─→ WordPress REST API → Upload ภาพ + สร้าง Post
       ├─→ Facebook Graph API → แชร์ลิงก์บน Page
       ├─→ LinkedIn API       → แชร์ Article
       └─→ X API v2          → ทวีต
```

---

## สิ่งที่ต้องใช้ (Checklist)

- [ ] GitHub Account + Repository
- [ ] Anthropic API Key (Claude)
- [ ] Google Cloud Project (Imagen + Sheets API)
- [ ] WordPress Application Password
- [ ] Facebook Developer App + Page Access Token
- [ ] LinkedIn Developer App + Access Token
- [ ] X (Twitter) Developer Account + API Keys

---

## ขั้นตอนที่ 1 — WordPress Application Password

> ⚠️ **สำคัญ:** WordPress REST API ไม่รับ password ปกติ ต้องสร้าง Application Password แยกต่างหาก

1. เข้า **WordPress Admin** → `https://teerapuch.com/backend/wp-admin/`
2. ไปที่ **Users → Profile** (หรือ `/wp-admin/profile.php`)
3. เลื่อนลงหา section **"Application Passwords"**
4. กรอกชื่อ เช่น `GitHub Actions Publisher`
5. กด **"Add New Application Password"**
6. **Copy password ที่แสดงออกมา** (รูปแบบ: `xxxx xxxx xxxx xxxx xxxx xxxx`)
7. บันทึกไว้ — จะใช้เป็น `WP_APP_PASSWORD` ใน GitHub Secrets

### ทดสอบด้วย cURL:
```bash
curl -s \
  --user "teerapuch:xxxx xxxx xxxx xxxx xxxx xxxx" \
  "https://teerapuch.com/wp-json/wp/v2/users/me?context=edit" \
  | python3 -m json.tool
```
ต้องเห็น `"name": "teerapuch"` ใน response

---

## ขั้นตอนที่ 2 — Google Cloud (Imagen + Sheets)

### 2.1 เปิดใช้งาน APIs
1. ไปที่ [console.cloud.google.com](https://console.cloud.google.com)
2. สร้าง Project ใหม่ หรือเลือก Project ที่มีอยู่
3. เปิดใช้งาน APIs ต่อไปนี้:
   - **Generative Language API** (สำหรับ Imagen)
   - **Google Sheets API**
   - **Google Drive API**

### 2.2 สร้าง API Key (สำหรับ Imagen)
1. IAM & Admin → **API Keys** → **Create API Key**
2. คลิก **Restrict Key** → เลือกเฉพาะ `Generative Language API`
3. บันทึก key นี้เป็น `GOOGLE_AI_API_KEY`

### 2.3 สร้าง Service Account (สำหรับ Google Sheets)
1. IAM & Admin → **Service Accounts** → **Create Service Account**
2. ตั้งชื่อ เช่น `auto-blog-publisher`
3. Role: **Editor** หรือ **Basic → Viewer** (แค่อ่าน/เขียน Sheets)
4. กด **Done**
5. คลิก Service Account ที่สร้าง → **Keys → Add Key → JSON**
6. Download ไฟล์ JSON
7. **แปลงเป็น single-line** สำหรับ GitHub Secret:

```bash
# บน Terminal ของคุณ:
cat service-account.json | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)))"
```

บันทึก output นี้เป็น `GOOGLE_SHEETS_CREDS_JSON`

### 2.4 สร้าง Google Sheet + แชร์ให้ Service Account
1. ไปที่ [sheets.google.com](https://sheets.google.com) → สร้าง Sheet ใหม่
2. คลิก **Share** → ใส่ email ของ Service Account (จาก JSON ช่อง `client_email`)
3. ให้สิทธิ์เป็น **Editor**
4. Copy **Sheet ID** จาก URL:
   - URL: `https://docs.google.com/spreadsheets/d/`**`1BxiM...SHEET_ID...xyz`**`/edit`
   - บันทึกเป็น `GOOGLE_SHEET_ID`

### 2.5 สร้าง Header ใน Sheet
Sheet ต้องมี header row (Row 1) ดังนี้:

| A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|
| idea | category | status | date_posted | post_url | tags | lang |

> หรือรัน `python create_sheet_template.py` เพื่อสร้าง template อัตโนมัติ

---

## ขั้นตอนที่ 3 — Anthropic API Key (Claude)

1. ไปที่ [console.anthropic.com](https://console.anthropic.com)
2. **API Keys → Create Key**
3. บันทึกเป็น `ANTHROPIC_API_KEY`

---

## ขั้นตอนที่ 4 — Facebook Page Access Token

### 4.1 สร้าง Facebook App
1. ไปที่ [developers.facebook.com](https://developers.facebook.com)
2. **My Apps → Create App** → เลือก **Business**
3. ตั้งชื่อ App (เช่น `AutoBlog Publisher`)

### 4.2 เพิ่ม Pages API
1. ใน App Dashboard → **Add Product** → **Facebook Login for Business**

### 4.3 หา Page ID
1. ไปที่ Facebook Page ของคุณ
2. **About** → ดู **Page ID** (ตัวเลขยาว)
3. หรือ: `https://www.facebook.com/YOUR_PAGE_NAME` → ดู source code หา `page_id`

### 4.4 สร้าง Long-Lived Page Access Token
```bash
# Step 1: ขอ User Token (ใช้ Facebook Graph API Explorer)
# ไปที่ developers.facebook.com/tools/explorer
# เลือก App ของคุณ → Generate Access Token
# เลือก Permissions: pages_manage_posts, pages_read_engagement

# Step 2: แปลงเป็น Long-Lived Token (อายุ 60 วัน)
curl -s "https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN"

# Step 3: ขอ Page Access Token จาก Long-Lived User Token
curl -s "https://graph.facebook.com/v21.0/me/accounts?access_token=LONG_LIVED_USER_TOKEN"
# จะได้ Page Access Token สำหรับแต่ละ Page
```

บันทึก:
- `FB_PAGE_ID` = Page ID ตัวเลข
- `FB_PAGE_ACCESS_TOKEN` = Page Access Token

> ⚠️ Page Access Token ไม่มีหมดอายุ (Never expires) ถ้าได้มาจาก Long-Lived User Token

---

## ขั้นตอนที่ 5 — LinkedIn API

### 5.1 สร้าง LinkedIn App
1. ไปที่ [linkedin.com/developers](https://www.linkedin.com/developers/)
2. **Create App** → กรอกข้อมูล App
3. ไปที่ **Products** → เพิ่ม **Share on LinkedIn** และ **Sign In with LinkedIn**

### 5.2 ขอ Access Token
```bash
# Step 1: Authorization URL
# เปิด Browser ไปที่:
https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=https://localhost&scope=openid%20profile%20w_member_social%20r_basicprofile

# Step 2: หลัง authorize จะได้ code ใน URL → แลกเป็น token
curl -X POST "https://www.linkedin.com/oauth/v2/accessToken" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=YOUR_CODE&redirect_uri=https://localhost&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET"

# Step 3: หา Person URN
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  "https://api.linkedin.com/v2/userinfo"
# จะได้ sub = person ID → ใช้เป็น urn:li:person:YOUR_PERSON_ID
```

บันทึก:
- `LINKEDIN_ACCESS_TOKEN` = Access Token (อายุ 60 วัน ต้อง refresh)
- `LINKEDIN_URN` = `urn:li:person:YOUR_PERSON_ID` หรือ `urn:li:organization:YOUR_ORG_ID`

---

## ขั้นตอนที่ 6 — X (Twitter) API

1. ไปที่ [developer.twitter.com](https://developer.twitter.com)
2. สร้าง Project + App
3. App Settings → **Keys and Tokens**
4. สร้าง **API Key & Secret**
5. สร้าง **Access Token & Secret** (ต้องมีสิทธิ์ Read and Write)

บันทึก:
- `TWITTER_API_KEY`
- `TWITTER_API_SECRET`
- `TWITTER_ACCESS_TOKEN`
- `TWITTER_ACCESS_TOKEN_SECRET`

---

## ขั้นตอนที่ 7 — ตั้งค่า GitHub Repository

### 7.1 สร้าง Repository
```bash
# สร้าง repo ใหม่บน github.com แล้ว push ไฟล์ทั้งหมด
git init
git add .
git commit -m "Initial: Auto Blog Publisher"
git remote add origin https://github.com/YOUR_USERNAME/auto-blog-publisher.git
git push -u origin main
```

### 7.2 ใส่ Secrets
ไปที่ GitHub Repository → **Settings → Secrets and variables → Actions → New repository secret**

ใส่ Secrets ทั้งหมดนี้:

| Secret Name | ค่า |
|---|---|
| `ANTHROPIC_API_KEY` | sk-ant-api03-... |
| `GOOGLE_AI_API_KEY` | AIzaSy... |
| `GOOGLE_SHEETS_CREDS_JSON` | `{"type":"service_account",...}` (JSON แบบ single-line) |
| `GOOGLE_SHEET_ID` | ID จาก URL ของ Google Sheet |
| `WP_APP_PASSWORD` | `xxxx xxxx xxxx xxxx xxxx xxxx` |
| `FB_PAGE_ID` | 12345678901234 |
| `FB_PAGE_ACCESS_TOKEN` | EAABl... |
| `LINKEDIN_ACCESS_TOKEN` | AQV... |
| `LINKEDIN_URN` | `urn:li:person:XXXXXXXX` |
| `TWITTER_API_KEY` | ... |
| `TWITTER_API_SECRET` | ... |
| `TWITTER_ACCESS_TOKEN` | ... |
| `TWITTER_ACCESS_TOKEN_SECRET` | ... |

---

## ขั้นตอนที่ 8 — เพิ่มไอเดียและทดสอบ

### เพิ่มไอเดียใน Google Sheet
เปิด Sheet แล้วเพิ่มแถวใหม่:
```
A: AI กับอนาคตของการทำงาน ในยุค 2025 ทุกคนต้องปรับตัวอย่างไร
B: Technology
C: pending
D: (ว่าง)
E: (ว่าง)
F: AI, Future of Work, Career
G: th
```

### ทดสอบ Manual Trigger
1. GitHub Repository → **Actions**
2. เลือก workflow **"Auto Blog Publisher — Daily"**
3. กด **"Run workflow"** → เลือก `dry_run: false`
4. ดู logs แบบ real-time

### ตรวจสอบการทำงาน
```bash
# ตรวจสอบ WordPress post ล่าสุด
curl -s "https://teerapuch.com/wp-json/wp/v2/posts?per_page=1" \
  | python3 -c "import sys,json; p=json.load(sys.stdin)[0]; print(p['link'], '\n', p['title']['rendered'])"
```

---

## ตารางเวลาทำงาน

ระบบจะ run อัตโนมัติทุกวัน เวลา **09:00 น. (Bangkok Time)**

ถ้าต้องการเปลี่ยนเวลา แก้ไขใน `.github/workflows/daily_post.yml`:
```yaml
# UTC time (Bangkok = UTC+7, ลบ 7 ชั่วโมง)
# 09:00 BKK = 02:00 UTC
cron: "0 2 * * *"

# ตัวอย่างอื่น:
# 07:00 BKK = "0 0 * * *"
# 12:00 BKK = "0 5 * * *"
# 20:00 BKK = "0 13 * * *"
```

---

## โครงสร้างไฟล์

```
auto-blog-publisher/
├── auto_blog_publisher.py      ← Script หลัก
├── create_sheet_template.py    ← สร้าง Google Sheet template
├── requirements.txt            ← Python dependencies
├── SETUP_GUIDE.md             ← คู่มือนี้
└── .github/
    └── workflows/
        └── daily_post.yml      ← GitHub Actions workflow
```

---

## แก้ปัญหาที่พบบ่อย

**❌ WordPress: "rest_not_logged_in"**
→ ต้องใช้ Application Password ไม่ใช่ password ปกติ (ดูขั้นตอนที่ 1)

**❌ Google Imagen: 403 Forbidden**
→ ตรวจสอบว่าเปิด "Generative Language API" ใน Google Cloud Console แล้ว

**❌ Facebook: "Invalid OAuth access token"**
→ Page Access Token หมดอายุ ต้อง generate ใหม่ (ทำทุก 60 วัน)

**❌ LinkedIn: 401 Unauthorized**
→ Access Token อายุ 60 วัน ต้อง refresh ทุก 2 เดือน

**❌ Twitter: "453 - You currently have access to a subset"**
→ ต้อง upgrade Twitter Developer account เป็น Basic ($100/เดือน) หรือขอสิทธิ์ Write Access

**❌ ไม่มีไอเดียใน Sheet**
→ Script จะหยุดทำงานโดยไม่ error — ตรวจสอบว่าแถวใน Sheet มี status = pending
