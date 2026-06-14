"""
Smart College Notice Board Management System
Flask Backend — v5 (SocketIO + Persistent Sessions + Push + Railway MySQL)
"""

import os, json, qrcode, io, base64
from datetime import datetime, timedelta
from functools import wraps
import eventlet
eventlet.monkey_patch()
from dotenv import load_dotenv
load_dotenv()

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_from_directory, make_response)
from flask_mysqldb import MySQL
from flask_socketio import SocketIO, emit, join_room
from werkzeug.utils import secure_filename
import MySQLdb.cursors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import anthropic
from flask_socketio import SocketIO, emit, join_room

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet"
)
# ─── App Configuration ────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'college_notice_board_secret_2024')

# ── Persistent sessions (30 days) ─────────────────────────────────────────────
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_HTTPONLY']    = True
app.config['SESSION_COOKIE_SAMESITE']   = 'Lax'

# ── MySQL ─────────────────────────────────────────────────────────────────────
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'railway')
app.config['MYSQL_PORT'] = int(os.environ.get('MYSQL_PORT', 3306))
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# ── File uploads ──────────────────────────────────────────────────────────────
UPLOAD_FOLDER      = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}
app.config['UPLOAD_FOLDER']      = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

mysql    = MySQL(app)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

# ─── Helpers ──────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'role' not in session or session['role'] not in roles:
                flash('Access denied.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

def log_activity(user_id, action, details=''):
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO activity_logs (user_id, action, details, ip_address) VALUES (%s,%s,%s,%s)",
            (user_id, action, details, request.remote_addr)
        )
        mysql.connection.commit()
        cur.close()
    except Exception:
        pass

