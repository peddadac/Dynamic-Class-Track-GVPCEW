# Dynamic Class Track — College Timetable & Classroom Allocation System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Flask 3.0+](https://img.shields.io/badge/flask-3.1-black.svg)](https://flask.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/tests-19%20passed-brightgreen.svg)](https://pytest.org/)
[![Bootstrap 5](https://img.shields.io/badge/bootstrap-5.3-purple.svg)](https://getbootstrap.com/)
[![OCR Engine](https://img.shields.io/badge/OCR-Tesseract%20%2B%20OpenCV-orange.svg)](https://github.com/tesseract-ocr/tesseract)

**Dynamic Class Track** is a full-featured, secure, responsive college management web application built for colleges such as **Gayatri Vidya Parishad College of Engineering for Women (GVPCEW)**. It enables students, faculty, and administrative staff to identify next classes, assigned classrooms, daily period timings, and instantaneous room reassignments without confusion.

---

## 1. Key System Features

### 🏛️ Three Dedicated Role Portals
- **Landing Gateway:** Professional landing page showcasing three distinct portal cards: **Admin**, **Faculty**, and **Student**.
- **Role-Based Protection:** Secure password hashing (pbkdf2/scrypt), session management, CSRF protection, and route isolation.

### 📷 Timetable Image Upload & Automatic OCR Extraction
- **Image & PDF Processing:** Accepts PNG, JPG, JPEG, and scanned timetable documents.
- **OpenCV Preprocessing:** Auto-resizing, grayscale conversion, Gaussian blur noise filtering, Otsu adaptive thresholding, and minAreaRect deskewing.
- **Intelligent Table Segmentation:** Detects horizontal and vertical cell boundary lines to parse timetable slots.
- **Editable Review Interface:** Extracted text is presented in an interactive review grid where uncertain fields are highlighted in amber. Administrators can edit cells, select faculty/rooms from live database dropdowns, validate conflicts, and approve for publication.
- **Never Silently Invents Data:** Cells with lower confidence or missing mappings are explicitly flagged for human verification.

### 🗓️ Cross-Branch Faculty Schedules & Strict Student Isolation
- **Faculty Portal:** Consolidates a professor’s teaching periods across multiple branches (e.g. CSE Section A during period 1, ECE Section B during period 2) in chronological order with current & upcoming class highlights.
- **Student Portal:** Strictly restricted to the authenticated student’s assigned branch, semester, and section. Students cannot view another section's private timetable by modifying URLs.

### 🚪 Classroom Change Management & Targeted Alerts
- **On-the-Fly Room Reassignment:** Reassign a class to a new room transactionally.
- **Conflict Checker:** Checks whether the new room is available before saving.
- **Targeted Notification Broadcast:** Only notifies the assigned faculty member and students belonging to that specific section. Unrelated branches/sections receive zero spam.
- **Audit History:** Full log of previous room, new room, reason, administrator, and timestamp.

### 🔔 Notifications & Background Class Reminders
- **In-App Bell Alerts:** Unread notification count badge with live updates.
- **Real-Time Updates:** Live event pushes via Socket.IO with automatic polling fallback.
- **Background Reminders:** APScheduler worker monitors upcoming classes (15 min beforehand) in the configured college timezone (`Asia/Kolkata`) with duplicate prevention (idempotency).
- **Web Push (VAPID):** Browser push notification support using Service Workers (`sw.js`).

---

## 2. Technology Stack

- **Backend:** Python 3.10+ with Flask 3.1
- **Database & ORM:** SQLite (development), fully compatible with PostgreSQL/MySQL via SQLAlchemy 2.0
- **Authentication:** Flask-Login with secure password hashing and role-based decorators
- **Image & OCR Processing:** OpenCV (`opencv-python-headless`), Pillow, Tesseract OCR (`pytesseract`), PyPDF
- **Frontend:** HTML5, CSS3, JavaScript (ES6), Bootstrap 5, FontAwesome 6
- **Real-Time & Tasks:** Flask-SocketIO, APScheduler, pywebpush
- **Testing:** pytest (19 automated tests covering 100% of core requirements)

---

## 3. Project Directory Structure

```text
Devops/
├── app/
│   ├── __init__.py                 # Application factory (create_app)
│   ├── extensions.py               # db, login_manager, csrf, socketio
│   ├── models/
│   │   ├── __init__.py             # Exports all SQLAlchemy models
│   │   ├── user.py                 # User model (admin, faculty, student)
│   │   ├── academic.py             # Branch, AcademicYear, Semester, Section, Subject, Profiles
│   │   ├── classroom.py            # Classroom model (building, capacity, availability)
│   │   ├── timetable.py            # TimetableVersion, TimetableEntry, UploadedTimetableImage, RoomChangeHistory
│   │   ├── notification.py         # Notification, PushSubscription
│   │   └── audit.py                # AuditLog
│   ├── auth/                       # Login, Logout, Password changes, Rate limiter, Decorators
│   ├── admin/                      # CRUD for Branches, Sections, Rooms, Faculty, Students, Upload, Review, Conflicts
│   ├── faculty/                    # Today's teaching schedule, Weekly cross-branch timetable, Alerts
│   ├── student/                    # Today's classes, Current/Next class cards, Section schedule, Alerts
│   ├── api/                        # Dropdowns, Notification polling, WebPush subscriptions
│   ├── services/
│   │   ├── ocr_service.py          # OpenCV preprocessing & Tesseract extraction
│   │   ├── timetable_parser.py     # Cell parsing & database entity mapping
│   │   ├── timetable_validation.py # Conflict detection (room, faculty, section overlaps)
│   │   ├── notification_service.py # Targeted alerts & SocketIO dispatch
│   │   └── reminder_service.py     # APScheduler background class reminder worker
│   ├── static/
│   │   ├── css/styles.css          # GVPCEW custom stylesheet
│   │   └── js/
│   │       ├── main.js             # Polling, dropdowns, live toasts
│   │       └── sw.js               # Service Worker for browser push
│   └── templates/
│       ├── base.html               # Navbar, alerts, toasts, footer
│       ├── index.html              # Landing page with 3 portal cards & stats
│       ├── auth/                   # login.html, change_password.html
│       ├── errors/                 # 404, 403, 500, 413
│       ├── admin/                  # Dashboard, CRUD, review table, room changes, conflicts
│       ├── faculty/                # Dashboard, schedule, notifications
│       └── student/                # Dashboard, schedule, notifications
├── sample_data/
│   ├── sample_timetable.png        # Sample college timetable image for OCR upload test
│   └── sample_students.csv         # Sample student bulk import CSV
├── instance/                       # SQLite database location (ignored by git)
├── uploads/                        # Uploaded timetable images & CSVs
├── tests/                          # 19 automated pytest tests
├── config.py                       # Dev, Test, Prod configuration
├── run.py                          # Server launcher & CLI entrypoint
├── cli.py                          # init-db, create-admin, seed-data commands
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
└── README.md                       # Comprehensive guide
```

---

## 4. Local Installation & Setup on Windows

### Prerequisites
1. **Python 3.10+** (verified on Python 3.14)
2. **Git**
3. *(Optional for real OCR)* **Tesseract OCR Engine**:
   - Download the Windows installer from [UB-Mannheim Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) or install via Winget:
     ```powershell
     winget install UB-Mannheim.TesseractOCR
     ```
   - Standard path is `C:\Program Files\Tesseract-OCR\tesseract.exe`.
   *(Note: If Tesseract is not installed, the app automatically activates a fallback parser so you can still test timetable uploading and the editable review grid without interruption).*

### Step-by-Step Installation

1. **Clone or Open the Repository Directory:**
   ```powershell
   cd c:\Users\pc\OneDrive\Desktop\Devops
   ```

2. **Create and Activate a Virtual Environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   Copy `.env.example` to `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```

5. **Initialize Database and Seed GVPCEW Starter Data:**
   ```powershell
   python run.py init-db
   python run.py seed-data
   ```

6. **(Optional) Create a Custom Administrator Account:**
   ```powershell
   python run.py create-admin
   ```

---

## 5. Running the Application

Start the Flask application:
```powershell
python run.py
```
By default, the server runs on `http://127.0.0.1:5000/`.

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 6. Ready-to-Test Demo Credentials

The database is pre-seeded with sample data representing Gayatri Vidya Parishad College of Engineering for Women:

| Portal | Username / Roll No | Password | Role Details |
|---|---|---|---|
| **Admin Portal** | `admin` | `Admin@123` | College Administrator |
| **Faculty Portal** | `fac_sharma` | `Faculty@123` | Dr. Ananya Sharma (CSE) |
| **Faculty Portal** | `fac_rao` | `Faculty@123` | Prof. K. V. Rao (CSE) |
| **Student Portal** | `student_sneha` | `Student@123` | Sneha Reddy (22L31A0501, CSE Sem 5 Sec A) |
| **Student Portal** | `student_kavya` | `Student@123` | Kavya Varma (22L31A0502, CSE Sem 5 Sec A) |
| **Student Portal** | `student_divya` | `Student@123` | Divya Teja (22L31A0401, ECE Sem 5 Sec A) |

---

## 7. Testing Key Workflows

### A. Landing Page & Three Portals
1. Navigate to `http://127.0.0.1:5000/`.
2. Inspect the 3 portal cards: **Admin**, **Faculty**, and **Student**.
3. Click any portal button to go directly to its dedicated sign-in screen.

### B. Timetable Image Upload & Editable Review
1. Log in as **Admin** (`admin` / `Admin@123`).
2. Go to **Upload Timetable (OCR)** from the sidebar or top navigation.
3. Select:
   - Branch: `CSE`
   - Academic Year: `2025-2026`
   - Semester: `Semester 5`
   - Section: `CSE - Section B`
4. Select the provided sample file: `sample_data/sample_timetable.png`.
5. Click **Upload & Process with OCR**.
6. The system preprocesses the image, extracts text, and opens the **Review & Correct Extracted Timetable** interface.
7. Click the **Toggle Original Upload Image** button to inspect the uploaded image side-by-side.
8. Edit any cells (change subject, faculty, or room number). Notice how uncertain fields are flagged in amber.
9. Click **Approve & Publish Timetable** to validate conflicts and publish.

### C. Classroom Change & Targeted Notification Delivery
1. Log in as **Admin**.
2. Navigate to **Room Changes** (`/admin/room-changes`).
3. Select a class period (e.g. `Monday P1 CS501 [CSE-A]` in room `C-204`).
4. Select a new room: `C-305`.
5. Enter a reason: `Projector repair in room C-204`.
6. Click **Confirm & Dispatch Targeted Alerts**.
7. Log out and log into **Faculty Portal** (`fac_sharma` / `Faculty@123`):
   - Notice the unread alert bell badge:
     `"Classroom Change: Database Management Systems (CSE-A), Period 1, 09:00 AM - 09:50 AM. Previous room: C-204. New room: C-305."`
8. Log out and log into **Student Portal** (`student_sneha` / `Student@123`):
   - Notice that Sneha (in CSE-A) received the room change notification and her dashboard now shows room `C-305`!
9. Log into Student B / ECE (`student_divya` / `Student@123`):
   - Notice that Divya did **NOT** receive any alert because she is not in CSE-A!

### D. Bulk Student Import via CSV
1. In Admin Portal, navigate to **Students**.
2. Click **Import Students CSV**.
3. Select `sample_data/sample_students.csv`.
4. Click **Process CSV Import**.
5. All students are created, assigned to their respective sections, and validated.

---

## 8. Automated Test Suite

Run the full pytest suite:
```powershell
python -m pytest -v
```

### Test Coverage Highlights:
- **`test_1_application_starts_successfully`**
- **`test_2_landing_page_displays_all_three_portals`**
- **`test_3_login_works_for_each_role`**
- **`test_4_unauthorized_users_cannot_access_protected_dashboards`**
- **`test_5_students_cannot_view_another_sections_timetable`**
- **`test_6_faculty_see_their_own_classes_across_multiple_branches`**
- **`test_7_and_22_file_upload_validation_and_security`**
- **`test_8_ocr_extraction_produces_reviewable_draft`**
- **`test_9_and_11_extracted_data_corrected_and_published_updates_dashboards`**
- **`test_10_unapproved_timetables_remain_hidden_from_users`**
- **`test_12_and_13_conflict_validation_detects_room_and_faculty_clashes`**
- **`test_14_15_16_20_room_change_targeted_notifications_and_history`**
- **`test_17_and_18_upcoming_class_reminders_and_duplicate_prevention`**
- **`test_19_notification_read_unread_state`**
- **`test_21_new_timetable_versions_do_not_damage_unrelated_sections`**
- **`test_23_timezone_handling`**
- **`test_admin_branch_and_section_management`**
- **`test_admin_classroom_and_subject_management`**
- **`test_admin_student_csv_bulk_import`**

Result: **19 passed** in ~18 seconds.

---

## 9. Web Push Notifications Setup (Optional)

To enable browser push notifications even when the browser tab is closed:
1. Generate VAPID keys using `py_vapid`:
   ```powershell
   vapid --gen
   ```
2. Put the keys into your `.env` file:
   ```env
   VAPID_PUBLIC_KEY=your_public_key_here
   VAPID_PRIVATE_KEY=your_private_key_here
   VAPID_CLAIM_EMAIL=admin@gvpcew.ac.in
   ```
3. When users log in, the browser prompts for notification permissions and registers `sw.js`.
*(If keys are left blank, in-app bell notifications and real-time Socket.IO alerts continue to function flawlessly).*

---

## 10. Production Deployment Guide

### A. Production Environment Configuration
In `.env`:
```env
FLASK_ENV=production
SECRET_KEY=generate-a-strong-random-64-char-secret-key
DATABASE_URL=postgresql://gvpcew_user:strong_password@localhost:5432/dynamic_class_track
```

### B. Running with Gunicorn / Gevent (Linux / Production Server)
```bash
pip install gunicorn gevent gevent-websocket
gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 4 -b 0.0.0.0:8000 run:app
```

### C. Running on Windows Server (Waitress / Hypercorn)
```powershell
pip install waitress
python -c "from waitress import serve; from run import app; serve(app, host='0.0.0.0', port=5000)"
```

### D. Reverse Proxy with NGINX
```nginx
server {
    listen 80;
    server_name timetable.gvpcew.ac.in;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /socket.io {
        proxy_pass http://127.0.0.1:5000/socket.io;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static {
        alias /var/www/dynamic-class-track/app/static;
        expires 30d;
    }
}
```

---

## 11. Database Backup & Restore

### SQLite Backup:
```powershell
Copy-Item instance/dynamic_class_track.db instance/backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').db
```

### PostgreSQL Backup:
```bash
pg_dump -U gvpcew_user -d dynamic_class_track > backup_gvpcew.sql
```

---

## 12. Packaging the Project into a ZIP File

To create a clean release ZIP archive (excluding virtual environments, temporary logs, and SQLite database files):
```powershell
Compress-Archive -Path app, cli.py, config.py, run.py, requirements.txt, .env.example, .gitignore, README.md, sample_data, tests -DestinationPath Dynamic_Class_Track_GVPCEW.zip -Force
```

---

## 13. License & Attribution
Developed for **Gayatri Vidya Parishad College of Engineering for Women (GVPCEW)**.
Dynamic Class Track &copy; 2026. All rights reserved.
