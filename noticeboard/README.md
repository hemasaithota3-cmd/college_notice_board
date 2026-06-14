# 📋 Smart College Notice Board Management System

> A full-stack, role-based digital notice board for colleges — built with Flask, MySQL, Bootstrap 5, and AI-powered features.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-green?logo=flask)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange?logo=mysql)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple?logo=bootstrap)

---

## 🌟 Features

### 🔐 Authentication
- **Three roles**: Admin, Faculty, Student
- Secure password hashing (Werkzeug / bcrypt)
- Session-based login with logout
- Role-based access control on all routes

### 🧑‍💼 Admin Dashboard
- Post, edit, delete, and archive any notice
- Manage all users (add, toggle active, delete)
- View analytics: total / active / expired notices, user counts
- Category-wise doughnut chart & user bar chart
- Activity log viewer
- One-click notice expiry automation

### 👩‍🏫 Faculty Dashboard
- Post notices, edit/delete their own notices
- View all active notices
- Receive student notifications on activity

### 🎓 Student Dashboard
- View all active notices sorted by priority
- Search notices by title/description (instant AJAX)
- Filter by category, priority, date range
- Download PDF/image attachments
- Real-time notification bell

### 📌 Notice Features
- Title, description, category, priority, expiry date
- File attachment (PDF or image, up to 16 MB)
- View count tracker
- QR code auto-generated for each notice
- AI summary (Claude Sonnet 4.6)
- PDF export via ReportLab
- Archive system

### 🔔 Notifications
- Auto-notified on new notice post
- Bell icon with unread badge
- 30-second background polling

### 🎨 UI/UX
- Sidebar navigation, sticky topbar
- Dark mode / Light mode (persisted in localStorage)
- Fully mobile responsive
- Smooth animations and hover transitions
- Professional college theme (blue/purple gradient)

---

## 🗂️ Project Structure

```
noticeboard/
├── app.py                  # Main Flask application
├── schema.sql              # MySQL database schema + seed data
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── README.md
├── templates/
│   ├── base.html           # Sidebar + topbar layout
│   ├── login.html          # Login page (split layout)
│   ├── dashboard.html      # Role-aware dashboard with charts
│   ├── notices.html        # Notice list with filters
│   ├── notice_detail.html  # Detail view + QR + AI summary
│   ├── add_notice.html     # Post notice form
│   ├── edit_notice.html    # Edit notice form
│   ├── users.html          # Admin user management table
│   ├── add_user.html       # Add user form
│   ├── notifications.html  # Notification inbox
│   ├── profile.html        # User profile editor
│   └── archive.html        # Archived notices
└── static/
    ├── css/                # Custom stylesheets (if any)
    ├── js/                 # Custom scripts (if any)
    └── uploads/
        ├── pdfs/           # Uploaded PDF files
        └── images/         # Uploaded images
```

---

## ⚙️ Installation Guide

### Prerequisites
- Python 3.10+
- MySQL 8.0+
- pip

### 1. Clone / Download the project

```bash
git clone https://github.com/yourname/college-noticeboard.git
cd college-noticeboard
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note**: On some systems you may need `mysqlclient` build tools:
> - Ubuntu: `sudo apt-get install libmysqlclient-dev`
> - Mac: `brew install mysql`
> - Windows: install the MySQL Connector/C from MySQL website

### 4. Set up MySQL database

```bash
mysql -u root -p < schema.sql
```

Or manually:
```sql
CREATE DATABASE college_noticeboard;
USE college_noticeboard;
-- then paste the contents of schema.sql
```

### 5. Configure environment

```bash
cp .env.example .env
# Edit .env with your MySQL credentials and Anthropic API key
```

### 6. Run the application

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000)

### 7. Demo Login Credentials

| Role    | Email                  | Password     |
|---------|------------------------|--------------|
| Admin   | admin@college.edu      | Admin@123    |
| Faculty | faculty@college.edu    | Faculty@123  |
| Student | student@college.edu    | Student@123  |

> **Note**: The default password hashes in schema.sql are pre-generated. If they don't work, reset via the admin panel after first login with updated hashes.

---

## 🚀 Deployment

### Option 1 — Render (Backend)

1. Push code to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your repo
4. Set:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. Add environment variables from `.env`
6. Deploy!

### Option 2 — Railway

1. `railway login` → `railway init` → `railway up`
2. Add MySQL plugin in Railway dashboard
3. Copy the `DATABASE_URL` parts into individual env vars

### Option 3 — Local Production

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Database Hosting
- [PlanetScale](https://planetscale.com) — free MySQL hosting
- [Clever Cloud](https://clever-cloud.com) — free MySQL
- [Filess.io](https://filess.io) — free MySQL

---

## 🔒 Security Features

| Feature | Implementation |
|---------|---------------|
| Password hashing | `werkzeug.security.generate_password_hash` (pbkdf2:sha256) |
| SQL injection | Parameterized queries via `Flask-MySQLdb` |
| Session management | Flask server-side sessions with secret key |
| File upload validation | Extension whitelist + `secure_filename` |
| Role-based access | `@role_required` decorator on all sensitive routes |
| CSRF protection | Forms via POST only; can add Flask-WTF for tokens |
| Input validation | Required fields checked server-side |

---

## 🤖 AI Summarizer Setup

1. Get your API key from [console.anthropic.com](https://console.anthropic.com)
2. Add to `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
3. Open any notice → click **"Generate AI Summary"**

The AI uses **Claude Sonnet 4.6** to produce 2–3 bullet-point summaries of each notice.

---

## 📊 Database Schema

### Tables
| Table | Purpose |
|-------|---------|
| `users` | All user accounts with roles |
| `categories` | Notice categories (Academic, Placement, etc.) |
| `notices` | All notices with metadata |
| `notifications` | Per-user notification inbox |
| `activity_logs` | Audit trail of all actions |

---

## 🔗 LinkedIn Project Description

**Smart College Notice Board Management System**

Built a full-stack web application to digitize and centralize college notice management. The system supports three user roles (Admin, Faculty, Student) with role-based dashboards and access control.

**Tech Stack**: Python Flask · MySQL · Bootstrap 5 · JavaScript · Chart.js · Anthropic Claude API

**Key highlights**:
- Role-based authentication (Admin / Faculty / Student) with session management
- CRUD operations for notices with file attachments (PDF & images)
- AI-powered notice summarizer using Anthropic's Claude Sonnet model
- Auto-generated QR codes for each notice for quick sharing
- PDF export functionality using ReportLab
- Real-time notification system with bell icon and unread badge
- Dark/Light mode with localStorage persistence
- Interactive analytics dashboard with Chart.js doughnut and bar charts
- Instant AJAX search across all notices
- Notice archiving and auto-expiry automation
- Activity log for full audit trail
- Mobile-responsive design with animated sidebar

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

*Built with ❤️ for college communities*