def get_unread_notifications(user_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM notifications WHERE user_id=%s AND is_read=0", (user_id,))
        row = cur.fetchone()
        cur.close()
        return row['cnt'] if row else 0
    except Exception:
        return 0

def generate_qr(notice_id):
    base = os.environ.get('APP_URL', 'http://localhost:5000')
    url  = f"{base}/notice/{notice_id}"
    qr   = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def push_notification_to_all(title, message, notice_id=None):
    """Emit real-time SocketIO event to all connected clients."""
    payload = {'title': title, 'message': message, 'notice_id': notice_id,
                'time': datetime.now().strftime('%H:%M')}
    socketio.emit('new_notice', payload, namespace='/')

# ─── Context Processor ────────────────────────────────────────────────────────

@app.context_processor
def inject_globals():
    notif_count = 0
    if 'user_id' in session:
        notif_count = get_unread_notifications(session['user_id'])
    onesignal_app_id = os.environ.get('ONESIGNAL_APP_ID', '')
    return dict(notif_count=notif_count, now=datetime.now(),
                onesignal_app_id=onesignal_app_id)

# ─── SocketIO Events ──────────────────────────────────────────────────────────

@socketio.on('connect')
def on_connect():
    if 'user_id' in session:
        join_room(f"user_{session['user_id']}")
        join_room('all_users')

@socketio.on('disconnect')
def on_disconnect():
    pass

# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role     = request.form.get('role', 'student')

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user_check = cur.fetchone()

        if not user_check:
            cur.close()
            flash('No account found with this email. Please register first.', 'danger')
        elif user_check['password'] != password:
            cur.close()
            flash('Incorrect password. Please try again.', 'danger')
        elif user_check['role'] != role:
            cur.close()
            flash(f'This account is registered as "{user_check["role"].capitalize()}", '
                  f'not "{role.capitalize()}". Please select the correct role.', 'danger')
        elif not user_check['is_active']:
            cur.close()
            flash('Your account is inactive. Please contact the admin.', 'danger')
        else:
            user = user_check
            cur.close()
            # ── Persistent session ────────────────────────────────
            session.permanent = True
            session['user_id'] = user['id']
            session['name']    = user['full_name']
            session['role']    = user['role']
            session['email']   = user['email']
            session['avatar']  = user.get('avatar', '')
            log_activity(user['id'], 'LOGIN', f"Logged in as {role}")
            try:
                cur2 = mysql.connection.cursor()
                cur2.execute(
                    "INSERT INTO notifications (user_id, title, message) VALUES (%s,%s,%s)",
                    (user['id'], 'Welcome Back!',
                     f"Hello {user['full_name']}, welcome back to Notice Board.")
                )
                mysql.connection.commit()
                cur2.close()
            except Exception:
                pass
            flash(f'Welcome, {user["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log_activity(session['user_id'], 'LOGOUT', '')
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        full_name  = request.form.get('full_name',  '').strip()
        email      = request.form.get('email',      '').strip()
        password   = request.form.get('password',   '')
        confirm    = request.form.get('confirm',    '')
        role       = request.form.get('role',       'student')
        department = request.form.get('department', '').strip()
        phone      = request.form.get('phone',      '').strip()
        roll_no    = request.form.get('roll_no',    '').strip()

        if not full_name or not email or not password or not role:
            flash('All required fields must be filled.', 'danger')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')

        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            cur.close()
            flash('This email is already registered. Please login.', 'danger')
            return render_template('register.html')

        cur.execute("""
            INSERT INTO users (full_name, email, password, role, department, phone, roll_no, is_active)
            VALUES (%s,%s,%s,%s,%s,%s,%s,1)
        """, (full_name, email, password, role, department, phone, roll_no))
        mysql.connection.commit()
        new_id = cur.lastrowid
        cur.execute("INSERT INTO notifications (user_id, title, message) VALUES (%s,%s,%s)",
                    (new_id, 'Welcome to CollegeBoard!',
                     f'Hello {full_name}, your account has been created as {role.capitalize()}.'))
        mysql.connection.commit()
        cur.close()
        flash(f'Account created! Welcome, {full_name}. Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    cur  = mysql.connection.cursor()
    role = session['role']
    uid  = session['user_id']

    cur.execute("SELECT COUNT(*) as c FROM notices WHERE is_archived=0")
    total = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM notices WHERE is_archived=0 AND (expiry_date IS NULL OR expiry_date >= CURDATE())")
    active = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM notices WHERE expiry_date < CURDATE()")
    expired = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) as c FROM users WHERE is_active=1")
    total_users = cur.fetchone()['c']

    cur.execute("""
        SELECT c.name, COUNT(n.id) as cnt
        FROM categories c LEFT JOIN notices n ON n.category_id=c.id AND n.is_archived=0
        GROUP BY c.id ORDER BY cnt DESC
    """)
    cat_stats = cur.fetchall()

    if role == 'admin':
        cur.execute("""
            SELECT n.*, c.name as cat_name, u.full_name as author_name
            FROM notices n JOIN categories c ON n.category_id=c.id
            JOIN users u ON n.user_id=u.id
            WHERE n.is_archived=0 ORDER BY n.created_at DESC LIMIT 8
        """)
    elif role == 'faculty':
        cur.execute("""
            SELECT n.*, c.name as cat_name, u.full_name as author_name
            FROM notices n JOIN categories c ON n.category_id=c.id
            JOIN users u ON n.user_id=u.id
            WHERE n.is_archived=0 AND n.user_id=%s ORDER BY n.created_at DESC LIMIT 8
        """, (uid,))
    else:
        cur.execute("""
            SELECT n.*, c.name as cat_name, u.full_name as author_name
            FROM notices n JOIN categories c ON n.category_id=c.id
            JOIN users u ON n.user_id=u.id
            WHERE n.is_archived=0 AND (n.expiry_date IS NULL OR n.expiry_date >= CURDATE())
            ORDER BY n.priority DESC, n.created_at DESC LIMIT 8
        """)
    notices = cur.fetchall()

    activity = []
    if role == 'admin':
        cur.execute("""
            SELECT a.*, u.full_name FROM activity_logs a
            JOIN users u ON a.user_id=u.id ORDER BY a.created_at DESC LIMIT 10
        """)
        activity = cur.fetchall()

    user_stats = {}
    if role == 'admin':
        cur.execute("SELECT role, COUNT(*) as cnt FROM users GROUP BY role")
        for r in cur.fetchall():
            user_stats[r['role']] = r['cnt']

    cur.close()
    return render_template('dashboard.html',
        total=total, active=active, expired=expired, total_users=total_users,
        cat_stats=cat_stats, notices=notices, activity=activity, user_stats=user_stats)

# ─── Notice Routes ────────────────────────────────────────────────────────────

@app.route('/notices')
@login_required
def notices():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()

    q         = request.args.get('q', '')
    cat       = request.args.get('category', '')
    priority  = request.args.get('priority', '')
    date_from = request.args.get('date_from', '')
    date_to   = request.args.get('date_to', '')

    filters = ["n.is_archived=0"]
    params  = []
    if session['role'] != 'admin':
        filters.append("(n.expiry_date IS NULL OR n.expiry_date >= CURDATE())")
    if q:
        filters.append("(n.title LIKE %s OR n.description LIKE %s)")
        params += [f'%{q}%', f'%{q}%']
    if cat:
        filters.append("n.category_id=%s"); params.append(cat)
    if priority:
        filters.append("n.priority=%s"); params.append(priority)
    if date_from:
        filters.append("DATE(n.created_at) >= %s"); params.append(date_from)
    if date_to:
        filters.append("DATE(n.created_at) <= %s"); params.append(date_to)

    where = " AND ".join(filters)
    cur.execute(f"""
        SELECT n.*, c.name as cat_name, u.full_name as author_name
        FROM notices n JOIN categories c ON n.category_id=c.id
        JOIN users u ON n.user_id=u.id
        WHERE {where} ORDER BY n.priority DESC, n.created_at DESC
    """, params)
    notice_list = cur.fetchall()
    cur.close()
    return render_template('notices.html', notices=notice_list, categories=categories,
                           q=q, sel_cat=cat, sel_priority=priority)

@app.route('/notice/<int:nid>')
@login_required
def notice_detail(nid):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT n.*, c.name as cat_name, u.full_name as author_name, u.role as author_role
        FROM notices n JOIN categories c ON n.category_id=c.id
        JOIN users u ON n.user_id=u.id WHERE n.id=%s
    """, (nid,))
    notice = cur.fetchone()
    if not notice:
        flash('Notice not found.', 'danger')
        return redirect(url_for('notices'))
    cur.execute("UPDATE notices SET views=views+1 WHERE id=%s", (nid,))
    mysql.connection.commit()
    qr_data = generate_qr(nid)
    cur.close()
    log_activity(session['user_id'], 'VIEW_NOTICE', f"Viewed notice #{nid}: {notice['title']}")
    return render_template('notice_detail.html', notice=notice, qr_data=qr_data)

@app.route('/notice/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'faculty')
def add_notice():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()
    if request.method == 'POST':
        title       = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category_id = request.form.get('category_id')
        priority    = request.form.get('priority', 'normal')
        expiry_date = request.form.get('expiry_date') or None
        attachment  = None
        attach_type = None

        if not title or not description or not category_id:
            flash('Please fill all required fields.', 'danger')
            return render_template('add_notice.html', categories=categories)

        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename and allowed_file(file.filename):
                filename  = secure_filename(file.filename)
                ts        = datetime.now().strftime('%Y%m%d%H%M%S')
                filename  = f"{ts}_{filename}"
                ext       = filename.rsplit('.', 1)[1].lower()
                subfolder = 'pdfs' if ext == 'pdf' else 'images'
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, filename)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                file.save(save_path)
                attachment  = f"{subfolder}/{filename}"
                attach_type = 'pdf' if ext == 'pdf' else 'image'

        cur.execute("""
            INSERT INTO notices (title, description, category_id, user_id, priority, expiry_date, attachment, attach_type)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (title, description, category_id, session['user_id'], priority, expiry_date, attachment, attach_type))
        mysql.connection.commit()
        nid = cur.lastrowid

        # ── Notify all students + faculty (DB + real-time) ────────
        cur.execute("SELECT id FROM users WHERE role IN ('student','faculty') AND is_active=1 AND id != %s",
                    (session['user_id'],))
        recipients = cur.fetchall()
        for r in recipients:
            cur.execute(
                "INSERT INTO notifications (user_id, notice_id, title, message) VALUES (%s,%s,%s,%s)",
                (r['id'], nid, f"New Notice: {title}", "A new notice has been posted on your board.")
            )
        mysql.connection.commit()
        cur.close()

        # ── Real-time SocketIO broadcast ──────────────────────────
        push_notification_to_all(f"📢 New Notice: {title}",
                                  "A new notice has been posted. Click to view.",
                                  nid)

        log_activity(session['user_id'], 'ADD_NOTICE', f"Added notice: {title}")
        flash('Notice posted successfully!', 'success')
        return redirect(url_for('notices'))
    cur.close()
    return render_template('add_notice.html', categories=categories)

@app.route('/notice/edit/<int:nid>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'faculty')
def edit_notice(nid):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM notices WHERE id=%s", (nid,))
    notice = cur.fetchone()
    if not notice:
        flash('Notice not found.', 'danger')
        return redirect(url_for('notices'))
    if session['role'] == 'faculty' and notice['user_id'] != session['user_id']:
        flash('You can only edit your own notices.', 'danger')
        return redirect(url_for('notices'))
    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()
    if request.method == 'POST':
        title       = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category_id = request.form.get('category_id')
        priority    = request.form.get('priority', 'normal')
        expiry_date = request.form.get('expiry_date') or None
        attachment  = notice['attachment']
        attach_type = notice['attach_type']

        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename and allowed_file(file.filename):
                filename  = secure_filename(file.filename)
                ts        = datetime.now().strftime('%Y%m%d%H%M%S')
                filename  = f"{ts}_{filename}"
                ext       = filename.rsplit('.', 1)[1].lower()
                subfolder = 'pdfs' if ext == 'pdf' else 'images'
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, filename)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                file.save(save_path)
                attachment  = f"{subfolder}/{filename}"
                attach_type = 'pdf' if ext == 'pdf' else 'image'

        cur.execute("""
            UPDATE notices SET title=%s, description=%s, category_id=%s,
            priority=%s, expiry_date=%s, attachment=%s, attach_type=%s, updated_at=NOW()
            WHERE id=%s
        """, (title, description, category_id, priority, expiry_date, attachment, attach_type, nid))
        mysql.connection.commit()
        cur.close()
        log_activity(session['user_id'], 'EDIT_NOTICE', f"Edited notice #{nid}: {title}")
        flash('Notice updated!', 'success')
        return redirect(url_for('notices'))
    cur.close()
    return render_template('edit_notice.html', notice=notice, categories=categories)

@app.route('/notice/delete/<int:nid>', methods=['POST'])
@login_required
@role_required('admin', 'faculty')
def delete_notice(nid):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM notices WHERE id=%s", (nid,))
    notice = cur.fetchone()
    if notice:
        if session['role'] == 'faculty' and notice['user_id'] != session['user_id']:
            flash('You can only delete your own notices.', 'danger')
        else:
            cur.execute("DELETE FROM notices WHERE id=%s", (nid,))
            mysql.connection.commit()
            log_activity(session['user_id'], 'DELETE_NOTICE', f"Deleted notice #{nid}")
            flash('Notice deleted.', 'success')
    cur.close()
    return redirect(url_for('notices'))

@app.route('/notice/archive/<int:nid>', methods=['POST'])
@login_required
@role_required('admin')
def archive_notice(nid):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE notices SET is_archived=1 WHERE id=%s", (nid,))
    mysql.connection.commit()
    cur.close()
    log_activity(session['user_id'], 'ARCHIVE_NOTICE', f"Archived notice #{nid}")
    flash('Notice archived.', 'info')
    return redirect(url_for('notices'))

@app.route('/archive')
@login_required
@role_required('admin')
def archive():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT n.*, c.name as cat_name, u.full_name as author_name
        FROM notices n JOIN categories c ON n.category_id=c.id
        JOIN users u ON n.user_id=u.id WHERE n.is_archived=1 ORDER BY n.updated_at DESC
    """)
    notices = cur.fetchall()
    cur.close()
    return render_template('archive.html', notices=notices)

# ─── AI Summarizer ────────────────────────────────────────────────────────────

@app.route('/api/summarize', methods=['POST'])
@login_required
def ai_summarize():
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    try:
        client  = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=300,
            messages=[{"role": "user",
                       "content": f"Summarize this college notice in 2-3 concise bullet points:\n\n{text}"}]
        )
        return jsonify({'summary': message.content[0].text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─── PDF Export ───────────────────────────────────────────────────────────────

@app.route('/notice/export/<int:nid>')
@login_required
def export_pdf(nid):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT n.*, c.name as cat_name, u.full_name as author_name
        FROM notices n JOIN categories c ON n.category_id=c.id
        JOIN users u ON n.user_id=u.id WHERE n.id=%s
    """, (nid,))
    notice = cur.fetchone()
    cur.close()
    if not notice:
        flash('Notice not found.', 'danger')
        return redirect(url_for('notices'))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    story  = []
    title_style = ParagraphStyle('CT', parent=styles['Title'], fontSize=20, spaceAfter=12,
                                  textColor=colors.HexColor('#1a56db'))
    story.append(Paragraph("COLLEGE NOTICE BOARD", title_style))
    story.append(Spacer(1, 0.1*inch))
    data = [
        ['Title',    notice['title']],
        ['Category', notice['cat_name']],
        ['Priority', notice['priority'].upper()],
        ['Posted By',notice['author_name']],
        ['Date',     str(notice['created_at'])[:10]],
        ['Expiry',   str(notice['expiry_date']) if notice['expiry_date'] else 'No Expiry'],
    ]
    t = Table(data, colWidths=[1.5*inch, 4.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(0,-1), colors.HexColor('#1a56db')),
        ('TEXTCOLOR', (0,0),(0,-1), colors.white),
        ('FONTNAME',  (0,0),(-1,-1),'Helvetica'),
        ('FONTSIZE',  (0,0),(-1,-1), 10),
        ('GRID',      (0,0),(-1,-1), 0.5, colors.grey),
        ('VALIGN',    (0,0),(-1,-1),'TOP'),
        ('PADDING',   (0,0),(-1,-1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Description", styles['Heading2']))
    story.append(Paragraph(notice['description'], styles['BodyText']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%d %b %Y %H:%M')}", styles['Normal']))
    doc.build(story)
    buf.seek(0)
    log_activity(session['user_id'], 'EXPORT_PDF', f"Exported notice #{nid}")
    response = make_response(buf.read())
    response.headers['Content-Type']        = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=notice_{nid}.pdf'
    return response

# ─── Notifications ────────────────────────────────────────────────────────────

@app.route('/notifications')
@login_required
def notifications():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC LIMIT 50
    """, (session['user_id'],))
    notifs = cur.fetchall()
    cur.execute("UPDATE notifications SET is_read=1 WHERE user_id=%s", (session['user_id'],))
    mysql.connection.commit()
    cur.close()
    return render_template('notifications.html', notifs=notifs)

@app.route('/api/notifications/count')
@login_required
def notif_count():
    return jsonify({'count': get_unread_notifications(session['user_id'])})

@app.route('/api/notifications/recent')
@login_required
def notif_recent():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, title, message, is_read, notice_id,
               DATE_FORMAT(created_at,'%%d %%b %%H:%%i') as time_fmt
        FROM notifications WHERE user_id=%s
        ORDER BY created_at DESC LIMIT 8
    """, (session['user_id'],))
    rows = cur.fetchall()
    cur.close()
    return jsonify(rows)

@app.route('/api/notifications/mark-read', methods=['POST'])
@login_required
def mark_all_read():
    cur = mysql.connection.cursor()
    cur.execute("UPDATE notifications SET is_read=1 WHERE user_id=%s", (session['user_id'],))
    mysql.connection.commit()
    cur.close()
    return jsonify({'ok': True})

# ─── OneSignal push token save ────────────────────────────────────────────────

@app.route('/api/push/register', methods=['POST'])
@login_required
def push_register():
    """Save OneSignal player_id for the logged-in user."""
    data = request.get_json() or {}
    player_id = data.get('player_id', '').strip()
    if player_id:
        try:
            cur = mysql.connection.cursor()
            cur.execute("UPDATE users SET push_token=%s WHERE id=%s",
                        (player_id, session['user_id']))
            mysql.connection.commit()
            cur.close()
        except Exception:
            pass
    return jsonify({'ok': True})

# ─── User Management ─────────────────────────────────────────────────────────

@app.route('/users')
@login_required
@role_required('admin')
def manage_users():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = cur.fetchall()
    cur.close()
    return render_template('users.html', users=users)

@app.route('/users/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_user():
    if request.method == 'POST':
        full_name  = request.form.get('full_name',  '').strip()
        email      = request.form.get('email',      '').strip()
        password   = request.form.get('password',   '')
        role       = request.form.get('role',       'student')
        department = request.form.get('department', '').strip()
        if not full_name or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('add_user.html')
        try:
            cur = mysql.connection.cursor()
            cur.execute(
                "INSERT INTO users (full_name, email, password, role, department) VALUES (%s,%s,%s,%s,%s)",
                (full_name, email, password, role, department)
            )
            mysql.connection.commit()
            cur.close()
            log_activity(session['user_id'], 'ADD_USER', f"Added user: {email} ({role})")
            flash('User added successfully!', 'success')
            return redirect(url_for('manage_users'))
        except Exception:
            flash('Email already exists.', 'danger')
    return render_template('add_user.html')

@app.route('/users/toggle/<int:uid>', methods=['POST'])
@login_required
@role_required('admin')
def toggle_user(uid):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET is_active = NOT is_active WHERE id=%s", (uid,))
    mysql.connection.commit()
    cur.close()
    flash('User status updated.', 'info')
    return redirect(url_for('manage_users'))

@app.route('/users/delete/<int:uid>', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(uid):
    if uid == session['user_id']:
        flash("You can't delete yourself.", 'danger')
        return redirect(url_for('manage_users'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM users WHERE id=%s", (uid,))
    mysql.connection.commit()
    cur.close()
    log_activity(session['user_id'], 'DELETE_USER', f"Deleted user #{uid}")
    flash('User deleted.', 'success')
    return redirect(url_for('manage_users'))

# ─── Profile ──────────────────────────────────────────────────────────────────

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    user = cur.fetchone()
    if request.method == 'POST':
        full_name    = request.form.get('full_name',    '').strip()
        department   = request.form.get('department',   '').strip()
        new_password = request.form.get('new_password', '')
        if full_name:
            if new_password:
                cur.execute("UPDATE users SET full_name=%s, department=%s, password=%s WHERE id=%s",
                            (full_name, department, new_password, session['user_id']))
            else:
                cur.execute("UPDATE users SET full_name=%s, department=%s WHERE id=%s",
                            (full_name, department, session['user_id']))
            mysql.connection.commit()
            session['name'] = full_name
            flash('Profile updated!', 'success')
        cur.close()
        return redirect(url_for('profile'))
    cur.close()
    return render_template('profile.html', user=user)

# ─── Static file serving ─────────────────────────────────────────────────────

@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    log_activity(session['user_id'], 'DOWNLOAD', f"Downloaded: {filename}")
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ─── API: Search ─────────────────────────────────────────────────────────────

@app.route('/api/search')
@login_required
def api_search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT n.id, n.title, c.name as category, n.priority, n.created_at
        FROM notices n JOIN categories c ON n.category_id=c.id
        WHERE n.is_archived=0 AND (n.title LIKE %s OR n.description LIKE %s)
        ORDER BY n.created_at DESC LIMIT 10
    """, (f'%{q}%', f'%{q}%'))
    results = cur.fetchall()
    cur.close()
    for r in results:
        if r.get('created_at'):
            r['created_at'] = str(r['created_at'])
    return jsonify(results)

# ─── Auto-expire ──────────────────────────────────────────────────────────────

@app.route('/api/expire-notices', methods=['POST'])
@login_required
@role_required('admin')
def expire_notices():
    cur = mysql.connection.cursor()
    cur.execute("UPDATE notices SET is_archived=1 WHERE expiry_date < CURDATE() AND is_archived=0")
    count = cur.rowcount
    mysql.connection.commit()
    cur.close()
    log_activity(session['user_id'], 'AUTO_EXPIRE', f"Archived {count} expired notices")
    return jsonify({'archived': count})

@app.route('/OneSignalSDKWorker.js')
def onesignal_worker():
    return send_from_directory('static', 'OneSignalSDKWorker.js',
                               mimetype='application/javascript')

@app.route('/OneSignalSDKUpdaterWorker.js')
def onesignal_updater():
    return send_from_directory('static', 'OneSignalSDKUpdaterWorker.js',
                               mimetype='application/javascript')
# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
